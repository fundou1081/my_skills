#!/usr/bin/env python3
"""
dump_chain.py — 递归 dump driver 链 (M5.1f)

用法:
    python scripts/dump_chain.py <file.sv> <signal>
    python scripts/dump_chain.py test.sv count --depth 5
    python scripts/dump_chain.py path/to/design.sv reg2hw.ctrl.tx.q --depth 3
"""
import argparse
import json
import sys
from pathlib import Path

from signal_tracer import SignalTracer


def main():
    ap = argparse.ArgumentParser(
        description="Dump recursive driver chain for a signal."
    )
    ap.add_argument("file", type=Path, help="Path to .sv file")
    ap.add_argument("signal", help="Signal name to trace")
    ap.add_argument(
        "--depth", type=int, default=10,
        help="Max chain depth (default: 10)"
    )
    ap.add_argument(
        "--direction", choices=["driver", "load"], default="driver",
        help="Trace direction: driver (upstream) or load (downstream) (default: driver)"
    )
    args = ap.parse_args()

    if not args.file.exists():
        print(f"ERROR: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    code = args.file.read_text()
    t = SignalTracer()
    t.add_file(str(args.file), code)
    t.build()

    if args.direction == "driver":
        dump = t.dump_driver_chain(args.signal, max_depth=args.depth)
    else:
        dump = t.dump_load_chain(args.signal, max_depth=args.depth)

    output = {
        "file": str(args.file),
        "signal": args.signal,
        "direction": args.direction,
        "max_depth": args.depth,
        "chain": dump,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
