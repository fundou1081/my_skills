# Evidence Chain — Schema, Validation, Worked Examples

The evidence chain is the **single source of truth** for an RCA session. This reference defines its schema, validation rules, and patterns for common chip-debug scenarios.

---

## Schema v1 (canonical)

```json
{
  "schema_version": "1.0",
  "session_id": "rca_session_20260714_091500",
  "created_at": "2026-07-14T09:15:00+08:00",
  "locked_entry": {
    "time": "8450 ns",
    "signal": "tb.env.scoreboard.mismatch",
    "source": "log:run.log:1247",
    "note": "First UVM_ERROR. NOT necessarily root cause."
  },
  "nodes": [
    {
      "node_id": "E0",
      "stage": "Stage1.LockEntry",
      "layer": 0,
      "hop": "symptom",
      "time": "8450 ns",
      "signal": "tb.env.scoreboard.mismatch",
      "actual": "expected=0xCAFEBABE actual=0xDEADBEEF",
      "expected": "0xCAFEBABE",
      "source": "log",
      "evidence_kind": "log_line",
      "relation": null,
      "confidence": 1.0,
      "note": "Symptom entry. Reverse-trace target."
    },
    {
      "node_id": "L1",
      "stage": "Stage2.5Why",
      "layer": 1,
      "hop": "5-Why-L1",
      "time": "8440 ns",
      "signal": "tb.dut.cpu.alu.result[31:0]",
      "actual": "0xDEADBEEF",
      "expected": null,
      "source": "wave:run.fsdb:@8440ns",
      "evidence_kind": "wave_dump",
      "relation": "Scoreboard mismatch sampled alu.result one cycle earlier",
      "confidence": 0.95,
      "note": "Driver of the mismatch signal."
    }
  ]
}
```

### Field reference

| Field            | Required | Type                  | Notes                                                        |
|------------------|----------|-----------------------|--------------------------------------------------------------|
| `node_id`        | YES      | string                | Monotonic. `E0`, `L1`, `L2`, ... or `RC` for the root node. |
| `stage`          | YES      | enum                  | `Stage1.LockEntry` / `Stage2.5Why` / `Stage3.Chain` / `Stage4.Falsify` / `Stage5.Deliver` |
| `layer`          | YES      | int                   | 0=symptom, 1..N=5-Why depth, -1=root candidate               |
| `hop`            | YES      | string                | Free-text short label of this hop                            |
| `time`           | YES      | string                | Time string with unit (`ns`, `ps`, `ps/clock`, `cycle`)      |
| `signal`         | YES      | string                | Full hierarchical path. Standard SV `tb.dut.mod.sig[index]`   |
| `actual`         | YES      | string                | What we observed. Hex/bin/dec all OK; include units.         |
| `expected`       | NO       | string                | What it should have been, if known.                          |
| `source`         | YES      | string                | Origin: `log:<file>:<line>`, `wave:<file>:@<time>`, `sva:<file>`, `code:<file>:<line>`, `coverage:<file>` |
| `evidence_kind`  | YES      | enum                  | `log_line` / `wave_dump` / `sva_fail` / `code_inspection` / `coverage_gap` / `formal_counterexample` / `derived` |
| `relation`       | NO       | string                | WHY this node connects to the prior. Mechanical relation.    |
| `confidence`     | YES      | float 0.0–1.0         | Subjective but must be argued                                |
| `note`           | NO       | string                | Free text                                                    |

---

## Validation rules (enforced by `scripts/evidence_chain.py`)

1. **Monotonic node_ids** — no duplicates, must follow `E0 → L1 → L2 → ...`.
2. **Time monotonicity** — within a chain segment, time must not decrease.
3. **Every non-E0 node has a `relation`** — explicitly stating the link to its parent.
4. **Confidence without a `source` is invalid** — every claim must cite evidence.
5. **Layer 0 is the symptom, layer -1 is the root candidate** — never invert.
6. **Expected must be present for any node with confidence ≥ 0.9** — high-confidence claims need ground truth.

### Time-Unidirectional Invariant (Canonical)

In addition to the structural checks above, the **causal chain must satisfy a
strict time-unidirectional constraint**:

