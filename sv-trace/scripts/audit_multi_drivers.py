#!/usr/bin/env python3
"""
audit_multi_drivers.py — 扫目录下所有 .sv 的多驱动, 输出 JSON

用法:
    python scripts/audit_multi_drivers.py <dir>
    python scripts/audit_multi_drivers.py ./rtl
    python scripts/audit_multi_drivers.py /path/to/opentitan/hw/ip/uart/rtl
"""
import argparse
import json
import sys
from pathlib import Path

from signal_tracer import SignalTracer


def main():
    ap = argparse.ArgumentParser(
        description="Scan a directory of .sv files and report multi-driver conflicts."
    )
    ap.add_argument("dir", type=Path, help="Directory to scan (recursive)")
    ap.add_argument(
        "--pattern", default="*.sv",
        help="Glob pattern (default: *.sv)"
    )
    ap.add_argument(
        "--min-drivers", type=int, default=2,
        help="Min drivers to count as multi-driver (default: 2)"
    )
    args = ap.parse_args()

    if not args.dir.is_dir():
        print(f"ERROR: {args.dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    files = sorted(args.dir.rglob(args.pattern))
    if not files:
        print(f"ERROR: no files match {args.pattern} in {args.dir}", file=sys.stderr)
        sys.exit(1)

    t = SignalTracer()
    for f in files:
        try:
            t.add_file(str(f), f.read_text())
        except Exception as e:
            print(f"WARN: skip {f}: {e}", file=sys.stderr)
            continue
    t.build()

    multi = t.find_multi_drivers()
    # filter by min-drivers
    multi = {sig: ds for sig, ds in multi.items() if len(ds) >= args.min_drivers}

    summary = t.dump_multi_drivers(summary_only=True)

    output = {
        "scanned_dir": str(args.dir),
        "files_scanned": len(files),
        "min_drivers": args.min_drivers,
        "summary": summary,
        "conflicts": [
            {
                "signal": sig,
                "driver_count": len(ds),
                "drivers": [d.to_context().to_dict() for d in ds],
            }
            for sig, ds in sorted(multi.items())
        ],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
