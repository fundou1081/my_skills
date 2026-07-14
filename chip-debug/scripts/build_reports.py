#!/usr/bin/env python3
"""build_reports.py — Render the two markdown deliverables of an RCA session.

Companion to `build_rc_file.py` (which emits the YAML RC file). Both tools are
mandatory under the operational discipline defined in
`references/output-artifacts-and-discipline.md` §3.5 (script-generated outputs).

Subcommands
-----------
- `chain-report <session_dir>`  produces `9_output/chain_report.md`
- `exploration-log <session_dir>` produces `9_output/exploration_log.md`
- `all <session_dir>`            does both

Each subcommand supports:
    --out <path>          explicit output path (default: under 9_output/)
    --verify              re-render and compare to on-disk output (CI gate)

The rendered output embeds:
- evidence_chain.json nodes (Per-hop Evidence, Falsification, Self-Check)
- decision_log.json entries (Exploration Log hypothesis index, Tag filter)
- raw time-check output (RC report §4.4)
- signal_snapshots/* referenced from chain nodes (RC report §3 excerpts)

Stdlib-only. No external deps.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Markdown primitives — small, hand-rolled, sufficient for the two reports.
# -----------------------------------------------------------------------------

class MdDoc:
    """A tiny markdown builder. Lines are accumulated in order; sections
    separated by blank lines. Output via render()."""

    def __init__(self) -> None:
        self.buf: List[str] = []

    def add(self, line: str) -> None:
        self.buf.append(line)

    def blank(self) -> None:
        if self.buf and self.buf[-1] != "":
            self.buf.append("")

    def h1(self, text: str) -> None:
        self.blank(); self.buf.append(f"# {text}"); self.blank()

    def h2(self, text: str) -> None:
        self.blank(); self.buf.append(f"## {text}"); self.blank()

    def h3(self, text: str) -> None:
        self.blank(); self.buf.append(f"### {text}"); self.blank()

    def para(self, text: str) -> None:
        self.blank(); self.buf.append(text); self.blank()

    def kv(self, key: str, value: Any) -> None:
        """Inline key/value line: `- **Key**: value`."""
        self.buf.append(f"- **{key}**: {value}")

    def bullets(self, items: Iterable[str]) -> None:
        for it in items:
            self.buf.append(f"- {it}")

    def code(self, body: str, lang: str = "") -> None:
        self.blank()
        self.buf.append(f"```{lang}")
        self.buf.append(body.rstrip("\n"))
        self.buf.append("```")
        self.blank()

    def quote(self, text: str) -> None:
        self.blank()
        for ln in text.rstrip("\n").splitlines():
            self.buf.append(f"> {ln}")
        self.blank()

    def table(self, headers: List[str], rows: List[List[str]]) -> None:
        self.blank()
        self.buf.append("| " + " | ".join(headers) + " |")
        self.buf.append("|" + "|".join(["---"] * len(headers)) + "|")
        for row in rows:
            self.buf.append("| " + " | ".join(str(c) for c in row) + " |")
        self.blank()

    def diff_block(self, body: str) -> None:
        self.blank()
        self.buf.append("```diff")
        self.buf.append(body.rstrip("\n"))
        self.buf.append("```")
        self.blank()

    def checklist(self, items: Iterable[str]) -> None:
        self.blank()
        for it in items:
            self.buf.append(f"- [ ] {it}")
        self.blank()

    def hr(self) -> None:
        self.blank(); self.buf.append("---"); self.blank()

    def raw(self, text: str) -> None:
        """Append a literal block of text."""
        self.blank(); self.buf.append(text.rstrip("\n")); self.blank()

    def render(self) -> str:
        # Collapse 3+ consecutive blanks into 1
        out: List[str] = []
        for ln in self.buf:
            if ln == "" and out and out[-1] == "":
                continue
            out.append(ln)
        # Trim leading/trailing blank lines
        while out and out[0] == "":
            out.pop(0)
        while out and out[-1] == "":
            out.pop()
        return "\n".join(out) + "\n"


# -----------------------------------------------------------------------------
# Common helpers (shared between chain-report and exploration-log)
# -----------------------------------------------------------------------------

def _now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _truncate(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else (s[: n - 1] + chr(8230))


def _relpath(p: Path, base: Path) -> str:
    """Best-effort relative path; falls back to absolute on symlinked tmp dirs."""
    try:
        return str(p.relative_to(base))
    except ValueError:
        try:
            return os.path.relpath(str(p), str(base))
        except ValueError:
            return str(p)


def _parse_source(src: str) -> Tuple[str, int]:
    if not src:
        return "", 0
    try:
        kind, rest = src.split(":", 1)
    except ValueError:
        return "", 0
    *fs, last = rest.split(":")
    line = int(last) if last.isdigit() else 0
    path = ":".join(fs).lstrip("@")
    return path, line


def _read_excerpt(file_: str, line_: int, context: int = 3) -> str:
    """Read a few lines of source as an excerpt."""
    if not file_ or not line_:
        return ""
    try:
        with open(file_, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return ""
    start = max(0, line_ - 1 - context)
    end = min(len(lines), line_ + context)
    return "".join(f"{i+1:>5}: {lines[i].rstrip()}\n" for i in range(start, end))


def _severity_summary(seconds: Optional[float]) -> str:
    """Tinier than checklists; returns a chip-style severity based on chipdays."""
    return "S0" if seconds and seconds <= 60 else "S2"  # very rough


# -----------------------------------------------------------------------------
# chain-report builder — references/assets/templates/RC_report.md.template
# -----------------------------------------------------------------------------

def build_chain_report(session_dir: Path,
                       chain_path: Optional[Path] = None,
                       decision_log_path: Optional[Path] = None,
                       out_path: Optional[Path] = None,
                       author: str = "(auto)",
                       module_or_project: str = "(unset)",
                       log_reference: str = "(unset)",
                       fix_description: str = "(populate after Stage 5)",
                       fix_diff: str = "--- a/(unset)\n+++ b/(unset)\n@@ -1,1 +1,1 @@\n-(populate)\n+(populate)",
                       ) -> str:
    chain_p = chain_path or (session_dir / "1_evidence" / "evidence_chain.json")
    dec_p = decision_log_path or (session_dir / "2_decisions" / "decision_log.json")
    chain = _read_json(chain_p)
    decisions = _read_json(dec_p)
    if not chain:
        raise FileNotFoundError(f"chain.json not found: {chain_p}")

    locked = chain.get("locked_entry") or {}
    nodes = list(chain.get("nodes") or [])
    rc_node = next((n for n in nodes if n.get("node_id") == "RC"), None)
    e0_node = next((n for n in nodes if n.get("node_id") == "E0"), None)
    if rc_node is None or e0_node is None:
        raise ValueError("chain must contain E0 and RC nodes")

    # Sort hops along the causal direction: RC -> ... -> E0 (layer ascending
    # with RC (-1) pushed to the start of "deepest" end).
    def sort_key(n):
        layer = n.get("layer")
        if layer is None:
            return (0, 0, n.get("node_id") or "")
        eff = 99 if layer == -1 else layer
        return (1, eff, n.get("node_id") or "")

    chain_nodes = sorted(nodes, key=sort_key)

    doc = MdDoc()

    # ── Title + meta block ──
    doc.h1(f"Root Cause Report — {chain.get('session_id', 'unknown')}")
    doc.add(f"**Date**: {_now_iso()}")
    doc.add(f"**Author**: {author}")
    doc.add(f"**Module / Project**: {module_or_project}")
    # Severity: best-effort from decisions
    severity = "S2"
    for d in decisions.get("decisions", []):
        if d.get("tag") == "stage4.toggle_test" and d.get("verdict") == "accept":
            severity = "S1"
    doc.add(f"**Severity**: {severity} *(S0=blocks CI, S1=wrong data, S2=rare miscompare, S3=cosmetic)*")
    doc.add(f"**Reference run / log**: {log_reference}")
    doc.hr()

    # ── 1. Symptom Summary ──
    doc.h2("1. Symptom Summary")
    doc.kv("Locked time", locked.get("time") or locked.get("timestamp_raw") or "(unset)")
    doc.kv("Locked signal", locked.get("signal") or "(unset)")
    doc.kv("Observed value", locked.get("actual") or "(unset)")
    doc.kv("Expected value", locked.get("expected") or "(unset)")

    # ── 2. Causal Chain (ASCII DAG) ──
    doc.h2("2. Causal Chain")
    doc.para(
        "Each line below is one hop with source pointer and confidence. "
        "Time is read with `time` field; downstream is later."
    )
    ascii_lines = ["[RC] (root) — layer=-1"]
    for n in chain_nodes:
        if n.get("node_id") in {"RC", "E0"}:
            continue
        nid = n.get("node_id", "?")
        sig = n.get("signal", "?")
        t = n.get("time") or "?"
        rel = _truncate(n.get("relation") or "(no relation)", 60)
        ascii_lines.append(f"[{nid}] {sig}  @ {t}  → {rel}")
    ascii_lines.append("[E0] symptom — layer=0")
    doc.code("\n".join(ascii_lines), lang="text")

    # ── 3. Per-hop Evidence ──
    doc.h2("3. Per-hop Evidence")
    for n in chain_nodes:
        nid = n.get("node_id", "?")
        hop = n.get("hop", "?")
        doc.h3(f"[{nid}] — {hop}")
        doc.kv("Stage", n.get("stage") or "?")
        doc.kv("Time", n.get("time") or "(unset)")
        doc.kv("Signal", n.get("signal") or "(unset)")
        actual = n.get("actual") or "(unset)"
        expected = n.get("expected") or "(unset)"
        doc.kv("Actual / Expected", f"`{actual}` / `{expected}`")
        doc.kv("Source", n.get("source") or "(unset)")
        doc.kv("Evidence kind", n.get("evidence_kind") or "(unset)")
        if n.get("relation"):
            doc.kv("Relation", n.get("relation"))
        doc.kv("Confidence", n.get("confidence"))
        if n.get("note"):
            doc.kv("Note", n.get("note"))
        # Attach a code excerpt if source is a code_inspection
        src = n.get("source", "")
        f_, line_ = _parse_source(src)
        if f_ and line_ and n.get("evidence_kind") in ("code_inspection", "formal_counterexample"):
            excerpt = _read_excerpt(f_, line_)
            if excerpt:
                doc.code(excerpt, lang="text")

    # ── 4. Falsification Evidence ──
    doc.h2("4. Falsification Evidence")
    # 4.1 toggle test
    doc.h3("4.1 Toggle test")
    ran_any = False
    for d in decisions.get("decisions", []):
        if d.get("tag") == "stage4.toggle_test":
            ran_any = True
            doc.kv(d.get("verdict", "?").capitalize(), f"{d.get('hypothesis','')} — {d.get('reason','')}")
    if not ran_any:
        doc.para("(toggle test not yet recorded; populate via `decision_log.py add --tag stage4.toggle_test`)")

    # 4.2 counter-examples
    doc.h3("4.2 Counter-example search")
    ce_present = False
    for d in decisions.get("decisions", []):
        if d.get("tag") == "stage4.counter_example":
            ce_present = True
            doc.kv(d.get("verdict", "?").capitalize(), f"{d.get('hypothesis','')} — {d.get('reason','')}")
    if not ce_present:
        doc.para("(no counter-examples recorded)")

    # 4.3 secondary anomalies
    doc.h3("4.3 Secondary anomaly coverage")
    sec_rows = []
    for d in decisions.get("decisions", []):
        if d.get("tag") == "stage3.secondary_anomaly":
            sec_rows.append([d.get("hypothesis") or "", d.get("evidence_ref") or "(unset)"])
    if sec_rows:
        doc.table(["Anomaly", "Explained by which hop"], sec_rows)
    else:
        doc.para("(no secondary anomalies recorded)")

    # 4.4 time-unidirectional
    doc.h3("4.4 Time-unidirectional check")
    doc.para(
        "Mandatory: time must monotonically non-decrease along the chain "
        "(RC -> ... -> E0). Run "
        "`python3 scripts/evidence_chain.py time-check <chain.json>`."
    )
    tc_out = _run_time_check(chain_p)
    doc.code(tc_out, lang="text")

    # ── 5. Suggested Fix ──
    doc.h2("5. Suggested Fix")
    doc.para(fix_description)
    doc.diff_block(fix_diff)

    # ── 6. Self-Check Confirmation ──
    doc.h2("6. Self-Check Confirmation")
    doc.para("Tick once complete:")
    doc.checklist([
        "Simplest possible 100% reproduction steps exist",
        "Causal chain has no logical jumps",
        "All secondary anomalies disappear after fix",
        "Reverting the fix re-introduces the symptom",
        "Fix is stable across compile-flag / timing / layout variations",
        "No other independent suspect explains all phenomena equally",
        "Peer-reviewed and logic accepted",
    ])

    # ── 7. Appendix ──
    doc.h2("7. Appendix — Artifacts")
    doc.bullets([
        f"`{_relpath(chain_p, session_dir)}`",
        f"`{_relpath(dec_p, session_dir)}`",
        "`3_repro/` — toggle-test reproducers",
        "`1_evidence/signal_snapshots/` — wave/log excerpts",
        f"`{session_dir / '9_output' / 'RC_file.yaml'}` — script-generated by `build_rc_file.py`",
    ])

    # ── 8. Root Cause Elevation (optional, hand-fill) ──
    doc.h2("8. Root Cause Elevation (optional)")
    doc.para(
        "See `references/root-cause-elevation.md`. Fill in only the dimensions "
        "that apply; default = skipped."
    )
    doc.bullets([
        "**Design** — spec gap / intent clarity: ...",
        "**Architecture** — rc_is_local / monitor_missed_at / debt entry: ...",
        "**Style / Convention** — bug_class / lint_rule / review_checklist_addition: ...",
        "**Generalization** — bug_fingerprint / audit_plan / cross_component_suspect: ...",
        "**Elevation done by / date / follow-up owner / due**: ...",
    ])

    # TL;DR
    doc.h2("TL;DR")
    doc.para(
        f"**Symptoms**: {locked.get('actual') or '(unset)'} at {locked.get('time') or '(unset)'} "
        f"on `{locked.get('signal') or '(unset)'}`."
    )
    if rc_node:
        rc_src = rc_node.get("source", "")
        rc_file, rc_line = _parse_source(rc_src)
        doc.para(
            f"**RC**: `{rc_node.get('signal','(unset)')}` at `{rc_file}:{rc_line}`."
        )
    doc.para("**Fix**: see §5.")
    doc.para("**Elevation**: see §8 (optional).")

    return doc.render()


def _run_time_check(chain_p: Path) -> str:
    """Run the bundled `evidence_chain.py time-check` and capture output."""
    script = Path(__file__).resolve().parent / "evidence_chain.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "time-check", str(chain_p)],
            capture_output=True, text=True, timeout=30,
        )
        out = (proc.stdout or "") + ((("\n" + proc.stderr) if proc.stderr else ""))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        out = "(time-check script not available; run `python3 scripts/evidence_chain.py time-check <chain.json>` manually)"
    return out.strip() or "(time-check produced no output)"


# -----------------------------------------------------------------------------
# exploration-log builder — references/assets/templates/exploration.md.template
# -----------------------------------------------------------------------------

def build_exploration_log(session_dir: Path,
                          chain_path: Optional[Path] = None,
                          decision_log_path: Optional[Path] = None,
                          out_path: Optional[Path] = None,
                          ) -> str:
    chain_p = chain_path or (session_dir / "1_evidence" / "evidence_chain.json")
    dec_p = decision_log_path or (session_dir / "2_decisions" / "decision_log.json")
    chain = _read_json(chain_p)
    decisions = _read_json(dec_p)

    decs = list((decisions or {}).get("decisions", []))
    session_id = (chain or {}).get("session_id") or (decisions or {}).get("session_id") or "unknown"

    doc = MdDoc()
    doc.h1(f"Exploration Log — {session_id}")
    doc.para(
        "A human-readable record of every branch tried and every hypothesis "
        "rejected. Source of truth is `decision_log.json`; this file mirrors "
        "it for human review and share-out."
    )
    doc.hr()

    # Branch / Hypothesis Index
    doc.h2("Branch / Hypothesis Index")
    if decs:
        for d in decs:
            did = d.get("decision_id", "?")
            verdict = d.get("verdict", "?")
            tag = d.get("tag") or "-"
            ts = d.get("timestamp", "")
            doc.h3(f"[{did}] — {ts}  *(verdict: {verdict}, tag: {tag})*")
            doc.kv("Hypothesis", d.get("hypothesis") or "(empty)")
            if d.get("evidence_ref"):
                doc.kv("Evidence at", d.get("evidence_ref"))
            doc.kv("Reason", d.get("reason") or "(empty)")
    else:
        doc.para("(no decisions recorded yet)")

    # Search strategy
    doc.h2("Search Strategy Used")
    doc.para(
        "(populate — describe whether DFS / BFS / hybrid, scoring rationale, "
        "and any strategy pivots)"
    )

    # Tied-off branches
    doc.h2("Branches Tied Off Without Closure")
    doc.para("(none recorded — populate when you defer hypotheses with re-open conditions)")

    # Counter-examples
    doc.h2("Counter-Examples Considered")
    ce = [d for d in decs if d.get("tag") == "stage4.counter_example"]
    if ce:
        rows = [[d.get("decision_id", "?"), d.get("hypothesis") or "", d.get("reason") or ""] for d in ce]
        doc.table(["Decision", "Hypothesis", "Finding"], rows)
    else:
        doc.para("(no counter-examples documented)")

    # Tooling notes
    doc.h2("Tooling Notes")
    snap_dir = session_dir / "1_evidence" / "signal_snapshots"
    if snap_dir.is_dir():
        snaps = sorted(snap_dir.glob("*.json"))
        if snaps:
            rows = [[s.name, str(s.relative_to(session_dir))] for s in snaps]
            doc.table(["Snapshot", "Path"], rows)
        else:
            doc.para("(no snapshots archived)")
    else:
        doc.para("(no snapshots directory)")

    # Cross-session handoff
    doc.h2("Cross-Session Handoff")
    nodes = (chain or {}).get("nodes", [])
    rc = next((n for n in nodes if n.get("node_id") == "RC"), None)
    e0 = next((n for n in nodes if n.get("node_id") == "E0"), None)
    if e0:
        doc.kv("Current stage", "Stage 5 (Delivery)" if rc else "Stage 1–4 in progress")
    if rc:
        doc.kv("Open RC", rc.get("signal", "(unset)"))
    doc.kv("Total decisions", len(decs))
    doc.kv("Accepts / rejects / parks",
           f"{sum(1 for d in decs if d.get('verdict') == 'accept')} / "
           f"{sum(1 for d in decs if d.get('verdict') == 'reject')} / "
           f"{sum(1 for d in decs if d.get('verdict') == 'park')}")

    return doc.render()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def _write_and_announce(text: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"wrote: {out_path}")


def _verify_with_fresh(out_path: Path, builder: Callable[[], str]) -> int:
    """Re-run builder, compare to on-disk file; exit 0 if identical."""
    if not out_path.is_file():
        print(f"verify-fail: file not found: {out_path}", file=sys.stderr)
        return 2
    fresh = builder()
    on_disk = out_path.read_text(encoding="utf-8")
    if fresh == on_disk:
        print(f"OK: {out_path} matches script-generated output.")
        return 0
    print(f"MISMATCH: re-run `python3 scripts/build_reports.py ... --out {out_path}` to regenerate.",
          file=sys.stderr)
    return 1


def cmd_chain_report(args) -> int:
    session = Path(args.session_dir).resolve()
    chain_p = Path(args.chain).resolve() if args.chain else (session / "1_evidence" / "evidence_chain.json")
    dec_p = Path(args.decision_log).resolve() if args.decision_log else (session / "2_decisions" / "decision_log.json")
    out_p = Path(args.out).resolve() if args.out else (session / "9_output" / "chain_report.md")
    try:
        text = build_chain_report(
            session, chain_p, dec_p, out_p,
            author=getattr(args, "author", "") or "(auto)",
            module_or_project=getattr(args, "module", "") or "(unset)",
            log_reference=getattr(args, "log_ref", "") or "(unset)",
            fix_description=getattr(args, "fix_description", "") or "(populate after Stage 5)",
            fix_diff=getattr(args, "fix_diff", "") or "--- a/(unset)\n+++ b/(unset)\n@@ -1,1 +1,1 @@\n-(populate)\n+(populate)",
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if getattr(args, "verify", False) and out_p.is_file():
        return _verify_with_fresh(out_p, lambda: build_chain_report(session, chain_p, dec_p, out_p))
    _write_and_announce(text, out_p)
    return 0


def cmd_exploration_log(args) -> int:
    session = Path(args.session_dir).resolve()
    chain_p = Path(args.chain).resolve() if args.chain else (session / "1_evidence" / "evidence_chain.json")
    dec_p = Path(args.decision_log).resolve() if args.decision_log else (session / "2_decisions" / "decision_log.json")
    out_p = Path(args.out).resolve() if args.out else (session / "9_output" / "exploration_log.md")
    text = build_exploration_log(session, chain_p, dec_p, out_p)
    if getattr(args, "verify", False) and out_p.is_file():
        return _verify_with_fresh(out_p, lambda: build_exploration_log(session, chain_p, dec_p, out_p))
    _write_and_announce(text, out_p)
    return 0


def cmd_all(args) -> int:
    rc = cmd_chain_report(args)
    if rc != 0:
        return rc
    return cmd_exploration_log(args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render markdown reports for an RCA session.")
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("session_dir")
    common.add_argument("--chain", default=None)
    common.add_argument("--decision-log", default=None)
    common.add_argument("--out", default=None)
    common.add_argument("--verify", action="store_true",
                        help="Re-render and compare to on-disk output (CI gate).")

    sp = sub.add_parser("chain-report", parents=[common],
                        help="Render the chain report (per-hop evidence, falsification, self-check).")
    sp.add_argument("--author", default="")
    sp.add_argument("--module", default="")
    sp.add_argument("--log-ref", default="")
    sp.add_argument("--fix-description", default="")
    sp.add_argument("--fix-diff", default="")
    sp.set_defaults(func=cmd_chain_report)

    sp = sub.add_parser("exploration-log", parents=[common],
                        help="Render the exploration log (decision mirror + tooling notes + handoff).")
    sp.set_defaults(func=cmd_exploration_log)

    sp = sub.add_parser("all", parents=[common],
                        help="Render both chain_report.md and exploration_log.md.")
    sp.set_defaults(func=cmd_all)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