> When nodes are ordered **from root cause to symptom** (RC → L_n → ... → L_1 → E_0),
> their simulation timestamps must be **monotonically non-decreasing**.

Equivalent phrasing (more familiar to debuggers):

- Walking **upstream** from E_0 toward RC, time **must decrease** or stay equal.
- Walking **downstream** from RC toward E_0, time **must increase** or stay equal.

Any violation is a data bug — either:

- **Wrong timestamp** (the recorded time at a hop is later than what the wave /
  log actually shows), or
- **Wrong relation** (the hop doesn't actually derive the next node at the
  claimed moment), or
- **Wrong layering** (the hop is misplaced in the chain).

**This is a necessary condition**: a chain that does not satisfy
time-unidirectionallity cannot be a valid causal chain (it might be coincidental
correlation, not causation). Use it as a **check during step 4 of the RCA** and
as a **release gate** for any deliverable.

Implementation: `python3 scripts/evidence_chain.py time-check <chain.json>`
prints per-hop time and any monotonicity violations explicitly.

---

## Building the chain: a worked example

**Scenario**: `UVM_ERROR: read data mismatch @ 8450 ns` in a tiny APB slave.

### E0 — Lock entry

```json
{
  "node_id": "E0",
  "stage": "Stage1.LockEntry",
  "layer": 0,
  "hop": "symptom",
  "time": "8450 ns",
  "signal": "tb.env.apb_mst.scoreboard.mismatch",
  "actual": "expected=0xCAFEBABE actual=0xDEADBEEF",
  "expected": "0xCAFEBABE",
  "source": "log:run.log:1247",
  "evidence_kind": "log_line",
  "confidence": 1.0,
  "note": "First UVM_ERROR. Wrote at 8450ns but sampled at 8440ns+δ."
}
```

### L1 — Find the divergent signal feeding E0

```json
{
  "node_id": "L1",
  "stage": "Stage2.5Why",
  "layer": 1,
  "hop": "5-Why-L1",
  "time": "8444 ns",
  "signal": "tb.dut.apb_slave.rdata[31:0]",
  "actual": "0xDEADBEEF",
  "expected": "0xCAFEBABE",
  "source": "wave:run.fsdb:@8444ns",
  "evidence_kind": "wave_dump",
  "relation": "Scoreboard samples rdata 1 cycle after PRDATA rises",
  "confidence": 0.97,
  "note": "rdata is wrong. Inspect what drives it."
}
```

### L2 — What writes rdata?

```json
{
  "node_id": "L2",
  "stage": "Stage2.5Why",
  "layer": 2,
  "hop": "5-Why-L2",
  "time": "8444 ns",
  "signal": "tb.dut.apb_slave.mem_rd_data[31:0]",
  "actual": "0xDEADBEEF",
  "expected": "0xCAFEBABE",
  "source": "wave:run.fsdb:@8444ns",
  "evidence_kind": "wave_dump",
  "relation": "rdata is combinational pass-through of mem_rd_data",
  "confidence": 0.95,
  "note": "mem_rd_data wrong. Why?"
}
```

### L3 — Why is mem_rd_data wrong?

```json
{
  "node_id": "L3",
  "stage": "Stage2.5Why",
  "layer": 3,
  "hop": "5-Why-L3",
  "time": "8440 ns",
  "signal": "tb.dut.apb_slave.mem_addr[9:0]",
  "actual": "0x3FF",
  "expected": "0x080",
  "source": "wave:run.fsdb:@8440ns",
  "evidence_kind": "wave_dump",
  "relation": "mem_rd_data = mem[mem_addr]; wrong addr → wrong data",
  "confidence": 0.9,
  "note": "Address is wrong."
}
```

### L4 — Why is mem_addr wrong?

```json
{
  "node_id": "L4",
  "stage": "Stage2.5Why",
  "layer": 4,
  "hop": "5-Why-L4",
  "time": "8430 ns",
  "signal": "tb.dut.apb_slave.paddr_latched[9:0]",
  "actual": "0x3FF",
  "expected": "0x080",
  "source": "wave:run.fsdb:@8430ns",
  "evidence_kind": "wave_dump",
  "relation": "paddr_latched drives mem_addr (no offset applied here)",
  "confidence": 0.9,
  "note": "paddr is wrong. The test sent PADDR=0x080."
}
```

