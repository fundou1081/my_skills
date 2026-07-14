#!/usr/bin/env python3
"""iter_init.py — Create a new iter-flow task directory + card.md.

Usage:
    python3 scripts/iter_init.py <task_name> [options]

Examples:
    python3 scripts/iter_init.py debug_502_spike
    python3 scripts/iter_init.py perf_p99_investigation \
        --workdir ~/proj/foo \
        --background "P99 在 14:00 后从 200ms 涨到 800ms" \
        --hypotheses "连接池耗尽|慢 SQL 阻塞|网络抖动"

Outputs:
    <workdir>/experiments/<task_name>/
    ├── card.md          (from assets/templates/card.md.template)
    ├── scripts/
    └── data/

Side-effects:
    - Creates directories if missing (idempotent for repeats)
    - Refuses to overwrite an existing card.md without --force
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import shutil
import sys
from pathlib import Path
from typing import List


TEMPLATE_PATH_DEFAULT = Path(__file__).resolve().parent.parent / "assets" / "templates" / "card.md.template"


def _now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _placeholder(name: str, fallback: str = "(populate)") -> str:
    return f"{{{{{name}}}}}" if fallback == "(populate)" else fallback


def _fill_template(template: str, replacements: Dict[str, str]) -> str:
    out = template
    for k, v in replacements.items():
        out = out.replace(f"{{{{{k}}}}}", v)
    return out


def cmd_init(args) -> int:
    task_name = args.task_name
    workdir = Path(args.workdir).resolve()
    experiments = workdir / "experiments" / task_name
    # Idempotent
    if experiments.exists():
        if not args.force and not (experiments / "card.md").exists():
            pass  # OK to fill in remaining pieces
        elif not args.force:
            print(f"task already exists: {experiments}", file=sys.stderr)
            print(f"  pass --force to overwrite (DESTRUCTIVE).", file=sys.stderr)
            return 2
    experiments.mkdir(parents=True, exist_ok=True)
    (experiments / "scripts").mkdir(exist_ok=True)
    (experiments / "data").mkdir(exist_ok=True)

    # Build card.md from template
    template = TEMPLATE_PATH_DEFAULT.read_text(encoding="utf-8")
    hypotheses = args.hypotheses.split("|") if args.hypotheses else ["(populate)", "(populate)", "(populate)"]
    # Pad to 3 entries so the template renders predictably
    while len(hypotheses) < 3:
        hypotheses.append("")

    card_md = _fill_template(
        template,
        {
            "TASK_TITLE": task_name.replace("-", " ").replace("_", " ").title(),
            "CREATED_AT": _now_iso(),
            "CURRENT_ITER": "00",
            "STATUS": "open",
            "BACKGROUND": args.background or _placeholder("BACKGROUND"),
            "TIME_WINDOW": args.time_window or _placeholder("TIME_WINDOW"),
            "SCOPE": args.scope or _placeholder("SCOPE"),
            "USER_PERCEPTION": args.user_perception or _placeholder("USER_PERCEPTION"),
            "HYPOTHESIS_1": hypotheses[0] or _placeholder("HYPOTHESIS_1"),
            "HYPOTHESIS_2": hypotheses[1] or _placeholder("HYPOTHESIS_2"),
            "HYPOTHESIS_3": hypotheses[2] or _placeholder("HYPOTHESIS_3"),
            "NEXT_ACTION_1": _placeholder("NEXT_ACTION_1"),
            "NEXT_ACTION_2": _placeholder("NEXT_ACTION_2"),
        },
    )

    card_path = experiments / "card.md"
    if card_path.exists() and not args.force:
        print(f"refusing to overwrite existing card.md (use --force): {card_path}",
              file=sys.stderr)
        return 3
    card_path.write_text(card_md, encoding="utf-8")
    print(f"wrote: {card_path}")
    print(f"created: {experiments}/  (with scripts/, data/)")
    print()
    print("Next steps:")
    print(f"  1. Review and edit: {card_path}")
    print(f"  2. Start first iter:")
    print(f"     python3 scripts/iter_new.py {experiments} --title \"<verb-noun>\"")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Initialize an iter-flow task: card.md + scripts + data dirs.")
    p.add_argument("task_name", help="Kebab-case task name, e.g. 'debug-502-spike'.")
    p.add_argument("--workdir", default=".", help="Parent workdir (default: cwd).")
    p.add_argument("--background", default=None,
                   help="3-5 lines describing the symptom/impact/time window.")
    p.add_argument("--time-window", default=None,
                   help="Free-text: '14:00-14:30 GMT+8' or 'since deploy v3.2' etc.")
    p.add_argument("--scope", default=None,
                   help="Free-text: 'prod i-0a1b' or 'all apb_* IPs' etc.")
    p.add_argument("--user-perception", default=None,
                   help="Free-text: 5xx rate, latency, error message, etc.")
    p.add_argument("--hypotheses", default=None,
                   help='Pipe-separated list, e.g. "h1|h2|h3" (top 3).')
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing card.md (DESTRUCTIVE).")
    p.set_defaults(func=cmd_init)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
