# RCA Workflow — Per-Stage Operational Guide

This is the **operational companion** to `SKILL.md`. Where `SKILL.md` describes the principles, this file describes the **per-stage steps**, **templates**, and **session protocol**.

> Read this when you are about to **start a new RCA session** or **re-enter an existing one**.

---

## Stage 0 — Open the session (always do this first)

Create an isolated work directory for this RCA so session state doesn't pollute other work:

```
<workdir>/rca_session_<YYYYMMDD_HHMMSS>/
├── 0_input/                  # raw log, wave, fault repro script
├── 1_evidence/
│   ├── evidence_chain.json   # main evidence chain
│   └── signal_snapshots/     # raw snapshots
├── 2_decisions/
│   └── decision_log.json     # explored branches, rejected hypotheses
├── 3_repro/                  # toggle-test artifacts
└── 9_output/
    ├── RC_report.md          # final RC report
    ├── RC_file.yaml          # all signals + constraints
    └── exploration_log.md    # human-readable exploration history
```

Initialize with:

```bash
mkdir -p <workdir>/rca_session_<ts>/{0_input,1_evidence/signal_snapshots,2_decisions,3_repro,9_output}
python3 scripts/evidence_chain.py init <session_dir>
python3 scripts/decision_log.py init <session_dir>
```

---

## Stage 1 — Lock the error entry

### Goals
- Find the **earliest** objective anomaly on the time axis.
- Record: **timestamp** + **hierarchical path** + **observed value** (and expected value if known).

### Where to look
- **UVM logs**: first `UVM_ERROR` / `UVM_FATAL` (chronologically earliest).
- **SVA**: first assertion fail line (often `Error: ... at <time>`).
- **Wave dumps**: first divergent signal vs reference / golden.
- **Coverage** anomalies: gaps that appear earlier than visible failures (often a leading indicator).

### How to extract
1. Strip timestamp prefix from each log line.
2. Sort by simulated time (not file order — reordering can happen with concurrent threads).
3. Take the **first** "ERROR" / "FATAL" / "FAIL" line.
4. Sanity-check: this is NOT necessarily root cause. It is the **target point for reverse-tracing**.

> Auto-extract: `python3 scripts/parse_uvm_log.py <log> --first-error`
> Multi-format support: see `references/tools-and-bridges.md`.

### Output (write into evidence_chain.json node #0)

```json
{
  "node_id": "E0",
  "stage": "Stage1.LockEntry",
  "time": "8450 ns",
  "signal": "tb.env.scoreboard.mismatch",
  "actual": "expected=0xCAFEBABE actual=0xDEADBEEF",
  "source": "log:run.log:1247",
  "note": "First UVM_ERROR in the run. Not necessarily root cause — this is the symptom entry point."
}
```

---

## Stage 2 — Reverse-trace & signal collection (5-Why)

### The discipline

For each "why", the agent **MUST** produce:
- A concrete signal + value at a specific time (objective evidence).
- A logical relation to the prior level (driver/load, fork, propagation, etc.).

**No "I suspect" without a signal.** If you can't find a signal, you haven't asked the right "why" yet.

### Layering template

| Layer | Question                                                | Required output                          |
|-------|---------------------------------------------------------|------------------------------------------|
| L1    | Why did this signal become `actual` at this time?       | Driver signal + value at the SAME/HB time |
| L2    | Why did the driver drive this value?                    | Control signal + condition               |
| L3    | Why was that condition true?                            | Upstream state register + value          |
| L4    | Why did that register hold this state?                  | Reset/initialization + clock domain      |
| L5    | Why was the initialization wrong?                       | Buggy line / RTL / constraint / X-prop   |

> **Depth rule**: stop digging only when you hit immutable hardware (e.g. reset vector hardcoded wrong) OR when layers match the originally observed symptom without needing further preconditions. For typical RTL bugs, 3–5 layers is normal. > 7 layers usually means you have an unclear front layer.

