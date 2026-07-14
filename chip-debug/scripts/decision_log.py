#!/usr/bin/env python3
"""decision_log.py — Manage decision_log.json for chip-debug RCA sessions.

The decision log captures every hypothesis explored, every branch taken,
and every rejection — with reason. It is the audit-trail companion to
`evidence_chain.py`.

Usage
-----
    init     <session_dir>                  Initialize a fresh log under a session dir.
    add      <log.json> [flags]             Append a decision entry.
    show     <log.json>                     Pretty-print the log.
    summary  <log.json>                     Counts by verdict + recent entries.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0"
VALID_VERDICTS = {"accept", "reject", "park", "supersede"}


# -----------------------------------------------------------------------------
# Operations
# -----------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def cmd_init(args) -> int:
    log_path = os.path.join(args.session_dir, "2_decisions", "decision_log.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    if os.path.exists(log_path) and not args.force:
        print(f"refusing to overwrite existing {log_path}; pass --force", file=sys.stderr)
        return 2
    skeleton = {
        "schema_version": SCHEMA_VERSION,
        "session_id": f"rca_session_{args.session_dir.rstrip('/').split('/')[-1]}",
        "created_at": _now_iso(),
        "decisions": [],
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(skeleton, f, indent=2, ensure_ascii=False)
    print(f"initialized: {log_path}")
    return 0


def cmd_add(args) -> int:
    if args.verdict not in VALID_VERDICTS:
        print(f"verdict must be one of {VALID_VERDICTS}; got {args.verdict!r}", file=sys.stderr)
        return 2

    log_path = args.log
    if not os.path.isfile(log_path):
        print(f"decision log not found: {log_path}; run `init` first.", file=sys.stderr)
        return 2
    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    decision_id = args.decision_id or f"D-{uuid.uuid4().hex[:8]}"
    entry: Dict[str, Any] = {
        "decision_id": decision_id,
        "timestamp": _now_iso(),
        "hypothesis": args.hypothesis,
        "evidence_ref": args.evidence_ref,
        "verdict": args.verdict,
        "reason": args.reason,
        "tag": args.tag,
    }
    log["decisions"].append(entry)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"appended decision {decision_id} ({args.verdict}) -> {log_path}")
    return 0


def cmd_show(args) -> int:
    if not os.path.isfile(args.log):
        print(f"log not found: {args.log}", file=sys.stderr)
        return 2
    with open(args.log, "r", encoding="utf-8") as f:
        log = json.load(f)
    print(f"# session : {log.get('session_id', '?')}")
    print(f"# schema  : v{log.get('schema_version', '?')}  decisions={len(log.get('decisions', []))}")
    print("-" * 78)
    for d in log.get("decisions", []):
        print(f"[{d.get('decision_id'):>12}] {d.get('timestamp')}  verdict={d.get('verdict'):<8}  tag={d.get('tag') or '-'}")
        print(f"     hypothesis : {d.get('hypothesis')}")
        if d.get("evidence_ref"):
            print(f"     evidence   : {d.get('evidence_ref')}")
        if d.get("reason"):
            print(f"     reason     : {d.get('reason')}")
        print()
    return 0


def cmd_summary(args) -> int:
    if not os.path.isfile(args.log):
        print(f"log not found: {args.log}", file=sys.stderr)
        return 2
    with open(args.log, "r", encoding="utf-8") as f:
        log = json.load(f)
    counts: Dict[str, int] = {}
    for d in log.get("decisions", []):
        counts[d.get("verdict", "?")] = counts.get(d.get("verdict", "?"), 0) + 1
    print(f"# decision log summary  total={len(log.get('decisions', []))}")
    for v in sorted(counts):
        print(f"  {v:<10} {counts[v]}")
    if args.recent:
        print()
        print("# last 5 decisions:")
        for d in log.get("decisions", [])[-5:]:
            print(f"  [{d.get('decision_id'):>12}] {d.get('timestamp')}  {d.get('verdict'):<8}  {d.get('hypothesis')[:80]}")
    return 0


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Decision-log manager for chip-debug RCA.")
    sub = p.add_subparsers(dest="command", required=True)

    # init
    sp = sub.add_parser("init")
    sp.add_argument("session_dir")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_init)

    # add
    sp = sub.add_parser("add")
    sp.add_argument("log", help="Path to decision_log.json")
    sp.add_argument("--hypothesis", required=True,
                    help="Short, falsifiable statement of what we're testing.")
    sp.add_argument("--evidence-ref", default=None,
                    help="Reference to a chain node_id or external evidence.")
    sp.add_argument("--verdict", required=True, choices=sorted(VALID_VERDICTS))
    sp.add_argument("--reason", required=True,
                    help="WHY we accept/reject/park this hypothesis.")
    sp.add_argument("--tag", default=None,
                    help="Optional category tag (e.g. 'stage2.L1', 'toggle-test').")
    sp.add_argument("--decision-id", default=None,
                    help="Optional override (default: auto-generated).")
    sp.set_defaults(func=cmd_add)

    # show
    sp = sub.add_parser("show")
    sp.add_argument("log")
    sp.set_defaults(func=cmd_show)

    # summary
    sp = sub.add_parser("summary")
    sp.add_argument("log")
    sp.add_argument("--recent", action="store_true",
                    help="Show last 5 decisions.")
    sp.set_defaults(func=cmd_summary)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
