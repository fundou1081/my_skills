# Atomic Tools — Spec for Chip-Debug RCA Primitives

These are the **8 atomic primitives** that the RCA workflow composes into
every 5-Why hop. They are **interface contracts**, not implementations —
`SKILL.md` and `references/rca-workflow.md` describe when to call them;
this file defines their input/output shape so that any backend can
implement them consistently (sv-query wrapper, VCD/FSDB reader, AST
indexer, etc.).

The 8 tools fall into two families:

- **Code-side (T01–T04)**: structural / static (RTL source of truth).
- **Wave-side (T05–T08)**: temporal / dynamic (waveform dump of truth).

---

## 0. Notation & Conventions

These conventions apply to **all** tools unless a tool says otherwise.

| Concept               | Convention                                                                            |
|-----------------------|---------------------------------------------------------------------------------------|
| Hierarchical path     | SV-style dotted path. `tb.dut.cpu.alu.result[31:0]`. Case-sensitive.                   |
| Time                  | String with unit. `12345 ns`, `1.234 us`, `100 ps`.                                    |
| Time comparison       | Internally normalized to nanoseconds for ordering; units preserved in human output.  |
| Numeric value         | Default radix hex (`0xDEADBEEF`). Override via `--radix dec|bin|hex|auto`.             |
| Output format         | JSON on stdout when `--format json`; human-readable text otherwise.                   |
| Errors                | Standard envelope `{"error": "...", "kind": "not_found|ambiguous|io|invalid_arg", "tool": "T0X"}`. |
| Tooling prefix        | All CLI invocations: `python3 scripts/atom.py T0X ...` or backend-specific.            |
| Cross-tool consistency| One tool's output should be ingestible by another — e.g. `wave_value_at` returns `{ts, value}` and `wave_prev_change` accepts the same shape. |

---

# Code-Side Tools (Static RTL)

## T01 — `code_path_resolve`

**Purpose** — Given a candidate hierarchical path, verify it exists in the
elaborated design and return the canonical form.

**Why this exists** — RCA often encounters signals referenced slightly
differently across `sv-query trace fanin` outputs, RTL comments, log
prints, etc. This tool normalizes them.

**Inputs**

| name      | type   | required | notes                                       |
|-----------|--------|----------|---------------------------------------------|
| `path`    | string | yes      | Hierarchical path to resolve.              |
| `top`     | string | no       | Optional elaboration root scope.           |
| `fuzzy`   | bool   | no       | If true, also return top-K similar candidates when exact fails. Default `false`. |

**Outputs**

```json
{
  "exists": true,
  "canonical_path": "tb.dut.cpu.alu.result[31:0]",
  "module_or_kind": "logic [31:0]",
  "scope": "tb.dut.cpu.alu",
  "candidates": [
    {"path": "tb.dut.cpu.alu.result[31:0]", "score": 1.0, "kind": "logic [31:0]"},
    {"path": "tb.dut.cpu.alu.result[15:0]", "score": 0.85, "kind": "logic [15:0]"}
  ]
}
```

**Invariants**

- Exact match → `exists=true`, `canonical_path` equals input after whitespace normalization.
- Not found → `exists=false`, `canonical_path=null`, `candidates` populated when `fuzzy=true`.
- Score uses Levenshtein on the leaf name + scope-trail similarity.

**Errors** — `not_found` (with `candidates` populated if `fuzzy=true`),
`ambiguous` (multiple prefix paths exist for short input).

**Example**

```
$ atom T01 code_path_resolve --path tb.dut.cpu.alu.rslt
{
  "exists": false,
  "canonical_path": null,
  "candidates": [
    {"path": "tb.dut.cpu.alu.result[31:0]", "score": 0.87, "kind": "logic [31:0]"}
  ]
}
```

---

## T02 — `code_define`

**Purpose** — Return the source-level definition of a signal.

**Inputs**

