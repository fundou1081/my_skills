#!/usr/bin/env python3
"""
trace_one.py — CLI: 跑 trace, 输出 JSON

用法:
    python scripts/trace_one.py <file.sv> <signal>
    python scripts/trace_one.py test.sv count
    python scripts/trace_one.py path/to/design.sv reg2hw.ctrl.tx.q
"""
import argparse
import json
import sys
from pathlib import Path

from signal_tracer import SignalTracer


def main():
    ap = argparse.ArgumentParser(
        description="Run sv-trace on a single .sv file, output JSON to stdout."
    )
    ap.add_argument("file", type=Path, help="Path to .sv file")
    ap.add_argument("signal", help="Signal name to trace (e.g. 'count' or 'top.u_mid.x')")
    ap.add_argument(
        "--verify", action="store_true", default=True,
        help="Run trace_verified() with credibility (default: True)"
    )
    ap.add_argument("--no-verify", dest="verify", action="store_false")
    args = ap.parse_args()

    if not args.file.exists():
        print(f"ERROR: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    code = args.file.read_text()

    t = SignalTracer()
    t.add_file(str(args.file), code)
    t.build()

    if args.verify:
        result = t.trace_verified(args.signal)
    else:
        result = t.trace(args.signal)

    output = {
        "file": str(args.file),
        "signal": args.signal,
        "verified": args.verify,
        "drivers": [d.to_context().to_dict() for d in result.drivers],
        "loads":   [l.to_context().to_dict() for l in result.loads],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
