#!/usr/bin/env python3
"""iter_review.py — Summarize the most recent 3 iters for the §回顾引用 section.

Usage:
    python3 scripts/iter_review.py <task_dir>

Output:
    For each of the last 3 iter_NN_*.md files in <task_dir>:
      - iter ID
      - title
      - §目的 (one-line summary)
      - §Findings (last few lines, often a one-liner conclusion)
      - §决策 (which option is checked)

Exit code:
    0: at least one iter found
    1: no iter files in task_dir
    2: task_dir not found
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


ITER_FILENAME_RE = re.compile(r"^iter_(\d{2,3})_(.+)\.md$", re.UNICODE)


def _extract_section(text: str, heading: str) -> str:
    """Return the body of a markdown section `## <heading>` until the next ## header."""
    pat = re.compile(rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)", re.M | re.S)
    m = pat.search(text)
    return m.group(1).strip() if m else ""


def _shorten(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else (s[: n - 1] + "…")


def _find_checked(text: str) -> List[str]:
    """Find which decision checkbox (if any) is checked in §决策."""
    checked = []
    # Match lines like "- [x] 启动 iter_NN" but we use [ ] in our template, so
    # ALSO accept lines starting with "**" or "[DONE]" as a soft signal.
    section = _extract_section(text, "决策")
    if not section:
        return []
    out = []
    for ln in section.splitlines():
        ln_strip = ln.strip()
        if not ln_strip:
            continue
        # Checked box
        if ln_strip.startswith("- [x]") or ln_strip.startswith("- [X]"):
            out.append("✓ " + ln_strip.split("]", 1)[1].strip())
            continue
        # Our template uses "[ ]" by default; treat "[DONE]" or "**DONE**" as sentinel
        if "[DONE]" in ln_strip or "**DONE**" in ln_strip or "[完成]" in ln_strip:
            out.append("✓ " + ln_strip)
    return out


def _summarize_one(path: Path) -> Tuple[str, str, str, str, str, List[str]]:
    """Return (id, title, purpose, findings, decision_block, decision_checked)."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^#\s+iter_(\d{2,3}):\s*(.+?)\s*$", text.splitlines()[0])
    if m:
        nid = f"iter_{m.group(1)}"
        title = m.group(2).strip()
    else:
        nid = path.stem
        title = path.name
    purpose = _extract_section(text, "目的").replace("\n", " ").strip()
    findings = _extract_section(text, "Findings").strip()
    decision = _extract_section(text, "决策").strip()
    checked = _find_checked(text)
    return nid, title, purpose, findings, decision, checked


def cmd_review(args) -> int:
    task_dir = Path(args.task_dir).resolve()
    if not task_dir.is_dir():
        print(f"task dir not found: {task_dir}", file=sys.stderr)
        return 2
    iters = sorted(task_dir.glob("iter_*.md"),
                   key=lambda p: int(ITER_FILENAME_RE.match(p.name).group(1)) if ITER_FILENAME_RE.match(p.name) else 0)
    if not iters:
        print(f"# No iter files in {task_dir}", file=sys.stderr)
        return 1
    last = iters[-3:]
    print(f"# iter-flow review -- {task_dir}")
    print(f"# Found {len(iters)} iter(s) total, summarizing last {len(last)}")
    print("=" * 70)
    for path in last:
        nid, title, purpose, findings, decision, checked = _summarize_one(path)
        print()
        print(f"## {nid} -- {title}")
        if purpose:
            print(f"  目的  : {_shorten(purpose, 220)}")
        if findings:
            print(f"  Findings: {_shorten(findings, 220)}")
        else:
            print(f"  Findings: (not yet filled)")
        if checked:
            print(f"  决策  : {' | '.join(checked[:1])}")
        else:
            print(f"  决策  : (no checkbox yet)")
    print()
    print("=" * 70)
    print("# COPY THESE into the new iter's §回顾引用 section (DO NOT write 'see above').")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Summarize the last 3 iter files for §回顾引用 population.")
    p.add_argument("task_dir", help="Path to the task dir, e.g. experiments/debug_502_spike/")
    p.set_defaults(func=cmd_review)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