| name      | type   | required | notes                                                            |
|-----------|--------|----------|------------------------------------------------------------------|
| `path`    | string | yes      | Resolved path from T01 (or after passing through it).           |
| `context` | int    | no       | Lines of source context above/below the definition. Default 3.   |

**Outputs**

```json
{
  "path": "tb.dut.cpu.alu.result[31:0]",
  "kind": "logic",                   // wire | reg | logic | parameter | typedef | const | event
  "bit_width": 32,
  "is_array": false,
  "definition_site": {
    "file": "dut/cpu/alu.sv",
    "line": 142,
    "column": 18,
    "snippet": "logic [31:0] result;"
  },
  "context_above":  ["// functional ALU result", "/* packed struct */"],
  "context_below":  ["always_comb begin", "..."],
  "module_scope": "dut.cpu.alu",
  "elaboration_chain": ["alu.sv:138 module alu", "alu.sv:142 logic [31:0] result"]
}
```

**Invariants**

- `definition_site` always populated when `exists=true` (resolved paths always have a definition somewhere).
- For interface signals, `definition_site` refers to the interface body, not the modport usage.

**Errors** — `not_found`, `multiple_defs` (e.g. parameter redeclared in generate block),
`io_error` (source file unreadable).

---

## T03 — `code_scope_list`

**Purpose** — List all declarations under a given scope.

**Inputs**

| name       | type   | required | notes                                                                  |
|------------|--------|----------|------------------------------------------------------------------------|
| `scope`    | string | yes      | Hierarchical path of the scope (`tb.dut.cpu`).                        |
| `kind`     | enum   | no       | Filter: `signal` (default) / `wire` / `reg` / `logic` / `param` / `all`. |
| `prefix`   | string | no       | Optional leaf-name prefix filter (e.g. `r_` for registers).            |
| `limit`    | int    | no       | Max rows returned. Default 256.                                        |

**Outputs**

```json
{
  "scope": "tb.dut.cpu.alu",
  "module_or_kind": "module alu",
  "count": 17,
  "truncated": false,
  "items": [
    {"path": "tb.dut.cpu.alu.result",    "kind": "logic [31:0]", "is_input": false, "is_output": true},
    {"path": "tb.dut.cpu.alu.op_a",       "kind": "logic [31:0]", "is_input": true,  "is_output": false},
    ...
  ]
}
```

**Invariants**

- Scope must be resolvable (use T01 if unsure).
- `count` = `len(items)` unless `truncated=true`, in which case
  `count` reflects the **total** matching scope members.

**Errors** — `not_found` (scope does not exist), `ambiguous`.

---

## T04 — `code_rels`

**Purpose** — Return semantic relations of a signal: `drive`, `load`,
`control`, `clock`, `reset`. **Most heavily-used atom for the
5-Why workflow.**

**Inputs**

| name      | type   | required | notes                                                |
|-----------|--------|----------|------------------------------------------------------|
| `path`    | string | yes      | Resolved signal path.                               |
| `depth`   | int    | no       | Max hops to expand. Default `1`; `0` = leaf only.   |

**Outputs**

```json
{
  "path": "tb.dut.cpu.alu.result[31:0]",
  "definition": "dut/cpu/alu.sv:142 logic [31:0] result;",
  "drivers": [
    {"path": "tb.dut.cpu.alu.alu_comb_op",   "kind": "always_comb",  "line": 156,
     "expression": "case (op) ... result = a + b; endcase"}
  ],
  "loads": [
    {"path": "tb.dut.cpu.wb.stage_q[$].result", "kind": "sensitivity", "file": "wb.sv", "line": 88},
    {"path": "tb.env.scoreboard.observed",      "kind": "monitor",     "file": "scb.sv", "line": 32}
  ],
  "controls": [
    {"path": "tb.dut.cpu.alu.op[3:0]",          "kind": "mux_select",  "file": "alu.sv", "line": 156}
  ],
  "clock":   {"path": "tb.dut.cpu.clk",         "edge": "posedge"},
  "reset":   {"path": "tb.dut.cpu.rst_n",       "polarity": "active_low",
              "reset_value": "0x00000000", "kind": "async"}
}
```