### DFS vs BFS decision (use BOTH checklists, both must fit)

**DFS criteria (any of these qualifies for DFS)**:
- Error propagation is single-path (only ONE diverging signal at the locked time).
- You can name a single candidate driver by static analysis.
- All secondary anomalies trace back to the same upstream signal.

**BFS criteria (any of these qualifies for BFS)**:
- Multiple divergences at the locked time.
- Concurrent processes modifying the same signal.
- Multiple agents/sequencers in flight.
- Coverage/functional anomalies happening concurrently with the locked error.

> Ambiguous? List 3 top-scoring branches and propose BFS for one round, then re-converge on the highest-score one.

### Signal scoring (BFS scoring, 0–10 each)

| Dimension          | Question                                                    | Score |
|--------------------|-------------------------------------------------------------|-------|
| Anomaly degree     | How far from expected?                                       | 0–3   |
| Temporal proximity | How close in time to the locked anomaly?                     | 0–3   |
| Logical dependency | How strong is the dependency to the locked signal?           | 0–2   |
| Reachability       | Can we reach it from a known good upstream?                  | 0–2   |

Total ≥ 7 → descend. 4–6 → keep in pool. < 4 → park.

---

## Stage 3 — Build the causal chain

### Chain structure (directed, no cycles)

```
E0 (symptom)  ←  L1  ←  L2  ←  L3  ←  L4  ←  L5 (root)
```

Each `←` is one hop. Each hop MUST have:
- Source signal + time + value (from the prior node).
- Target signal + time + value (the current node).
- A logical relation (assignment / mux select / port connect / reset / X-prop).

### Forward-derivation test (DO THIS MENTALLY BEFORE PROCEEDING)

Starting **only** from the root node, and using ONLY the relations in the hops:

1. What state does L4 predict at its time?
2. Apply L4 → L3 relation. What does L3 become?
3. Apply L3 → L2 relation. ...
4. ... down to E0.

Do these match the observed E0 values to a **bit-for-bit** level? If any hop requires an extra assumption, the chain is incomplete.

### Accept / reject criteria for the chain

| Test                                             | Pass required? |
|--------------------------------------------------|----------------|
| Every hop has objective evidence                 | YES            |
| Forward derivation reaches E0 without gaps       | YES            |
| No hop requires an "untested" precondition       | YES            |
| Earliest node is upstream of all observed anomalies on time axis | YES |
| Changing only the earliest node flips E0         | YES            |

If ANY of these fails → back to Stage 2.

---

## Stage 4 — Falsify & verify

### Toggle test (the gold standard)

1. **Inject test**: modify code to deliberately introduce the proposed RC → re-run → E0 must reappear.
2. **Remove test**: revert the injection → re-run → E0 must disappear.
3. Both 100%, multiple runs.

> Use `3_repro/` for toggle-test scripts and outputs.

### Counter-example search

Actively try to find:
- A run where RC condition is met but E0 does NOT appear → RC fails necessity.
- A run where E0 appears but RC condition is NOT met → RC fails sufficiency.

For either finding, demote to intermediate cause and resume Stage 2.

### Coverage of secondary anomalies

List every secondary anomaly you observed (other warnings, X-prop, garbage counts, etc.). For EACH, write one line:

> "The proposed RC explains this because [link to a hop or node in the chain]."

If any anomaly is **unexplained**, the chain is incomplete.

---

## Stage 5 — Converge & deliver

### Pre-declaration gates

- Both checklists from `references/checklists.md` are all "Yes".
- Toggle test passed.
- All secondary anomalies explained.

### Deliverables

