#!/usr/bin/env python3
"""parse_uvm_log.py — Find the earliest anomaly in a simulation log.

Designed as Stage-1 (Lock the error entry) evidence source for the
`chip-debug` RCA workflow. Tries to be tolerant of mixed log formats
(VCS / Questa / Xcelium / Verilator / Vivado xsim) while remaining
dependency-free (stdlib only).

Usage examples
--------------
    # First error only, JSON to stdout
    python3 parse_uvm_log.py run.log --first-error --format json

    # All errors with 5 lines of context, pretty text
    python3 parse_uvm_log.py run.log --all-errors --context 5

    # Auto-detect simulator by file marker
    python3 parse_uvm_log.py trace.log --format auto --first-error

    # CSV for downstream scripts
    python3 parse_uvm_log.py run.log --all-errors --format csv

Notes
-----
- Timestamps are extracted from leading prefixes like `[12345 ns]`,
  `<12345 ns>`, `T=12345ns`. If multiple errors fire near-simultaneously
  they are all returned; pick the deepest hierarchical path for the
  primary L1 target.
- This script does NOT decide root causes — it only produces structured
  evidence. The agent must apply the chip-debug discipline on top.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Iterable, List, Optional


# -----------------------------------------------------------------------------
# Severity patterns — keep these conservative. Order matters: more specific
# classes (UVM_FATAL) come before generic ERROR.
# -----------------------------------------------------------------------------

SEVERITIES: List[tuple] = [
    # (canonical_label, regex)
    ("UVM_FATAL",  re.compile(r"\bUVM_FATAL\b")),
    ("UVM_ERROR",  re.compile(r"\bUVM_ERROR\b")),
    ("UVM_WARNING",re.compile(r"\bUVM_WARNING\b")),
    ("SVA_FAIL",   re.compile(r"\b(?:SVA|Assertion)\s*(?:fail|failure|failed)\b", re.I)),
    ("FATAL",      re.compile(r"\bFATAL\s*:", re.I)),
    ("ERROR",      re.compile(r"^(?:[^a-zA-Z])\s*(?:ERROR|Error)\b|^\s*\*\*\s*Error\b")),
    ("FSDB_ERROR", re.compile(r"\bFSDB\s*Error\b", re.I)),
]

# Timestamp patterns. Order: explicit units first, then bare integers with
# a space suffix. Each pattern has named groups.
TIME_PATTERNS: List[tuple] = [
    # [12345 ns]
    re.compile(r"\[(?P<time>\d+(?:\.\d+)?)\s*(?P<unit>ns|ps|us|fs|ms|simstep|cycles?)\]"),
    # <12345 ns>
    re.compile(r"<(?P<time>\d+(?:\.\d+)?)\s*(?P<unit>ns|ps|us|fs|ms|simstep|cycles?)>"),
    # T=12345ns or time=12345ns
    re.compile(r"\b[Tt](?:ime)?\s*=\s*(?P<time>\d+(?:\.\d+)?)\s*(?P<unit>ns|ps|us|fs|ms|simstep|cycles?)"),
    # 12345 ns (space-separated, must be early on the line)
    re.compile(r"^\s*(?P<time>\d+(?:\.\d+)?)\s*(?P<unit>ns|ps|us|fs|ms|simstep|cycles?)\b"),
]

# Hierarchical path patterns. Greedy on dotted names then bounded by index.
HIER_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?P<path>(?:tb|testbench|tb\.|env\.|dut\.|cpu\.|core\.|soc\.)[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*|\[[^\]]+\])*)\b"),
    re.compile(r"\bid\s*=\s*\"(?P<path>[^\"]+)\""),
]

# File:line patterns emitted by VCS / Questa / Xcelium / Verilator.
FILE_LINE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?P<file>[^:\s]+\.(?:sv|v|vh|svh))\s*[:](?P<line>\d+)"),
    re.compile(r"\b(?:at|file=)\s*(?P<file>[^:\s]+\.(?:sv|v|vh|svh))(?::(?P<line>\d+))?"),
]


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------

@dataclass
class LogError:
    """A single anomalous log line."""
    line_no: int
    raw: str
    severity: str
    timestamp_ns: Optional[float]  # normalized to nanoseconds if possible
    timestamp_raw: Optional[str]   # original representation
    hier_path: Optional[str]
    file: Optional[str]
    file_line: Optional[int]
    message: str
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------

UNIT_TO_NS = {
    "ns": 1.0,
    "us": 1_000.0,
    "ms": 1_000_000.0,
    "ps": 0.001,
    "fs": 0.000001,
    "simstep": 1.0,   # treat as ns-equivalent
    "cycle": 1.0,     # treat as ns-equivalent; real mapping is design-specific
    "cycles": 1.0,
}


def detect_format(text: str) -> str:
    """Sniff the simulator/log kind from markers in the head of the file."""
    head = "\n".join(text.splitlines()[:200]).lower()
    markers = {
        "vcs":     ["synopsys vcs", "vcs simulator", "$vcs_version"],
        "questa":  ["modelsim", "questa", "vsim", "vlog"],
        "xcelium": ["xcelium", "xrun", "ncsim", "irun"],
        "verilator":["verilator"],
        "vivado":  ["vivado", "xsim"],
    }
    for kind, words in markers.items():
        if any(w in head for w in words):
            return kind
    return "generic"


def extract_timestamp(line: str) -> tuple[Optional[float], Optional[str]]:
    """Return (time_ns, original_string)."""
    for pat in TIME_PATTERNS:
        m = pat.search(line)
        if m:
            try:
                value = float(m.group("time"))
            except (TypeError, ValueError):
                continue
            unit = m.group("unit").lower()
            scale = UNIT_TO_NS.get(unit, 1.0)
            return value * scale, m.group(0)
    return None, None


def extract_hier(line: str) -> Optional[str]:
    """Return the longest matching hierarchical path or None."""
    candidates: List[str] = []
    for pat in HIER_PATTERNS:
        for m in pat.finditer(line):
            path = m.group("path") if "path" in m.groupdict() else m.group(0)
            if path and "." in path:
                candidates.append(path)
    if not candidates:
        return None
    # Prefer the longest (most qualified)
    return max(candidates, key=len)


def extract_file_line(line: str) -> tuple[Optional[str], Optional[int]]:
    for pat in FILE_LINE_PATTERNS:
        m = pat.search(line)
        if m:
            return m.group("file"), int(m.group("line")) if m.group("line") else None
    return None, None


def extract_severity(line: str) -> Optional[str]:
    for label, pat in SEVERITIES:
        if pat.search(line):
            return label
    return None


def parse_message(line: str, severity_pat: re.Pattern) -> str:
    """Return the message body after the severity marker."""
    m = severity_pat.search(line)
    if not m:
        return line.strip()
    return line[m.end():].strip(" :-\t")


def _iter_with_context(lines: List[str], context: int) -> Iterable[tuple[int, List[str], str, List[str]]]:
    """Yield (line_no, before, current, after) tuples for each error line.

    before / after are bounded by `context`. "before" is in document order
    (oldest at index 0); "after" likewise.
    """
    n = len(lines)
    for i, line in enumerate(lines):
        sev = extract_severity(line)
        if sev is None:
            continue
        before = lines[max(0, i - context):i]
        after  = lines[i + 1:i + 1 + context]
        yield i + 1, before, line, after


def parse_log(text: str, context: int = 0) -> List[LogError]:
    """Parse a log file body, return all error/warning entries as LogError."""
    lines = text.splitlines()
    out: List[LogError] = []

    for line_no, before, current, after in _iter_with_context(lines, context):
        sev = extract_severity(current)
        if sev is None or sev == "UVM_WARNING":
            # warnings are intentionally filtered unless explicitly asked
            continue
        ts_ns, ts_raw = extract_timestamp(current)
        hier = extract_hier(current)
        file, fline = extract_file_line(current)
        # pick the right severity pattern to slice message
        sev_pat = next(p for lbl, p in SEVERITIES if lbl == sev)
        msg = parse_message(current, sev_pat)
        out.append(LogError(
            line_no=line_no,
            raw=current.rstrip(),
            severity=sev,
            timestamp_ns=ts_ns,
            timestamp_raw=ts_raw,
            hier_path=hier,
            file=file,
            file_line=fline,
            message=msg,
            context_before=before,
            context_after=after,
        ))
    return out


# -----------------------------------------------------------------------------
# Output formatting
# -----------------------------------------------------------------------------

def fmt_text(errors: List[LogError], first_only: bool) -> str:
    if not errors:
        return "No UVM_ERROR / UVM_FATAL / SVA failure detected.\n"
    buf = io.StringIO()
    items = errors[:1] if first_only else errors
    for i, e in enumerate(items, 1):
        buf.write(f"--- [{i}/{len(items)}] {e.severity} @ {e.timestamp_raw or 'N/A'} ---\n")
        buf.write(f"  line   : {e.line_no}\n")
        if e.timestamp_ns is not None:
            buf.write(f"  ts_ns  : {e.timestamp_ns:g}\n")
        if e.hier_path:
            buf.write(f"  hier   : {e.hier_path}\n")
        if e.file:
            buf.write(f"  file   : {e.file}:{e.file_line}\n")
        buf.write(f"  msg    : {e.message}\n")
        if (e.context_before or e.context_after) and not first_only:
            if e.context_before:
                buf.write("  before :\n")
                for ln in e.context_before:
                    buf.write(f"           | {ln}\n")
            if e.context_after:
                buf.write("  after  :\n")
                for ln in e.context_after:
                    buf.write(f"           | {ln}\n")
        buf.write("\n")
    if first_only and len(errors) > 1:
        buf.write(f"(+{len(errors) - 1} more errors not shown; rerun with --all-errors)\n")
    return buf.getvalue()


def fmt_json(errors: List[LogError], first_only: bool, log_path: str) -> str:
    items = errors[:1] if first_only else errors
    payload = {
        "log_file": log_path,
        "n_total": len(errors),
        "n_returned": len(items),
        "errors": [e.to_dict() for e in items],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def fmt_csv(errors: List[LogError], first_only: bool) -> str:
    items = errors[:1] if first_only else errors
    if not items:
        return "line_no,severity,timestamp_ns,timestamp_raw,hier_path,file,file_line,message\n"
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["line_no", "severity", "timestamp_ns", "timestamp_raw",
                     "hier_path", "file", "file_line", "message"])
    for e in items:
        writer.writerow([
            e.line_no, e.severity, e.timestamp_ns, e.timestamp_raw,
            e.hier_path, e.file, e.file_line, e.message,
        ])
    return buf.getvalue()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse a simulation log and extract UVM_ERROR / UVM_FATAL "
                    "/ SVA failures — Stage-1 evidence source for chip-debug.",
    )
    parser.add_argument("logfile", help="Path to the simulation log file.")
    parser.add_argument("--first-error", action="store_true",
                        help="Return only the earliest error.")
    parser.add_argument("--all-errors", action="store_true",
                        help="Return all errors with full context.")
    parser.add_argument("--context", type=int, default=3,
                        help="Lines of context before/after each error (default: 3).")
    parser.add_argument("--include-warnings", action="store_true",
                        help="Include UVM_WARNING lines in addition to errors.")
    parser.add_argument("--format", choices=["text", "json", "csv", "auto"],
                        default="text",
                        help="Output format (default: text).")
    parser.add_argument("--detect", action="store_true",
                        help="Print detected simulator/log kind and exit.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress non-essential output.")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.logfile):
        print(f"error: log file not found: {args.logfile}", file=sys.stderr)
        return 2

    with open(args.logfile, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    if args.detect:
        print(detect_format(text))
        return 0

    # Modulate context based on mode
    context = 0 if (args.first_error and not args.all_errors) else args.context

    # If --include-warnings requested, override the default warning filter
    if args.include_warnings:
        global SEVERITIES
        # Insert UVM_WARNING back without breaking order
        if not any(lbl == "UVM_WARNING" for lbl, _ in SEVERITIES):
            SEVERITIES = SEVERITIES + [("UVM_WARNING", re.compile(r"\bUVM_WARNING\b"))]

    errors = parse_log(text, context=context)
    # Sort by timestamp (errors missing time go last)
    errors.sort(key=lambda e: (e.timestamp_ns is None, e.timestamp_ns or 0.0))

    if not args.first_error and not args.all_errors:
        # Default: behave like --first-error
        args.first_error = True

    fmt = args.format
    if fmt == "auto":
        fmt = "json" if sys.stdout.isatty() is False else "text"

    if fmt == "json":
        print(fmt_json(errors, args.first_error, args.logfile))
    elif fmt == "csv":
        print(fmt_csv(errors, args.first_error))
    else:
        print(fmt_text(errors, args.first_error))

    if not args.quiet:
        if errors:
            print(f"# Detected {len(errors)} error line(s); "
                  f"earliest @ {errors[0].timestamp_raw or errors[0].line_no}.",
                  file=sys.stderr)
        else:
            print("# No errors detected.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