**Field semantics**

- `drivers` — assignment sites that **write** this signal (always blocks, continuous assigns, port connections at the source).
- `loads` — read sites / sensitivity lists / port connections at the sink.
- `controls` — control inputs that affect the driver (e.g. mux select, enable, condition).
- `clock` — single-clock signals only; for multi-clock signals list multiple entries (rare).
- `reset` — may include `reset_value` and `kind` ∈ `async | sync`.

**Invariants**

- For pure-net signals (assign-only), `drivers` may have many entries (multi-driver).
- For local variables in `always_comb`, `clock`/`reset` are null.
- The returned paths are themselves resolvable by T01.

**Errors** — `not_found`, `no_static_info` (e.g. dynamic ref via DPI call).

**Example downstream use (5-Why hop)**

```
# From the L3 node of an RCA session:
$ atom T04 code_rels --path tb.dut.cpu.alu.op_a --depth 1
... → drivers[0] is the upstream register, becomes L4 ...
```

---

# Wave-Side Tools (Dynamic / Waveform)

Wave-side tools all share the common error envelope `{"error": ..., "kind": "io|not_found|out_of_range|invalid_arg", "tool": "T0X"}`. Every output carries the **canonical signal path** and **time** — even if absent — so evidence-chain nodes can be formed mechanically.

## T05 — `wave_value_at`

**Purpose** — Sample the value of a signal at a specific simulation time.

**Inputs**

| name       | type   | required | notes                                              |
|------------|--------|----------|----------------------------------------------------|
| `path`     | string | yes      | Hierarchical path.                                 |
| `time`     | string | yes      | Time with unit (e.g. `8440 ns`).                   |
| `radix`    | enum   | no       | `hex` (default) / `dec` / `bin`.                   |
| `wave`     | string | no       | Path to wave dump. Default: latest in session.    |

**Outputs**

```json
{
  "path": "tb.dut.cpu.alu.result[31:0]",
  "sample_time": "8440 ns",
  "value": "0xDEADBEEF",
  "value_kind": "logic [31:0]",
  "value_change_time": "8439 ns",      // The simulation time the value *became* 0xDEADBEEF.
  "value_change_delta_ns": 1.0,
  "is_x": false,
  "is_z": false,
  "wave_file": "run.fsdb",
  "hint": {
    "prev_change":   {"time": "8428 ns", "value": "0xCAFEBABE"},
    "next_change":   {"time": "8441 ns", "value": "0x12345678"}
  }
}
```

**Invariants**

- `value` reflects what the signal **holds** at `sample_time` (i.e. after the most recent value-change at or before `sample_time`).
- If `sample_time` lands between two changes, `value_change_time` < `sample_time`.
- For multi-driver nets, the resolved value is returned (X for unresolved conflicts).

**Errors** — `not_found` (signal not in waveform), `out_of_range` (before time-zero or after end-of-simulation), `io` (dump unreadable).

---

## T06 — `wave_prev_change`

**Purpose** — Find the most recent change of a signal **strictly before** a given reference time. The most common atom in 5-Why forward-tracing.

> User note: "**默认手工 debug 时,根据信号关系,追踪变化并定位**". This tool is the canonical primitive for that mode of work — once you have a relation hint from T04, you walk **backwards in time** on each driver using T06.

**Inputs**

| name       | type   | required | notes                                                            |
|------------|--------|----------|------------------------------------------------------------------|
| `path`     | string | yes      | Hierarchical path.                                              |
| `ref_time` | string | yes      | The reference time (default semantics: search *back* from this). |
| `n`        | int    | no       | Return last `n` changes instead of 1. Default `1`. Max 64.      |
| `wave`     | string | no       | Wave dump path.                                                 |

**Outputs (n=1)**

