# Example — A Complete RCA Session

> Worked example to show the workflow in action. The scenario: an APB slave
> read returns the wrong data on a corner case. This is the SAME worked
> example as `references/evidence-chain.md`, just walked through with
> `scripts/parse_uvm_log.py` and `scripts/evidence_chain.py` end-to-end.

---

## Step 0 — Open the session

```bash
SESSION=/tmp/rca_apb_mismatch
mkdir -p $SESSION/{0_input,1_evidence/signal_snapshots,2_decisions,3_repro,9_output}

# Drop the failing log into the session
cp ~/runs/apb/run_2026_07_14.log $SESSION/0_input/run.log

# Init the chain + decision log
python3 scripts/evidence_chain.py init $SESSION
python3 scripts/decision_log.py   init $SESSION
```

This creates:

- `1_evidence/evidence_chain.json` — empty skeleton
- `2_decisions/decision_log.json` — empty skeleton

---

## Step 1 — Lock the error entry

```bash
python3 scripts/parse_uvm_log.py $SESSION/0_input/run.log --first-error --format json
```

```json
{
  "log_file": ".../0_input/run.log",
  "n_total": 3,
  "n_returned": 1,
  "errors": [
    {
      "line_no": 1247,
      "raw": "UVM_ERROR @ 8450 ns [tb.env.apb_mst.scoreboard] read data mismatch: expected 0xCAFEBABE actual 0xDEADBEEF",
      "severity": "UVM_ERROR",
      "timestamp_ns": 8450.0,
      "timestamp_raw": "[8450 ns]",
      "hier_path": "tb.env.apb_mst.scoreboard",
      "file": null,
      "file_line": null,
      "message": "[tb.env.apb_mst.scoreboard] read data mismatch: expected 0xCAFEBABE actual 0xDEADBEEF"
    }
  ]
}
```

Now write a decision entry:

```bash
python3 scripts/decision_log.py add \
    $SESSION/2_decisions/decision_log.json \
    --hypothesis "Locked entry: UVM_ERROR at 8450 ns on apb_mst.scoreboard with expected=0xCAFEBABE actual=0xDEADBEEF" \
    --evidence-ref "log:run.log:1247" \
    --verdict accept \
    --reason "First UVM_ERROR on the time axis. Will serve as target for reverse-tracing." \
    --tag "stage1.lock_entry"
```

And seed the chain with `E0`:

```bash
python3 scripts/evidence_chain.py add \
    $SESSION/1_evidence/evidence_chain.json \
    --node-id E0 --stage Stage1.LockEntry --layer 0 \
    --hop symptom \
    --time "8450 ns" \
    --signal "tb.env.apb_mst.scoreboard" \
    --actual "expected=0xCAFEBABE actual=0xDEADBEEF" \
    --expected "0xCAFEBABE" \
    --source "log:run.log:1247" \
    --evidence-kind log_line \
    --relation null \
    --confidence 1.0 \
    --note "First UVM_ERROR. NOT root cause."
```

---

## Step 2 — DFS into the chain

The scoreboard samples `apb_slave.rdata` one cycle earlier. Open wave dump
viewer, scroll to `8444 ns`, and observe:

```bash
python3 scripts/evidence_chain.py add \
    $SESSION/1_evidence/evidence_chain.json \
    --node-id L1 --stage Stage2.5Why --layer 1 \
    --hop "5-Why-L1" \
    --time "8444 ns" \
    --signal "tb.dut.apb_slave.rdata[31:0]" \
    --actual "0xDEADBEEF" \
    --expected "0xCAFEBABE" \
    --source "wave:run.fsdb:@8444ns" \
    --evidence-kind wave_dump \
    --relation "Scoreboard samples rdata 1 cycle after PRDATA rises" \
    --confidence 0.97 \
    --note "rdata diverges. Find upstream driver."
```

Repeat for L2 … L7 (omitted for brevity — see `references/evidence-chain.md`
for the full set of nodes).

After every layer, also add a decision entry:

```bash
python3 scripts/decision_log.py add \
    $SESSION/2_decisions/decision_log.json \
    --hypothesis "rdata wrong because it pass-throughs mem_rd_data" \
    --evidence-ref "L2" \
    --verdict accept \
    --reason "RTL inspection of apb_slave.sv: combinational assign rdata = mem_rd_data." \
    --tag "stage2.L2"
```

---

## Step 3 — Forward-derive

```bash
python3 scripts/evidence_chain.py validate $SESSION/1_evidence/evidence_chain.json
python3 scripts/evidence_chain.py forward-check $SESSION/1_evidence/evidence_chain.json
```

The forward-check confirms every non-root node has a `relation` field,
which is the **structural** form of forward-derivation. The semantic
forward-derivation (does L7 + constraint + random → E0?) is done mentally
during Stage 3 review.

---

## Step 4 — Toggle test

Make a copy of the test, narrow the constraint, rerun:

```bash
git worktree add /tmp/rca_repro_inject main   # inject: only 0x000..0x0FF
# edit constraint, re-run
./apb_test +UVM_TESTNAME=apb_read_test +seed=42 -do run.do
```

| Direction          | Expectation                  | Result                |
|--------------------|------------------------------|-----------------------|
| Inject RC          | Reproduce mismatch           | ✅ PASS — mismatch at 8450 ns reappears |
| Remove RC          | No mismatch                  | ✅ PASS — clean run, 0 UVM_ERRORs |

Record:

```bash
python3 scripts/decision_log.py add \
    $SESSION/2_decisions/decision_log.json \
    --hypothesis "RC = constraint includes reserved region 0x3F0..0x3FF" \
    --evidence-ref "RC" \
    --verdict accept \
    --reason "Toggle test passed both directions over 5 random seeds; no other suspect explains all secondary anomalies." \
    --tag "stage4.toggle_test"
```

---

## Step 5 — Deliver

Three artifacts land in `9_output/`:

```bash
cp assets/templates/RC_report.md.template     $SESSION/9_output/RC_report.md
cp assets/templates/evidence.yaml.template    $SESSION/9_output/RC_file.yaml
cp assets/templates/exploration.md.template   $SESSION/9_output/exploration_log.md
# ... hand-fill them, or use a templating helper ...
```

Then close the session: confirm both checklists (Discrimination + Self-Check)
from `references/checklists.md` are all "Yes".

---

## Quick-recap — what just happened

1. `parse_uvm_log.py` extracted E0 (symptom) from a noisy log in milliseconds.
2. `evidence_chain.py` captured every 5-Why hop as a validated JSON node.
3. `decision_log.py` recorded every hypothesis accepted/rejected with reason.
4. Toggle test verified the RC is toggleable.
5. Three deliverables (RC report, RC file, exploration log) were emitted.

If a future turn re-opens this RCA, the agent reads `decision_log.json` and
`evidence_chain.json`, re-derives from where it left off, and never loses
context.

---

## What to NOT do in an RCA session

- ❌ Skip `parse_uvm_log.py` and start grep'ing manually → noisy, inconsistent.
- ❌ Add evidence nodes without `relation` field → forward derivation breaks.
- ❌ Skip `decision_log.py` for "obvious" acceptances → audit trail incomplete.
- ❌ Declare RC without toggle test → violates `checklists.md` Section B.
- ❌ Edit `evidence_chain.json` in place after the session starts → use versions.