| File                                  | Producer script                 | Required content                                           |
|---------------------------------------|----------------------------------|------------------------------------------------------------|
| `9_output/RC_report.md`               | `assets/templates/RC_report.md.template` filled | Symptom summary, chain diagram, each hop's evidence, findings |
| `9_output/RC_file.yaml`               | `assets/templates/evidence.yaml.template` filled | All involved signals + constraints + reproducer recipe |
| `9_output/exploration_log.md`         | `assets/templates/exploration.md.template` filled | All branches tried, hypotheses rejected, with reason |
| `2_decisions/decision_log.json`       | `scripts/decision_log.py`        | Machine-readable audit trail                               |
| `1_evidence/evidence_chain.json`      | `scripts/evidence_chain.py`     | The chain itself                                           |

### Final review (before declaring RC done)

- Re-read `references/checklists.md` once more.
- If the user is in the loop, ship a 1-paragraph summary and ask for sign-off.
- Archive the session folder. DO NOT delete — it is the audit trail for this bug.

---

## Multi-turn re-entry protocol

When the user resumes the conversation:

1. Read the latest snapshot of `decision_log.json` and `evidence_chain.json`.
2. State current stage + last completed layer explicitly in the reply.
3. If the user provides new evidence, append to the chain at the appropriate layer, do NOT restart.
4. If the user challenges a hop, walk back to that hop and re-open it.

### Sample re-entry template

```
[Resume @ Stage2.L3] Reopened from previous hop. Current nodes:
- E0: tb.env.scoreboard.mismatch @ 8450ns (symptom)
- L1: dut.cpu.alu.result == 0xDEADBEEF @ 8440ns
- L2: alu_op = SUB @ 8430ns

User challenges L2 with new evidence: "alu_op was forced by test_force, not by decoder".
→ Reopen L2: search for test_force call site, add L2' entry.
```

---

## Audit-trail invariants

- Every file in `1_evidence/`, `2_decisions/`, `3_repro/`, `9_output/` is **append-only** during a session — when revisiting, write a new version alongside, do not edit history.
- Each evidence node has a monotonic `node_id` and a `stage` label.
- Each decision-log entry has: `decision_id`, `hypothesis`, `evidence_ref`, `verdict`, `reason`.
- The session folder is the source of truth. Any external summary MUST cite nodes by node_id.

---

## TL;DR

1. Open a session folder.
2. Lock the entry → write E0.
3. DFS or BFS by scoring; one hop = one evidence node + one decision entry.
4. Forward-derive; cover all secondary anomalies.
5. Toggle-test; counter-example search.
6. Both checklists all-Yes → deliver three artifacts.
7. Re-enterable, audit-trail complete.

## Field Manual

> For the **hands-on, manual-debug decomposition** of these stages —
> per-step input/output/tools — see [`debug-playbook.md`](debug-playbook.md).
> That file is the practitioner's companion to this methodology skeleton.

## Output Artifacts & Discipline

> The 3 deliverable products (RC_file.yaml / chain_report.md / exploration state)
> plus the 5 operational-discipline rules (local-first / replay-from-E0 /
> no-fabrication / bi-directional traceability / script-generated RC file)
> are defined in [`output-artifacts-and-discipline.md`](output-artifacts-and-discipline.md).
> Treat those rules as **hard constraints** — same level as the methodology above.

## Time-Unidirectional Invariant (necessary condition)

> The **causal chain must be time-monotonic**: walking from RC toward E0,
> simulation time must be **non-decreasing**. Any reverse is a data bug,
> not "loosely stated" or "exempt". See
> [`output-artifacts-and-discipline.md` §4.4](output-artifacts-and-discipline.md#44-时间单调不变量-time-unidirectional-invariant--necessary)
> and [`evidence-chain.md`](evidence-chain.md) for the canonical spec.
> Tooling: `python3 scripts/evidence_chain.py time-check <chain.json>` —
> suitable as a CI / pre-merge gate.

## Root Cause Elevation (post-RC)

> Optional but recommended for severity S0/S1 or repeated-class bugs:
> after declaring RC, elevate from "this bug's fix" to "this class's root" —
> see [`root-cause-elevation.md`](root-cause-elevation.md).