```json
{
  "path": "tb.dut.cpu.alu.result[31:0]",
  "ref_time": "8440 ns",
  "found": true,
  "change_time": "8439 ns",
  "value_after_change": "0xDEADBEEF",
  "delta_ns": 1.0
}
```

**Outputs (n>1, list form)**

```json
{
  "path": "tb.dut.cpu.cpu.alu.result[31:0]",
  "ref_time": "8440 ns",
  "found": true,
  "changes": [
    {"change_time": "8439 ns", "value_after_change": "0xDEADBEEF"},
    {"change_time": "8428 ns", "value_after_change": "0xCAFEBABE"},
    {"change_time": "4000 ns", "value_after_change": "0x00000000"}
  ]
}
```

**Invariants**

- Change times are **strictly before** `ref_time`.
- If no change found before `ref_time`, `found=false`. The chain node records `found=false` as objective evidence (a hidden uninitialized region, e.g. an X-prop culprit).

**Errors** — same as T05.

**Forward-derivation seam**

```
L_k (symptom observed at t_sym):
  for each candidate driver drv in T04(drv, depth=1).drivers:
      chg = T06(drv.path, ref_time=t_sym, n=1)
      → L_{k+1} node: drv.path = chg.value at chg.change_time
      recurse upstream
```

---

## T07 — `wave_diff`

**Purpose** — Compare two signals' value-change sequences over a time window. Two output modes:

- **mode=`event`** (default): return two event-stamped series with alignment — useful for "do they change together?"
- **mode=`sequence`**: return value-only (radix-normalized) sequences for equality checks — useful for "are these identical?"

**Inputs**

| name        | type   | required | notes                                                |
|-------------|--------|----------|------------------------------------------------------|
| `path_a`    | string | yes      | First signal.                                       |
| `path_b`    | string | yes      | Second signal.                                      |
| `time_from` | string | no       | Start of window. Default: start of waveform.        |
| `time_to`   | string | no       | End of window. Default: end of waveform.            |
| `mode`      | enum   | no       | `event` (default) or `sequence`.                    |
| `radix`     | enum   | no       | Default `hex`.                                      |
| `wave`      | string | no       | Wave dump path.                                     |

**Outputs (mode=`event`)**

```json
{
  "mode": "event",
  "from_time": "8000 ns",
  "to_time":   "9000 ns",
  "alignment": [
    {"time": "8001 ns", "a": "0x1111", "b": "0x1111", "agree": true},
    {"time": "8200 ns", "a": "0x2222", "b": "0x2222", "agree": true},
    {"time": "8439 ns", "a": "0xDEAD", "b": "0xBEEF", "agree": false,  "diverged_at": true}
  ],
  "summary": {
    "n_changes_a": 17,
    "n_changes_b": 16,
    "n_mismatches": 1,
    "first_mismatch_time": "8439 ns"
  }
}
```

**Outputs (mode=`sequence`)**

```json
{
  "mode": "sequence",
  "a_sequence": ["0x0000", "0x1111", "0xDEAD"],
  "b_sequence": ["0x0000", "0x1111", "0xBEEF"],
  "equal_as_sequences": false,
  "longest_common_prefix": 2
}
```

**Invariants**

- For `event`, time-monotonic ordering is preserved.
- For `sequence`, the value at `time_from` (or the latest-before-`time_from` value) is included as the first element so the comparison has a starting baseline.
- X/Z counts as a distinct token in both modes.

**Errors** — `not_found` (either signal missing), `wave_mismatch` (signals reside in different wave files).

---

## T08 — `wave_nearest_change`

**Purpose** — Given a reference time `ref_t` that is **not** necessarily a
value-change moment, find the **closest** change (in simulation time) to
`ref_t` for a signal. **Bidirectional** — supports `prev`, `next`, or `both`.

> Pairing with T06: T06 is best when the reference time IS a value-change
> moment (the natural "walk back" primitive). T08 is best when the
> reference time is an *external* anchor (a log timestamp, an assertion
> fail time, a `force`/`release` event) that you want to align to the
> signal's change history.

