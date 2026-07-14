#!/usr/bin/env python3
"""evidence_chain.py — Manage evidence-chain.json for chip-debug RCA sessions.

The chain is the SINGLE SOURCE OF TRUTH for the RCA. Schema and invariants
are documented in `references/evidence-chain.md`. This script provides:

    init     <session_dir>        Initialize a fresh chain file.
    add      <chain.json> [flags] Add a node (with validation).
    show     <chain.json>         Pretty-print the chain.
    validate <chain.json>         Run invariant checks; non-zero exit on fail.
    forward-check <chain.json>     Smoke-test forward-derivation fields.

Stdlib-only. The script is intentionally small so it can be hot-patched from
inside an RCA session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "1.0"
VALID_STAGES = {
    "Stage1.LockEntry",
    "Stage2.5Why",
    "Stage3.Chain",
    "Stage4.Falsify",
    "Stage5.Deliver",
}
VALID_EVIDENCE_KINDS = {
    "log_line", "wave_dump", "sva_fail", "code_inspection",
    "coverage_gap", "formal_counterexample", "derived",
}
NODE_ID_RE = re.compile(r"^(?:E0|L\d+|L-?\d+|RC|v\d+_[A-Za-z]+)$")

# Time-unit normalization: keep parity with parse_uvm_log.py so chains and
# snapshots compare bit-for-bit.
TIME_UNIT_TO_NS: Dict[str, float] = {
    "ns": 1.0,
    "us": 1_000.0,
    "ms": 1_000_000.0,
    "ps": 0.001,
    "fs": 0.000001,
    "simstep": 1.0,
    "cycle": 1.0,
    "cycles": 1.0,
}
_TIME_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?\s*$")


def parse_time_string(s: str) -> Optional[float]:
    """Parse '8444 ns' / '1.234 us' / 'N/A' into nanoseconds.

    Returns None for non-numeric (e.g. 'N/A', 'reset').
    """
    if not s:
        return None
    m = _TIME_RE.match(s)
    if not m:
        return None
    try:
        value = float(m.group(1))
    except (TypeError, ValueError):
        return None
    unit = (m.group(2) or "ns").lower()
    return value * TIME_UNIT_TO_NS.get(unit, 1.0)


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

class ChainInvariantError(ValueError):
    """Raised when a chain violates an invariant."""


def _required(node: Dict[str, Any], field: str) -> Any:
    if field not in node:
        raise ChainInvariantError(f"node missing required field: {field}")
    return node[field]


_ROOT_NODE_IDS = {"E0", "RC"}


def validate_node(node: Dict[str, Any], parent: Optional[Dict[str, Any]] = None,
                  is_root: Optional[bool] = None) -> List[str]:
    """Validate a single node; return list of warnings.

    `is_root` is auto-inferred for `E0` (locked symptom) and `RC` (root cause)
    if not passed explicitly.
    """
    warnings: List[str] = []
    nid = node.get("node_id")
    if nid is None or not NODE_ID_RE.match(str(nid)):
        warnings.append(f"node_id format unexpected: {nid!r}")
    if node.get("stage") not in VALID_STAGES:
        warnings.append(f"stage not in canonical set: {node.get('stage')!r}")
    if node.get("evidence_kind") not in VALID_EVIDENCE_KINDS:
        warnings.append(f"evidence_kind unexpected: {node.get('evidence_kind')!r}")
    if is_root is None:
        is_root = nid in _ROOT_NODE_IDS
    if not is_root and not node.get("relation"):
        warnings.append(f"non-root node {nid} has no 'relation' field")
    confidence = node.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
        warnings.append(f"confidence out of [0,1]: {confidence!r}")
    if confidence >= 0.9 and not node.get("expected") and node.get("stage") != "Stage5.Deliver":
        warnings.append(f"high-confidence node {nid} lacks 'expected' comparator")
    if not node.get("source"):
        warnings.append(f"node {nid} missing 'source' field")
    return warnings


def validate_chain(chain: Dict[str, Any], *, strict: bool = True) -> List[str]:
    """Validate the full chain against schema v1 invariants."""
    issues: List[str] = []
    if chain.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"schema_version mismatch: {chain.get('schema_version')!r}")
    if not chain.get("locked_entry"):
        issues.append("missing 'locked_entry' block")
    nodes = chain.get("nodes", [])
    if not nodes:
        issues.append("'nodes' is empty")
        return issues
    # Node-id set monotonic
    seen_ids: List[str] = []
    for n in nodes:
        nid = n.get("node_id")
        if nid in seen_ids:
            issues.append(f"duplicate node_id: {nid}")
        seen_ids.append(nid)
    # Time-monotonic: along the chain (E0 -> L1 -> L2 -> ... -> RC by
    # layer ASCENDING), simulation time must be NON-INCREASING (each hop
    # earlier in time than its successor's downstream). RC (layer -1)
    # sorts last and is allowed to have no timestamp.
    def _sort_key(t):
        layer, ts, nid = t
        if layer is None:
            return (0, 0, nid or "")
        # RC (-1) pushed past the deepest L_n so that 'later in chain'
        # really means 'closer to E0'.
        eff_layer = 99 if layer == -1 else layer
        return (1, eff_layer, nid or "")
    ts_layers = [(n.get("layer"), n.get("timestamp_ns"), n.get("node_id")) for n in nodes]
    by_layer = sorted(ts_layers, key=_sort_key)
    prev_ts: Optional[float] = None
    prev_id: Optional[str] = None
    for layer, ts, nid in by_layer:
        if ts is None or layer is None:
            continue
        if prev_ts is not None and ts > prev_ts + 1e-6:
            issues.append(
                f"time INCREASES from {prev_id} (ts={prev_ts:g}ns) to {nid} "
                f"(ts={ts:g}ns, layer={layer}); chain must be non-increasing "
                f"in time along E0 -> ... -> RC"
            )
        prev_ts = ts
        prev_id = nid
    # Validate each node
    for i, n in enumerate(nodes):
        parent = nodes[i - 1] if i > 0 else None
        try:
            warnings = validate_node(n, parent)
        except ChainInvariantError as e:
            issues.append(str(e))
            continue
        if strict:
            issues.extend(f"{n.get('node_id')}: {w}" for w in warnings)
    return issues


# -----------------------------------------------------------------------------
# Operations
# -----------------------------------------------------------------------------

def cmd_init(args) -> int:
    """Initialize a fresh chain.json under <session_dir>/1_evidence/."""
    chain_path = os.path.join(args.session_dir, "1_evidence", "evidence_chain.json")
    os.makedirs(os.path.dirname(chain_path), exist_ok=True)
    if os.path.exists(chain_path) and not args.force:
        print(f"refusing to overwrite existing {chain_path}; pass --force", file=sys.stderr)
        return 2
    skeleton = {
        "schema_version": SCHEMA_VERSION,
        "session_id": f"rca_session_{args.session_dir.rstrip('/').split('/')[-1]}",
        "created_at": _now_iso(),
        "locked_entry": {},
        "nodes": [],
    }
    with open(chain_path, "w", encoding="utf-8") as f:
        json.dump(skeleton, f, indent=2, ensure_ascii=False)
    print(f"initialized: {chain_path}")
    return 0


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def cmd_add(args) -> int:
    """Append a node to the chain, after validation."""
    if not os.path.isfile(args.chain):
        print(f"chain file not found: {args.chain}", file=sys.stderr)
        return 2
    with open(args.chain, "r", encoding="utf-8") as f:
        chain = json.load(f)
    node: Dict[str, Any] = {
        "node_id": args.node_id,
        "stage": args.stage,
        "layer": args.layer,
        "hop": args.hop,
        "time": args.time,
        "signal": args.signal,
        "actual": args.actual,
        "expected": args.expected,
        "source": args.source,
        "evidence_kind": args.evidence_kind,
        "relation": args.relation,
        "confidence": args.confidence,
        "note": args.note or "",
    }
    try:
        warnings = validate_node(node, parent=None)
    except ChainInvariantError as e:
        print(f"validation failed: {e}", file=sys.stderr)
        return 2
    if warnings:
        for w in warnings:
            print(f"warn: {w}", file=sys.stderr)
        if args.strict:
            print("refusing to add due to warnings; pass --no-strict to override.", file=sys.stderr)
            return 3
    # Auto-derive numeric timestamp_ns if --time was a parseable unit-bearing string.
    if node.get("timestamp_ns") is None and node.get("time"):
        ts = parse_time_string(node["time"])
        if ts is not None:
            node["timestamp_ns"] = ts
    chain["nodes"].append(node)
    with open(args.chain, "w", encoding="utf-8") as f:
        json.dump(chain, f, indent=2, ensure_ascii=False)
    print(f"appended node {args.node_id} -> {args.chain}")
    return 0


def cmd_show(args) -> int:
    if not os.path.isfile(args.chain):
        print(f"chain file not found: {args.chain}", file=sys.stderr)
        return 2
    with open(args.chain, "r", encoding="utf-8") as f:
        chain = json.load(f)
    le = chain.get("locked_entry", {})
    print(f"# session : {chain.get('session_id', '?')}")
    print(f"# schema  : v{chain.get('schema_version', '?')}  nodes={len(chain.get('nodes', []))}")
    if le:
        # Support both 'time' (canonical) and 'timestamp_raw' (legacy) keys.
        t = le.get("time") or le.get("timestamp_raw") or "?"
        print(f"# locked  : {t}  signal={le.get('signal', '?')}")
    print("-" * 78)
    for n in chain.get("nodes", []):
        print(f"[{n.get('node_id'):>4}] layer={n.get('layer'):>3}  {n.get('stage')}")
        print(f"       time={n.get('time')}  signal={n.get('signal')}")
        print(f"       actual={n.get('actual')}")
        if n.get("expected"):
            print(f"       expected={n.get('expected')}")
        print(f"       source={n.get('source')}  kind={n.get('evidence_kind')}  conf={n.get('confidence')}")
        if n.get("relation"):
            print(f"       relation: {n.get('relation')}")
        if n.get("note"):
            print(f"       note: {n.get('note')}")
        print()
    return 0


def cmd_validate(args) -> int:
    if not os.path.isfile(args.chain):
        print(f"chain file not found: {args.chain}", file=sys.stderr)
        return 2
    with open(args.chain, "r", encoding="utf-8") as f:
        chain = json.load(f)
    issues = validate_chain(chain, strict=not args.no_strict)
    if issues:
        print("ISSUES FOUND:", file=sys.stderr)
        for it in issues:
            print(f"  - {it}", file=sys.stderr)
        return 1
    print("OK: chain passes invariants.")
    return 0


def cmd_time_check(args) -> int:
    """Time-unidirectional check.

    Walks the chain from RC (layer -1) toward E_0 (layer 0) and verifies that
    simulation time is monotonically non-decreasing — i.e. causes precede effects.

    Prints a per-hop table and any violations explicitly. Exits non-zero on
    failure so this command is usable as a CI/release gate.
    """
    if not os.path.isfile(args.chain):
        print(f"chain file not found: {args.chain}", file=sys.stderr)
        return 2
    with open(args.chain, "r", encoding="utf-8") as f:
        chain = json.load(f)

    nodes = chain.get("nodes", []) or []
    # Carry both 'timestamp_ns' (canonical) and 'timestamp_raw' (legacy).
    def _ts(n):
        return n.get("timestamp_ns", None)
    timestamped = [n for n in nodes if _ts(n) is not None]
    # Sort by layer descending (RC -1 first), then by node_id for stable order.
    timestamped.sort(key=lambda n: (-(n.get("layer") or 0), n.get("node_id") or ""))

    print(f"# Time-unidirectional check  ({len(timestamped)} timestamped hops)")
    print(f"# Schema : chain v{chain.get('schema_version', '?')}, session={chain.get('session_id', '?')}")
    print(f"# Order  : RC -> L_n -> ... -> L_1 -> E_0 (along the causal chain)")
    print()
    print(f"  {'NODE':>5}  {'LAYER':>5}  {'TIME':>10}  {'DELTA':>10}  STATUS")
    print("  " + "-" * 60)
    prev_id = None
    prev_ts = None
    issues = []
    for n in timestamped:
        ts = _ts(n)
        nid = n.get("node_id", "?")
        layer = n.get("layer")
        if prev_ts is not None:
            delta = round(ts - prev_ts, 3)
            status = "OK" if delta >= -1e-6 else "VIOLATION"
            delta_str = f"{delta:+g}"
        else:
            delta_str = "—"
            status = "head"
        print(f"  {nid:>5}  {layer!s:>5}  {ts!s:>10}  {delta_str:>10}  {status}")
        if prev_ts is not None and ts < prev_ts - 1e-6:
            issues.append(
                f"  {prev_id} -> {nid}: time DECREASES by {prev_ts - ts:g} ns"
            )
        prev_ts = ts
        prev_id = nid

    print()
    if issues:
        print("# INVARIANT VIOLATIONS:", file=sys.stderr)
        for it in issues:
            print(it, file=sys.stderr)
        print()
        print(
            "# HINT: violation means either a wrong timestamp at this hop, or "
            "wrong relation between two hops. Inspect the wave/log at this "
            "exact time window and verify which is the cause and which is "
            "the effect.",
            file=sys.stderr,
        )
        return 1
    print("# OK: time is monotonically non-decreasing along the causal chain.")
    return 0


def cmd_forward_check(args) -> int:
    """Heuristic forward-derivation smoke check.

    Walks the chain by descending layer and reports missing `relation` on
    any non-root node. More sophisticated derivation would require parsing
    the chip semantics; we only flag structural completeness here.
    """
    if not os.path.isfile(args.chain):
        print(f"chain file not found: {args.chain}", file=sys.stderr)
        return 2
    with open(args.chain, "r", encoding="utf-8") as f:
        chain = json.load(f)
    nodes = sorted(chain.get("nodes", []), key=lambda n: -(n.get("layer") or 0))
    gaps: List[str] = []
    for n in nodes:
        if n.get("node_id") in _ROOT_NODE_IDS:
            continue
        if not n.get("relation"):
            gaps.append(f"{n.get('node_id')}: missing relation (forward derivation impossible)")
    if gaps:
        print("FORWARD-DERIVATION GAPS:", file=sys.stderr)
        for g in gaps:
            print(f"  - {g}", file=sys.stderr)
        return 1
    print("OK: every non-root node has a relation, structural forward derivation complete.")
    return 0


# -----------------------------------------------------------------------------
# CLI plumbing
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Evidence-chain manager for chip-debug RCA.")
    sub = p.add_subparsers(dest="command", required=True)

    # init
    sp = sub.add_parser("init", help="Initialize a fresh chain file under a session dir.")
    sp.add_argument("session_dir")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_init)

    # add
    sp = sub.add_parser("add", help="Append a node to the chain.")
    sp.add_argument("chain", help="Path to evidence_chain.json")
    sp.add_argument("--node-id", required=True)
    sp.add_argument("--stage", required=True, choices=sorted(VALID_STAGES))
    sp.add_argument("--layer", required=True, type=int)
    sp.add_argument("--hop", required=True)
    sp.add_argument("--time", required=True, help="Time string with unit, e.g. '8440 ns'.")
    sp.add_argument("--signal", required=True)
    sp.add_argument("--actual", required=True)
    sp.add_argument("--expected", default=None)
    sp.add_argument("--source", required=True, help="Source pointer like 'log:run.log:1247'.")
    sp.add_argument("--evidence-kind", required=True, choices=sorted(VALID_EVIDENCE_KINDS))
    sp.add_argument("--relation", default=None)
    sp.add_argument("--confidence", required=True, type=float)
    sp.add_argument("--note", default=None)
    sp.add_argument("--strict", action="store_true", default=True,
                    help="Refuse on warnings (default).")
    sp.add_argument("--no-strict", dest="strict", action="store_false",
                    help="Add even with warnings.")
    sp.set_defaults(func=cmd_add)

    # show
    sp = sub.add_parser("show", help="Pretty-print the chain.")
    sp.add_argument("chain")
    sp.set_defaults(func=cmd_show)

    # validate
    sp = sub.add_parser("validate", help="Run invariant checks against the chain.")
    sp.add_argument("chain")
    sp.add_argument("--no-strict", action="store_true",
                    help="Treat warnings as advisory instead of errors.")
    sp.set_defaults(func=cmd_validate)

    # forward-check
    sp = sub.add_parser("forward-check", help="Smoke-test forward-derivation fields.")
    sp.add_argument("chain")
    sp.set_defaults(func=cmd_forward_check)

    # time-check (NEW)
    sp = sub.add_parser(
        "time-check",
        help="Verify simulation time is monotonically non-decreasing along the chain (RC -> ... -> E0).",
    )
    sp.add_argument("chain")
    sp.set_defaults(func=cmd_time_check)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