### L5 — Why is paddr_latched wrong?

```json
{
  "node_id": "L5",
  "stage": "Stage2.5Why",
  "layer": 5,
  "hop": "5-Why-L5",
  "time": "8425 ns",
  "signal": "tb.dut.apb_slave.padaddr_in[9:0]",
  "actual": "0x3FF",
  "expected": "0x080",
  "source": "wave:run.fsdb:@8425ns",
  "evidence_kind": "wave_dump",
  "relation": "paddr_latched captures PADDR on PSEL & PWRITE rise",
  "confidence": 0.95,
  "note": "PADDR from bus is 0x3FF. Master is driving wrong PADDR."
}
```

### L6 — Why does master drive wrong PADDR?

```json
{
  "node_id": "L6",
  "stage": "Stage2.5Why",
  "layer": 6,
  "hop": "5-Why-L6",
  "time": "8420 ns",
  "signal": "tb.env.apb_mst.seq_item.addr",
  "actual": "0x3FF",
  "expected": "0x080",
  "source": "log:run.log:1209",
  "evidence_kind": "log_line",
  "relation": "seq_item.addr is the source for PADDR",
  "confidence": 0.85,
  "note": "Sequence emitted wrong address."
}
```

### L7 — Why did the sequence emit 0x3FF?

```json
{
  "node_id": "L7",
  "stage": "Stage2.5Why",
  "layer": 7,
  "hop": "5-Why-L7",
  "time": "N/A",
  "signal": "tb/tests/apb_test.sv:47",
  "actual": "constraint c_addr { addr inside {[9'h000:9'h0FF], [9'h3F0:9'h3FF]}; }",
  "expected": "inside {[9'h000:9'h0FF]};",
  "source": "code:apb_test.sv:47",
  "evidence_kind": "code_inspection",
  "relation": "Random constraint allows 0x3FF, sequence picked it",
  "confidence": 1.0,
  "note": "ROOT CAUSE candidate. Over-broad constraint includes a reserved region."
}
```

### RC — Root cause

```json
{
  "node_id": "RC",
  "stage": "Stage5.Deliver",
  "layer": -1,
  "hop": "root",
  "time": "N/A",
  "signal": "tb/tests/apb_test.sv:47",
  "actual": "addr inside {[9'h000:9'h0FF], [9'h3F0:9'h3FF]};",
  "expected": "addr inside {[9'h000:9'h0FF]};",
  "source": "code:apb_test.sv:47",
  "evidence_kind": "code_inspection",
  "relation": "All upstream nodes derive mechanically from this constraint.",
  "confidence": 1.0,
  "note": "Constrain the addr range. Toggle test: revert range to {0x000..0x0FF} → mismatch disappears."
}
```

### Why this is a good chain

- **Time monotonic** L1 → L7 (descending into the past).
- **Every hop has a `relation`** linking to the prior.
- **Forward-derivable**: starting from constraint, with random picking 0x3FF, the chain mechanically reaches 0xDEADBEEF at the scoreboard, no extra assumptions.
- **Toggle-test passed**: removing `9'h3F0:9'h3FF` from the range → mismatch gone.

---

## Anti-patterns (DO NOT)

- ❌ A node with `confidence >= 0.9` and no `expected` value — high confidence needs a comparator.
- ❌ Skipping layers (jumping L3 → L6) without an explicit intermediate node.
- ❌ Time going forward inside the chain — the chain must trace backwards in time.
- ❌ `relation` left null for non-root nodes.
- ❌ Root declared at a node whose time is later than another anomaly.
- ❌ `evidence_kind: speculation` — not allowed; use `derived` with explicit reasoning if no direct signal, but mark low confidence.

---

## Reusing vs. forking chains

If during a session you discover the prior chain was wrong:

- **Do not edit history**.
- Append a new chain (chain v2) starting from the contested node.
- In `decision_log.json`, mark the prior decision as "superseded by v2".

This keeps the audit trail intact.
