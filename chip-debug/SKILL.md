---
name: chip-debug
description: Evidence-driven Root Cause Analysis (RCA) workflow for chip/HW/UVM/debug tasks. Use when a user asks to debug a UVM error, simulation failure, RTL bug, assertion fail, X/Z propagation, hang, CDC issue, test miscompare, or any "find the root cause" request on chip/HDL/SV/Verilog projects. Follows a strict 5-stage workflow (lock error entry → reverse trace → build causal chain → falsify → converge) with a structured evidence-chain schema, DFS-vs-BFS exploration policy, RC exclusion tests, and multi-turn session persistence. Load references/rca-workflow.md when starting a session, references/checklists.md before declaring RC, references/tools-and-bridges.md when bridging with external tools (sv-query, sv-trace, waveform, log parsers).
---

# Chip Debug — Evidence-Driven RCA Methodology

## What this skill is for

Apply a **disciplined Root Cause Analysis (RCA) workflow** to chip / HW / UVM / SV / Verilog debug problems. The goal is not "patch the symptom" — it is to find the **earliest objective signal** from which the entire observed failure can be deterministically derived, and to **refuse to stop** at any candidate that fails the falsification tests.

This skill is methodology-first: it tells the agent **how to think, what to log, when to declare RC, and when to back off**. Tooling (waveform, log parser, sv-query, formal, coverage, version diff) is invoked as evidence sources, not as decision-makers.

## When to trigger (must match)

Trigger this skill when the user mentions ANY of:

- "debug this", "找根因", "RCA", "为什么挂", "为什么 X", "复现", "跑挂了", "fail"
- `UVM_ERROR`, `UVM_FATAL`, `SVA` / assertion failure, `X-propagation`, `Z-state`, `hang`, `deadlock`
- "miscompare", "signature mismatch", "波形不对", "覆盖率不涨", "CDC 违例"
- specific signal/instance name + "奇怪" / "异常" / "错了"
- a run id, log path, wave path, time range, or error message that needs root-cause triage

Do NOT trigger for: pure feature design, code writing without a defect, performance tuning (different discipline), documentation tasks.

## Hard rules (the four core principles)

1. **Progressive disclosure** — Only surface the most suspicious causal line at any moment. Mute everything unrelated.
2. **Evidence-driven** — Every inference must cite a concrete signal + timestamp + value. "我觉得" / "maybe" / "很可能" is **not evidence**. No speculation.
3. **Reproducible & falsifiable** — The final root cause must be toggleable: introduce it → error occurs 100%; remove it → error disappears 100%.
4. **Full audit trail** — Persist every explored branch, every rejected hypothesis, every signal snapshot. The user must be able to rewind to any earlier node.

## The 5-Stage Workflow

### Stage 1 — Lock the error entry

- Find the **earliest** `UVM_ERROR` / `UVM_FATAL` / assertion fail / first divergent signal in logs & waves.
- Record its **exact timestamp** and **full hierarchical path** (e.g. `tb.dut.cpu.alu.result[31:0]`).
- This timestamp becomes the **target point** for Stage 2 reverse-tracing.

> Use `scripts/parse_uvm_log.py <log>` to automate this. See `references/tools-and-bridges.md`.

### Stage 2 — Reverse-trace & signal collection (5-Why)

- For each "why", demand the **next concrete objective signal** before proceeding to the next "why".
- At each critical time point, list all relevant signals + values, score them by:
  - **Numerical anomaly degree** (deviation from expected)
  - **Temporal proximity** (closer time = more suspect)
  - **Logical dependency strength** (driver/load relationship)
- Pick the most-correlated signal and continue digging upstream.
- **Keep the chain temporally and logically continuous** — no jumps.

### Stage 3 — Build the causal chain

Assemble the evidence into a **directed chain**:

```
[initial defect] → [state propagation step 1] → ... → [final symptom]
```

**Forward-derivation test**: starting from the root cause alone, without extra assumptions, you MUST be able to mechanically derive the observed symptom.

### Stage 4 — Falsify & verify

- **Toggle test**: deliberately inject RC → error reappears; remove RC → error gone. Both must hold.
- Try to **explain every secondary anomaly** with the same RC. If unexplained leftovers exist, the hypothesis is incomplete → keep digging.
- Actively hunt for **counter-examples**. The moment a logical contradiction appears, **demote the candidate to "intermediate cause"** and continue upstream.

### Stage 5 — Converge & deliver

RC is accepted **only when** it passes every line of the discrimination checklist AND every line of the self-check checklist (see `references/checklists.md`).

Deliverables (all required, see `assets/templates/`):

1. **Causal-chain report** — Signals + times + values + reasoning at each hop.
2. **RC file** — All involved signals and their constraints, reproducibly.
3. **Exploration log** — Every branch tried, every hypothesis rejected, with reason.

## Exploration policy — DFS vs BFS

- **DFS (depth-first)** — When error propagation is single-path and clear, dig along the most-suspect signal until it bottoms out. Fast, decisive.
- **BFS (breadth-first)** — When symptoms scatter, possibly concurrent causes, snapshot all related signals at one timestamp, score them, then descend into the highest-score branch.