**Inputs**

| name        | type   | required | notes                                          |
|-------------|--------|----------|------------------------------------------------|
| `path`      | string | yes      | Hierarchical path.                            |
| `ref_time`  | string | yes      | Reference time (anchor, not necessarily a change). |
| `direction` | enum   | no       | `prev` (default), `next`, or `both`.           |
| `wave`      | string | no       | Wave dump path.                               |

**Outputs (direction=`both`)**

```json
{
  "path": "tb.dut.cpu.alu.result[31:0]",
  "ref_time": "8439.5 ns",
  "nearest_prev": {
    "change_time": "8439 ns",
    "value_after_change": "0xCAFEBABE",
    "delta_ns": 0.5
  },
  "nearest_next": {
    "change_time": "8441 ns",
    "value_after_change": "0xDEADBEEF",
    "delta_ns": 1.5
  },
  "closer_side": "prev",
  "min_delta_ns": 0.5
}
```

**Outputs (direction=`prev`)**

```json
{
  "path": "...",
  "ref_time": "8439.5 ns",
  "nearest_prev": {"change_time": "8439 ns", "value_after_change": "0xCAFEBABE", "delta_ns": 0.5},
  "nearest_next": null
}
```

**Invariants**

- For multi-clock scenarios, changes are reported at simulation-time granularity, not cycle-count.
- If `ref_time` lands exactly on a change, `delta_ns = 0` and `nearest_prev.change_time == ref_time == nearest_next.change_time` (returned in BOTH sides — caller should de-duplicate by ts).
- If no change exists in the requested direction, that side is `null`.

**Errors** — same family as T05.

---

## Cross-cutting Invariants (apply to ALL tools)

1. **Path consistency** — T01 should be called first whenever a path comes from outside (user, log line, etc.). T02/T03/T04/T05–T08 all expect a path already resolvable.
2. **Time normalization** — internally everything is normalized to picoseconds (or ns with explicit suffix); outputs round-trip to whatever the user passed.
3. **Empty / no-data cases** — when a tool cannot find anything, it returns `{"found": false, ...}` NOT an error, except when input itself is invalid. This is critical for the RCA workflow: "no change found before ref_time" is **objective evidence**, not a tool failure.
4. **Reproducibility** — given the same inputs + same wave + same elaboration root, outputs must be byte-identical. Backend implementations must respect this.
5. **Audit field** — every tool should accept `--actor <name>` so the session's decision-log can record who invoked it (default: `chip-debug-skill`).

---

## Composing Atoms into 5-Why Hops

A typical RCA `L_{k+1}` node is formed by composing:

```
t_k = L_k.time
sig = L_k.signal
   │
   ├── T01 (resolve sig)
   ├── T04 (relations of sig) → candidates {drv_1, drv_2, ...}
   │
   └── for each candidate drv in candidates:
        ├── T05 (drv at t_k)        → confirm wrong value
        ├── T06 (drv before t_k, n=1) → chg_drv = (t_chg, v_chg)
        └── T08 (drv around t_chg)  → ensure alignment with log/SVA anchors

   → emit L_{k+1} node with drv.path, t_chg, v_chg.
```

This composition pattern is what every hop in the chain will eventually look like. The bridge scripts in `references/tools-and-bridges.md` instantiate exactly these atoms via `sv-query` / waveform backends.

---

## Roadmap (not implemented)

These specs are the **target interface**. The current skill ships with
`scripts/parse_uvm_log.py` (log atoms for T05's anchors) and a plan to
add `scripts/atom.py` later. Tracked follow-ups:

1. `scripts/atom.py T01..T04` — backended by `sv-query` results cached in `sv-query`'s SQLite index.
2. `scripts/atom.py T05..T08` — backended by VCD (via `pyDigitalWaveTools`) and FSDB (via Verdi CLI conversion).
3. Once atoms are real, `references/tools-and-bridges.md` becomes a thin facade mapping **each atom** to its **backend call** instead of being a free-form doc.
