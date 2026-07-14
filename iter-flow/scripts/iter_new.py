#!/usr/bin/env python3
"""iter_new.py — Create the next iter_NN_<title>.md from template.

Usage:
    python3 scripts/iter_new.py <task_dir> --title "<verb-noun hypothesis>"

Behavior:
    - Auto-detects the next N from existing iter_NN_*.md files in <task_dir>.
      Use zero-fill (iter_01..iter_09..iter_10..iter_99..) for proper sort.
    - Renders from assets/templates/iter_template.md.
    - Auto-fills the "回顾引用" header with placeholders for the user to
      fill in (we don't auto-extract from prior iter because that's the
      user's judgement, per skill rule #3 — "把相关结论摘入新文件").

Examples:
    python3 scripts/iter_new.py experiments/debug_502_spike \
        --title "连接池耗尽假设" --hypothesis "当请求 > 5000/min 时连接池耗尽, 触发 502" \
        --scripts "scripts/check_conn_pool.sh" --env "prod i-0a1b"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path
from typing import List, Optional


TEMPLATE_PATH_DEFAULT = Path(__file__).resolve().parent.parent / "assets" / "templates" / "iter_template.md"

ITER_FILENAME_RE = re.compile(r"^iter_(\d{2,3})_(.+)\.md$", re.UNICODE)


def _now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _fill(template: str, replacements: Dict[str, str]) -> str:
    out = template
    for k, v in replacements.items():
        out = out.replace(f"{{{{{k}}}}}", v)
    return out


def _existing_iters(task_dir: Path) -> List[int]:
    nums: List[int] = []
    for p in task_dir.glob("iter_*.md"):
        m = ITER_FILENAME_RE.match(p.name)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def _next_iter_num(task_dir: Path) -> int:
    nums = _existing_iters(task_dir)
    return (max(nums) + 1) if nums else 1


def _safe_title(raw: str) -> str:
    """Coerce user title to a slug suitable for a filename. ASCII only by default;
    CJK names preserved when user explicitly uses non-ASCII."""
    raw = raw.strip()
    # Replace spaces and CJK punctuation with hyphens
    s = re.sub(r"[\s/]+", "-", raw)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s or "untitled"


def cmd_new(args) -> int:
    task_dir = Path(args.task_dir).resolve()
    if not task_dir.is_dir():
        print(f"task dir not found: {task_dir}", file=sys.stderr)
        return 2
    if not (task_dir / "card.md").exists():
        print(f"no card.md in {task_dir} -- run iter_init.py first.", file=sys.stderr)
        return 2

    n = args.number if args.number is not None else _next_iter_num(task_dir)
    nn = f"{n:02d}"
    safe = _safe_title(args.title)
    out_name = f"iter_{nn}_{safe}.md"
    out_path = task_dir / out_name
    if out_path.exists() and not args.force:
        print(f"file already exists: {out_path}  (pass --force to overwrite)", file=sys.stderr)
        return 3

    template = TEMPLATE_PATH_DEFAULT.read_text(encoding="utf-8")
    prev_nums = _existing_iters(task_dir)
    review_refs_lines = []
    if prev_nums:
        last = prev_nums[-3:]
        for i in last:
            review_refs_lines.append(f"- iter_{i:02d} → 见 `iter_{i:02d}_*.md` 的 §目的 + §Findings")
        review_refs_lines.append("")
        review_refs_lines.append("(复制前 3 轮的关键结论到上方, 不要写 '见上轮'。)")
    else:
        review_refs_lines.append("- 首轮 iter, 没有历史回顾.")
    review_refs = "\n".join(review_refs_lines)

    content = _fill(
        template,
        {
            "ITER_NUM": str(n),
            "TITLE": args.title,
            "REVIEW_REFS": review_refs,
            "HYPOTHESIS_STATEMENT": args.hypothesis or "(formulate as a falsifiable statement)",
            "SCRIPTS": args.scripts or "(scripts/iter_" + nn + "_xxx.sh — to be written)",
            "SCRIPTS_DIR": "scripts/",
            "ENV_DESCRIPTION": args.env or "(prod / staging / local — describe instances and time window)",
            "TIME_WINDOW": args.time_window or "(time window for this iter's data)",
            "CODE_CHANGE_NOTE": "(none — pure read) — OR list the commit if a code change is part of this iter",
            "EXEC_CMD": args.exec_cmd or "(fill after scripts/ is ready)",
            "METRIC_1": args.metric or "(first key metric)",
            "METRIC_2": "(second)",
            "METRIC_3": "(third)",
            "PASS_CRITERIA": args.pass_criteria or "(a specific, measurable criterion)",
            "TERMINATION_CRITERIA": args.termination or "(if PASS is achieved, conclude this iter; if 2 hours spent without progress, scope down)",
            "NEXT_ITER": f"{n + 1:02d}",
            "RESULT_LINE_1": "(fill after running)",
            "RESULT_LINE_2": "(fill after running)",
        },
    )

    out_path.write_text(content, encoding="utf-8")
    print(f"wrote: {out_path}")
    print()
    print("Next:")
    print(f"  1. Edit §目的 and §实验条件 to your situation.")
    print(f"  2. Write the script(s) referenced in §实验条件 BEFORE running them.")
    print(f"  3. After running, fill §结果, then §Findings, then §决策.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create the next iter_NN_<title>.md for an iter-flow task.")
    p.add_argument("task_dir", help="Path to the task dir, e.g. experiments/debug_502_spike/")
    p.add_argument("--title", required=True,
                   help="Concise title for the iter (verb-noun hypothesis preferred).")
    p.add_argument("--number", type=int, default=None,
                   help="Force a specific iter number (default: auto-detect from existing files).")
    p.add_argument("--hypothesis", default=None,
                   help="One-line falsifiable hypothesis statement.")
    p.add_argument("--scripts", default=None,
                   help="Comma-list of scripts (e.g. 'check_conn.sh,fetch_threads.sh').")
    p.add_argument("--env", default=None,
                   help="Environment description (prod / staging / etc.).")
    p.add_argument("--time-window", default=None,
                   help="Time window this iter covers.")
    p.add_argument("--exec-cmd", default=None,
                   help="Exact command to run for §检查方法.")
    p.add_argument("--metric", default=None,
                   help="Primary metric to observe.")
    p.add_argument("--pass-criteria", default=None,
                   help="What counts as PASS for this iter.")
    p.add_argument("--termination", default=None,
                   help="When to abandon this hypothesis and proceed to iter_N+1.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite an existing iter_NN file (DESTRUCTIVE).")
    p.set_defaults(func=cmd_new)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