**Always pick DFS / BFS by evidence, not by gut.** If both are valid, say so and let the user choose.

## Evidence-chain schema

Every evidence node is a dict:

```yaml
- time: 12345 ns               # simulation / wall time
  signal: tb.dut.cpu.alu.result[31:0]
  actual: 0xDEADBEEF
  expected: 0x12345678        # optional
  source: log / wave / SVA    # where this came from
  hop: "Stage2.L3"            # which 5-Why layer
  note: "Result diverges from expected at cycle 12, pc=0x80000004"
```

Persist the chain as JSON. Use `scripts/evidence_chain.py` for serialization. See `references/evidence-chain.md`.

## Root Cause — strict definition

A candidate is RC only when ALL of:

- **Earliest** — appears before any other anomaly on the time axis (necessary but not sufficient).
- **Toggleable** — can be made to appear/disappear 100% by toggling this one condition.
- **Closed chain** — every hop from RC to symptom is backed by objective evidence; forward derivation has no gap.
- **Most correlated** — among all suspects, explains the strongest correlation and covers ALL secondary anomalies.

Reject another candidate as RC the moment it fails ANY of: insufficient explanatory power, fails toggle test, temporal inversion, has counter-examples, looks like a fix-miracle (logging/restart/reordering hides it without principled cause), is an intermediate cause, fails necessity/sufficiency.

> See `references/checklists.md` for the two checklists (Discrimination + Self-check) — both must be all "Yes" before RC is declared.

## Multi-turn session model

This is a **roundtrip-able workflow** — the agent must explicitly state the current stage each turn ("Currently at Stage 2, 5-Why Layer 3, see evidence_chain.json#node_07"), and cite prior evidence. The user can rewind the agent to any prior node.

**Persist intermediate state**:

- `evidence_chain.json` — the chain nodes
- `decision_log.json` — every hypothesis explored, accepted, rejected, with reason
- `signal_snapshots/` — raw snapshots at key timestamps

Use `scripts/decision_log.py` to manage the audit trail. See `references/rca-workflow.md` for the full session protocol.

## Anti-patterns (NEVER do these)

- ❌ "I think it's probably X" — without a signal citation.
- ❌ Stop at the first plausible cause — without toggle test.
- ❌ "I added some prints and now it works" — without explaining the mechanism (this is a **fix-miracle**, demote immediately).
- ❌ Pick a "root cause" because it occurred earliest — earlist ≠ causal.
- ❌ Continue after a contradiction — back up one hop, do not push through.
- ❌ Declare RC without completing both checklists.

## How to invoke this skill (operational checklist)

When the user says "debug X" or hands a log/wave/error:

1. **Stage 0 — Open the session**:
   - Create `<workdir>/rca_session_<timestamp>/`.
   - Run `scripts/parse_uvm_log.py` on the log if log-based.
   - Initialize `evidence_chain.json` + `decision_log.json`.

2. **Stage 1 — Lock entry**: confirm first error timestamp + path, write into evidence node #0.

3. **Stage 2 — 5-Why**: each layer = one evidence node + one decision-log entry.

4. **Stage 3 — Chain**: ensure every hop has evidence; forward-derive mentally.

5. **Stage 4 — Falsify**: at least one toggle test, plus counter-example search.

6. **Stage 5 — Deliver**: complete both checklists → emit RC report + RC file + exploration log. Archive the session.

If at any point the user jumps in with extra context, **rewind to the affected node**, don't restart.

## See also

- `references/rca-workflow.md` — Full per-stage procedure + sessions protocol.
- `references/evidence-chain.md` — Detailed evidence-node schema + worked examples.
- `references/checklists.md` — Discrimination checklist + self-check checklist + RC-exclusion tests.
- `references/tools-and-bridges.md` — How to delegate evidence collection to `sv-query`, `sv-trace`, waveform parsers, log analyzers.
- `references/atomic-tools.md` — 8 atomic primitives (input/output contracts) for 5-Why hops.
- `references/debug-playbook.md` — Raw 5-step field manual (dialogue snapshot).
- `references/debug-playbook-enhanced.md` — Enhanced 5-step field manual (with triggers/matrices/templates).
- `references/output-artifacts-and-discipline.md` — **3 deliverable products + 5 operational discipline rules** + **time-monotonic invariant**.
- `references/root-cause-elevation.md` — **Post-RC 4-dim elevation**: design / architecture / style / generalization.
- `scripts/parse_uvm_log.py` — Auto-extract first error from a log.
- `scripts/evidence_chain.py` — Evidence chain schema & serialization helpers, plus `time-check` subcommand.
- `scripts/decision_log.py` — Hypothesis-tracking audit log.
- `scripts/build_rc_file.py` — **Script-generated RC_file.yaml** (never hand-write).
- `assets/templates/` — RC report, evidence template, exploration log templates.
- `examples/example_rca_session.md` — A complete RCA worked example.
