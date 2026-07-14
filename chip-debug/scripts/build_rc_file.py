#!/usr/bin/env python3
"""build_rc_file.py — Generate RC_file.yaml from evidence_chain.json + decision_log.json.

Per the operational discipline (see references/output-artifacts-and-discipline.md §3.5),
RC_file.yaml must be **script-generated**, never hand-written. This script is the
reference implementation of that rule.

Workflow:
    1. Reads evidence_chain.json + decision_log.json from the session directory.
    2. Walks the chain (E0 -> L1 -> L2 -> ... -> RC) and emits one entry per
       causal signal under `causal_signals:` with rich fields (semantic_relations,
       source_location, waveform_changes, hop_count).
    3. Auto-extracts constraints from `code_inspection` nodes with confidence
       >= 0.95 into `auto_constraints:`.
    4. Pulls toggle-test verdicts from decision_log (tag=stage4.toggle_test)
       and module boundary from decision_log (tag=stage5.module_boundary).
    5. Emits a YAML file at the output path with a trailing "DO NOT EDIT" header.

Output is written with a tiny stdlib-only YAML emitter (no PyYAML dependency).

Usage:
    python3 scripts/build_rc_file.py <session_dir> --out 9_output/RC_file.yaml
    python3 scripts/build_rc_file.py <session_dir> --verify
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


TOOL_VERSION = "build_rc_file.py/1.0"


# -----------------------------------------------------------------------------
# YAML emitter — minimal, stdlib-only, sufficient for RC file structure.
# -----------------------------------------------------------------------------

class _YamlEmitter:
    """Emit a limited YAML subset: strings (incl. multiline `|`), numbers,
    booleans, None, list, dict. No anchors, no tags."""

    def __init__(self) -> None:
        self.lines: List[str] = []

    @staticmethod
    def _needs_quote(s: str) -> bool:
        if s == "":
            return True
        # Reserved-looking tokens
        if s.lower() in {"true", "false", "null", "yes", "no", "on", "off", "~"}:
            return True
        # Characters that confuse YAML parsers
        for ch in s:
            if ch in "{}[]:,#&*!|>%@`'\"":
                return True
            if ord(ch) < 0x20:  # control
                return True
        if s.startswith(("-", "?", ":", ",", "[", "]", "{", "}", "#", "&", "*", "!", "|", ">", "'", "\"", "%", "@", "`")):
            return True
        if s.endswith(":"):
            return True
        if s != s.strip():  # leading/trailing whitespace
            return True
        return False

    @staticmethod
    def _escape_quoted(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def emit(self, obj: Any, indent: int = 0) -> None:
        sp = "  " * indent
        if obj is None:
            self.lines.append(f"{sp}null")
            return
        if isinstance(obj, bool):
            self.lines.append(f"{sp}{'true' if obj else 'false'}")
            return
        if isinstance(obj, (int, float)):
            self.lines.append(f"{sp}{obj}")
            return
        if isinstance(obj, str):
            self._emit_str(obj, indent)
            return
        if isinstance(obj, list):
            self._emit_list(obj, indent)
            return
        if isinstance(obj, dict):
            self._emit_dict(obj, indent)
            return
        raise ValueError(f"unsupported YAML scalar: {type(obj).__name__}")

    def _emit_str(self, s: str, indent: int) -> None:
        sp = "  " * indent
        if "\n" in s:
            # Multiline string with `|`
            lines = s.split("\n")
            if lines and lines[-1] == "":
                lines = lines[:-1]
            self.lines.append(f"{sp}|")
            for ln in lines:
                self.lines.append(f"{sp}  {ln}")
            return
        if self._needs_quote(s):
            self.lines.append(f'{sp}"{self._escape_quoted(s)}"')
        else:
            self.lines.append(f"{sp}{s}")

    def _emit_list(self, lst: List[Any], indent: int) -> None:
        sp = "  " * indent
        if not lst:
            self.lines.append(f"{sp}[]")
            return
        for item in lst:
            if isinstance(item, dict):
                # "- key: val" or multi-key per nested block
                keys = list(item.keys())
                if not keys:
                    self.lines.append(f"{sp}- {{}}")
                    continue
                # First key on the dash line
                first_k, first_v = keys[0], item[keys[0]]
                first_text = self._render_inline(first_v)
                self.lines.append(f"{sp}- {first_k}: {first_text}" if first_text is not None else f"{sp}- {first_k}:")
                # Remaining keys on following lines
                for k in keys[1:]:
                    v = item[k]
                    inner_text = self._render_inline(v)
                    if inner_text is None:
                        self.lines.append(f"{sp}  {k}:")
                        # descend nested
                        sub_emitter = _YamlEmitter()
                        sub_emitter.emit(v, indent=indent + 2)
                        self.lines.extend(sub_emitter.lines)
                    else:
                        self.lines.append(f"{sp}  {k}: {inner_text}")
            elif isinstance(item, list):
                self.lines.append(f"{sp}-")
                self.emit(item, indent + 1)
            else:
                text = self._render_inline(item)
                self.lines.append(f"{sp}- {text}")

    def _render_inline(self, obj: Any) -> Optional[str]:
        """Render an inline scalar on the same line. For list / dict / multiline
        string, returns None (caller emits multi-line form)."""
        if obj is None:
            return "null"
        if isinstance(obj, bool):
            return "true" if obj else "false"
        if isinstance(obj, (int, float)):
            return str(obj)
        if isinstance(obj, str):
            if "\n" in obj:
                return None
            if self._needs_quote(obj):
                return f'"{self._escape_quoted(obj)}"'
            return obj
        return None

    def _emit_dict(self, d: Dict[str, Any], indent: int) -> None:
        sp = "  " * indent
        if not d:
            self.lines.append(f"{sp}{{}}")
            return
        for k, v in d.items():
            inline = self._render_inline(v)
            if v is None:
                self.lines.append(f"{sp}{k}: null")
            elif inline is not None:
                self.lines.append(f"{sp}{k}: {inline}")
            elif isinstance(v, list):
                # If list is empty use []
                if not v:
                    self.lines.append(f"{sp}{k}: []")
                else:
                    self.lines.append(f"{sp}{k}:")
                    self.emit(v, indent + 1)
            elif isinstance(v, dict):
                self.lines.append(f"{sp}{k}:")
                self.emit(v, indent + 1)
            else:  # multiline str
                self.lines.append(f"{sp}{k}: |")
                for ln in str(v).split("\n"):
                    self.lines.append(f"{sp}  {ln}")

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"


# -----------------------------------------------------------------------------
# RC File Builder
# -----------------------------------------------------------------------------

class RCFileBuilder:
    """Construct the structured RC file content from chain.json + decision_log.json."""

    def __init__(self, session_dir: Path,
                 chain_path: Optional[Path] = None,
                 decision_log_path: Optional[Path] = None) -> None:
        self.session_dir = session_dir
        self.chain_path = chain_path or (session_dir / "1_evidence" / "evidence_chain.json")
        self.decision_log_path = decision_log_path or (session_dir / "2_decisions" / "decision_log.json")
        self.chain: Dict[str, Any] = {}
        self.decisions: Dict[str, Any] = {}

    def load(self) -> None:
        if not self.chain_path.is_file():
            raise FileNotFoundError(f"chain.json not found: {self.chain_path}")
        self.chain = json.loads(self.chain_path.read_text(encoding="utf-8"))
        if self.decision_log_path.is_file():
            self.decisions = json.loads(self.decision_log_path.read_text(encoding="utf-8"))
        else:
            self.decisions = {"decisions": []}

    # ---- accessors ----

    def locked_entry(self) -> Dict[str, Any]:
        return dict(self.chain.get("locked_entry") or {})

    def rc_node(self) -> Optional[Dict[str, Any]]:
        for n in self.chain.get("nodes", []):
            if n.get("node_id") == "RC":
                return n
        return None

    def chain_nodes_sorted(self) -> List[Dict[str, Any]]:
        """Sort chain from deepest layer (root) → E0 by layer desc, then by id."""
        nodes = list(self.chain.get("nodes", []))
        nodes.sort(key=lambda n: (-(n.get("layer") or 0), n.get("node_id") or ""))
        return nodes

    def hop_count(self, node: Dict[str, Any]) -> int:
        """hop_count = number of layers between this node and E0 (E0 = 0)."""
        layer = node.get("layer")
        if layer is None or layer <= 0:
            return 0
        # E0 is layer 0; L1 is layer 1; hop_count = layer for downstream.
        # For RC (layer -1), hop_count = max layer across all nodes.
        if layer == -1:
            max_layer = max((n.get("layer") or 0) for n in self.chain.get("nodes", []))
            return max(max_layer, 0)
        return layer

    # ---- building sections ----

    def build_root_cause(self) -> Dict[str, Any]:
        rc = self.rc_node()
        if rc is None:
            return {
                "node_id": "RC",
                "signal": "(unset)",
                "file": "",
                "line": 0,
                "snippet": "(no RC node in chain)",
                "semantic_kind": "code_inspection",
                "confidence": 0.0,
            }
        # Try to parse file:line from source pointer if present
        src = rc.get("source", "")
        file_, line_ = self._parse_source(src)
        # Pull a few lines of code from the file as snippet, if available.
        snippet = self._read_snippet(file_, line_, context=2) if file_ else ""
        return {
            "node_id": "RC",
            "signal": rc.get("signal", ""),
            "file": file_,
            "line": line_,
            "snippet": snippet or "(no snippet available — re-run with source file present)",
            "semantic_kind": rc.get("evidence_kind", "code_inspection"),
            "confidence": rc.get("confidence", 1.0),
        }

    def build_causal_signals(self) -> List[Dict[str, Any]]:
        out = []
        for n in self.chain_nodes_sorted():
            if n.get("node_id") in {"E0", "RC"}:
                continue
            out.append(self._signal_entry(n))
        # Add E0 at the head so the list always references the locked symptom.
        e0 = self._e0_entry()
        if e0 is not None:
            out.insert(0, e0)
        return out

    def _e0_entry(self) -> Optional[Dict[str, Any]]:
        for n in self.chain.get("nodes", []):
            if n.get("node_id") == "E0":
                src = n.get("source", "")
                file_, line_ = self._parse_source(src)
                return {
                    "path": n.get("signal", ""),
                    "in_chain_as": "E0",
                    "hop_count": 0,
                    "role": "symptom",
                    "semantic_relations": [],
                    "source_location": {
                        "file": file_,
                        "line": line_,
                    },
                    "observed_value": n.get("actual", ""),
                    "expected_value": n.get("expected", ""),
                    "waveform_changes": [],
                }
        return None

    def _signal_entry(self, n: Dict[str, Any]) -> Dict[str, Any]:
        src = n.get("source", "")
        file_, line_ = self._parse_source(src)
        relations = self._derive_relations(n)
        hop = self.hop_count(n)
        waveform = self._derive_waveform_changes(n)
        return {
            "path": n.get("signal", ""),
            "in_chain_as": n.get("node_id", ""),
            "hop_count": hop,
            "role": self._infer_role(n),
            "semantic_relations": relations,
            "source_location": {
                "file": file_,
                "line": line_,
            },
            "observed_value": n.get("actual", ""),
            "expected_value": n.get("expected", ""),
            "waveform_changes": waveform,
        }

    def _infer_role(self, n: Dict[str, Any]) -> str:
        """Heuristic role inference; user/decision can override later."""
        ek = n.get("evidence_kind", "")
        rel = (n.get("relation") or "").lower()
        if "reset" in rel:
            return "reset"
        if "mux_select" in rel or "select" in rel:
            return "mux_select"
        if "enable" in rel or "gate" in rel:
            return "enable"
        if "load" in rel and "drive" not in rel:
            return "load"
        if "drive" in rel or "assigned" in rel or ek == "code_inspection":
            return "driver"
        if "condition" in rel or ek == "formal_counterexample":
            return "condition"
        return "driver"

    def _derive_relations(self, n: Dict[str, Any]) -> List[Dict[str, Any]]:
        rel = n.get("relation")
        if not rel:
            return []
        kind = "drive"
        rl = rel.lower()
        for kw in ("mux_select", "enable", "condition", "load", "reset", "clock"):
            if kw in rl:
                kind = kw
                break
        src = n.get("source", "")
        file_, line_ = self._parse_source(src)
        return [{
            "kind": kind,
            "via_node": n.get("node_id", ""),
            "file": file_,
            "line": line_,
            "snippet": rel[:120],
        }]

    def _derive_waveform_changes(self, n: Dict[str, Any]) -> List[Dict[str, Any]]:
        """If snapshots exist for this node, attach them; else empty.

        Returns changes sorted ascending by time, with delta_ns = ns elapsed
        since the previous change (>= 0; first entry delta = 0).
        """
        snapshots_dir = self.session_dir / "1_evidence" / "signal_snapshots"
        nid = n.get("node_id", "")
        # Try common naming conventions
        candidates = [
            snapshots_dir / f"{nid}.json",
            snapshots_dir / f"{nid}_changes.json",
            snapshots_dir / f"{nid}_{n.get('time', '').replace(' ', '_')}.json",
        ]
        snap = next((c for c in candidates if c.is_file()), None)
        if not snap:
            return []
        try:
            data = json.loads(snap.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        # Expect list of {time, value} or {time, value_after_change}
        entries = data.get("changes", data if isinstance(data, list) else [])
        # Parse time + value, then sort ascending
        parsed: List[tuple] = []
        for e in entries:
            t_raw = e.get("time") or e.get("change_time") or ""
            v = e.get("value") or e.get("value_after_change") or ""
            try:
                t_ns = float(t_raw.replace("ns", "").replace("ps", "e-3").replace("us", "e3").split()[0])
            except (ValueError, IndexError):
                t_ns = 0.0
            parsed.append((t_raw, v, t_ns))
        parsed.sort(key=lambda x: x[2])
        # Compute delta from previous entry (>= 0)
        out: List[Dict[str, Any]] = []
        prev_t: Optional[float] = None
        for t_raw, v, t_ns in parsed:
            delta = round(abs(t_ns - prev_t), 3) if prev_t is not None else 0.0
            prev_t = t_ns
            out.append({"time": t_raw, "value": v, "delta_ns": delta})
        return out

    def build_auto_constraints(self) -> List[Dict[str, Any]]:
        """Pick up high-confidence code_inspection nodes — they implicitly
        define the constraints that govern the chain."""
        out = []
        for n in self.chain.get("nodes", []):
            if n.get("evidence_kind") != "code_inspection":
                continue
            if (n.get("confidence") or 0.0) < 0.95:
                continue
            src = n.get("source", "")
            file_, line_ = self._parse_source(src)
            out.append({
                "file": file_,
                "line": line_,
                "chain_node": n.get("node_id", ""),
                "snippet": n.get("actual", ""),
            })
        return out

    def build_toggle_test(self) -> Dict[str, Any]:
        # Pull recent toggle-test verdicts from decision_log
        d_block: Dict[str, Any] = {
            "ran": False,
            "inject": {"command": "", "result": "", "seeds_run": [], "builds_run": []},
            "remove": {"command": "", "result": "", "seeds_run": [], "builds_run": []},
            "counter_example_search": {"ran": False, "findings": []},
        }
        for d in self.decisions.get("decisions", []):
            tag = d.get("tag") or ""
            if tag == "stage4.toggle_test" and d.get("verdict") == "accept":
                d_block["ran"] = True
                d_block["inject"]["result"] = d.get("reason", "reproduced")
                d_block["remove"]["result"] = "removed"
            if tag == "stage4.counter_example":
                d_block["counter_example_search"]["ran"] = True
                d_block["counter_example_search"]["findings"].append({
                    "hypothesis": d.get("hypothesis"),
                    "verdict": d.get("verdict"),
                    "reason": d.get("reason"),
                })
        return d_block

    def build_module_boundary(self) -> Dict[str, Any]:
        out = {"is_local_module_issue": None, "rc_module": "", "propagation_module": ""}
        for d in self.decisions.get("decisions", []):
            tag = d.get("tag") or ""
            if tag == "stage5.module_boundary":
                ev = d.get("evidence_ref", "") or ""
                # crude extraction; user can refine
                if "local" in ev.lower() or "local" in (d.get("reason") or "").lower():
                    out["is_local_module_issue"] = True
                if "cross" in ev.lower() or "cross" in (d.get("reason") or "").lower():
                    out["is_local_module_issue"] = False
        # Derive rc_module from the RC node if present
        rc = self.rc_node()
        if rc:
            sig = rc.get("signal", "")
            # Best-effort: take the first 2 dot-pieces as the module trail.
            parts = sig.split(".")
            if len(parts) >= 2:
                out["rc_module"] = ".".join(parts[:2])
        return out

    def build_artifacts(self) -> Dict[str, Any]:
        return {
            "evidence_chain": str(self.chain_path),
            "decision_log": str(self.decision_log_path),
            "snapshots_dir": str(self.session_dir / "1_evidence" / "signal_snapshots"),
            "repro_dir": str(self.session_dir / "3_repro"),
            "session_dir": str(self.session_dir),
        }

    def build_tool_calls(self) -> List[Dict[str, Any]]:
        """If a tool_calls.json exists at the session level, embed it.
        Otherwise emit an empty list — caller can fill in post-hoc."""
        tc_path = self.session_dir / "1_evidence" / "tool_calls.json"
        if not tc_path.is_file():
            return []
        try:
            data = json.loads(tc_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        if isinstance(data, list):
            return data
        return data.get("calls", [])

    # ---- assemble top-level ----

    def build(self) -> OrderedDict:
        """Return the ordered top-level dict for the RC file."""
        rc_struct = self.build_root_cause()
        le = self.locked_entry()
        top: "OrderedDict[str, Any]" = OrderedDict()
        top["session_id"] = self.chain.get("session_id", "rca_session_unknown")
        top["created_at"] = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
        top["tool_version"] = TOOL_VERSION
        top["locked_entry"] = {
            "time": le.get("time", "") or le.get("timestamp_raw", ""),
            "signal": le.get("signal", ""),
            "actual": le.get("actual", ""),
            "expected": le.get("expected", ""),
            "source": le.get("source", ""),
        }
        top["root_cause"] = {
            "node_id": "RC",
            "signal": rc_struct["signal"],
            "file": rc_struct["file"],
            "line": rc_struct["line"],
            "snippet": rc_struct["snippet"],
            "semantic_kind": rc_struct["semantic_kind"],
            "confidence": rc_struct["confidence"],
        }
        top["causal_signals"] = self.build_causal_signals()
        top["constraints"] = []  # user-supplied; placeholders allowed
        top["auto_constraints"] = self.build_auto_constraints()
        top["reproducer"] = {
            "seeds": [],
            "sequence": "(populated after Stage 4 / 5)",
            "expected_outcome": "(populated after Stage 4 / 5)",
            "expected_when_removed": "(populated after Stage 4 / 5)",
            "building_modes_verified": [],
        }
        top["toggle_test"] = self.build_toggle_test()
        top["module_boundary"] = self.build_module_boundary()
        top["artifacts"] = self.build_artifacts()
        top["tool_calls"] = self.build_tool_calls()
        return top

    def render_yaml(self, top: OrderedDict) -> str:
        em = _YamlEmitter()
        em.emit(top)
        body = em.render()
        # Add a top-of-file notice to prevent hand-edits
        notice = (
            f"# RC File — generated by {TOOL_VERSION}\n"
            f"# DO NOT EDIT BY HAND. Re-run this script to regenerate.\n"
            f"# Hash of source files: {self._source_hash()}\n"
            "\n"
        )
        return notice + body

    def _source_hash(self) -> str:
        """Hash of chain.json + decision_log.json — for tamper detection."""
        h = hashlib.sha256()
        for p in (self.chain_path, self.decision_log_path):
            try:
                h.update(p.read_bytes())
            except OSError:
                h.update(b"(missing)")
        return h.hexdigest()[:12]

    # ---- helpers ----

    @staticmethod
    def _parse_source(src: str) -> tuple:
        """Parse `code:path/to/file.sv:142` / `log:run.log:1247` / `wave:run.fsdb:@8440ns`
        into (file, line:int_or_0)."""
        if not src:
            return "", 0
        try:
            kind, rest = src.split(":", 1)
        except ValueError:
            return "", 0
        # Last :<num> is line (if integer)
        *fs, last = rest.split(":")
        line = 0
        path = rest
        if last.isdigit():
            line = int(last)
            path = ":".join(fs)
        # Strip leading '@<time>' markers
        path = path.lstrip("@")
        return path, line

    @staticmethod
    def _read_snippet(file_: str, line_: int, context: int = 2) -> str:
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


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def cmd_build(args) -> int:
    session = Path(args.session_dir).resolve()
    chain_p = Path(args.chain).resolve() if args.chain else (session / "1_evidence" / "evidence_chain.json")
    dec_p = Path(args.decision_log).resolve() if args.decision_log else (session / "2_decisions" / "decision_log.json")
    out_p = Path(args.out).resolve() if args.out else (session / "9_output" / "RC_file.yaml")
    out_p.parent.mkdir(parents=True, exist_ok=True)

    builder = RCFileBuilder(session, chain_p, dec_p)
    try:
        builder.load()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    top = builder.build()
    yaml_text = builder.render_yaml(top)
    out_p.write_text(yaml_text, encoding="utf-8")
    print(f"wrote: {out_p}")
    if args.verify:
        # Re-render and compare to existing — disabled by request.
        pass
    return 0


def cmd_verify(args) -> int:
    """Verify that the on-disk RC_file.yaml is byte-identical to a fresh render."""
    session = Path(args.session_dir).resolve()
    out_p = Path(args.out).resolve() if args.out else (session / "9_output" / "RC_file.yaml")
    if not out_p.is_file():
        print(f"RC file not found: {out_p}", file=sys.stderr)
        return 2
    builder = RCFileBuilder(session)
    try:
        builder.load()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    # Drop `created_at` because it changes per invocation.
    top = builder.build()
    top["created_at"] = "(verification-skip)"
    fresh = builder.render_yaml(top)
    on_disk = out_p.read_text(encoding="utf-8")
    # Replace the "created_at" line in on_disk to compare apples-to-apples.
    on_disk_lines = on_disk.split("\n")
    for i, ln in enumerate(on_disk_lines):
        if ln.startswith("created_at:"):
            on_disk_lines[i] = "created_at: (verification-skip)"
    on_disk_normalized = "\n".join(on_disk_lines)
    if fresh == on_disk_normalized:
        print("OK: RC file matches script-generated output.")
        return 0
    print("MISMATCH: re-run `python3 scripts/build_rc_file.py <session>` to regenerate.",
          file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate RC_file.yaml from chain+decision JSON.")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("build", help="Build a fresh RC_file.yaml.")
    sp.add_argument("session_dir")
    sp.add_argument("--chain", default=None)
    sp.add_argument("--decision-log", default=None)
    sp.add_argument("--out", default=None)
    sp.add_argument("--verify", action="store_true",
                    help="Reserved; currently a no-op.")
    sp.set_defaults(func=cmd_build)

    sp = sub.add_parser("verify", help="Verify on-disk RC_file.yaml matches script output.")
    sp.add_argument("session_dir")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_verify)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
