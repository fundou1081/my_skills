# Tools and Bridges — How to Gather Evidence

This skill is methodology-first. The real work happens **at the tool layer**. This reference describes how to delegate evidence gathering to existing tools — most importantly the `sv-query` and `sv-trace` skills already in your workspace.

> Read this when you are about to call any external tool for evidence.

---

## 1. Log parsing — `scripts/parse_uvm_log.py`

Lightweight, dependency-free, finds the **earliest** `UVM_ERROR`, `UVM_FATAL`, `SVA` failure, or generic `Error:` line.

```bash
# Pick the first UVM_ERROR (or any error class you choose)
python3 scripts/parse_uvm_log.py run.log --first-error

# All errors, all severities, with full context
python3 scripts/parse_uvm_log.py run.log --all-errors --context 5

# Parse a sim log from VCS / Questa / Xcelium / Verilator (auto-detect by file marker)
python3 scripts/parse_uvm_log.py trace.log --format auto --first-error

# CSV-friendly output for downstream scripts
python3 scripts/parse_uvm_log.py run.log --all-errors --format csv
```

### What it extracts

For each error line:
- Timestamp (sim time, normalized to ns when possible).
- Severity (`UVM_ERROR`, `UVM_FATAL`, `ERROR`, `FATAL`).
- Hierarchical path (best-effort parse of `id` field).
- File:line if printed by the simulator (e.g. VCS `at <file>:<line>`).
- Full message body.

### Integration with the chain

- The first error becomes `E0` in `evidence_chain.json`.
- If multiple errors fire near-simultaneously, include all in E0 and pick the deepest hierarchical path as the target for `L1`.

---

## 2. Signal tracing — bridging to `sv-query` and `sv-trace`

> Both skills are present in your `~/my_skills/`. Use them as evidence sources, NOT as decision-makers. Their output is one **objective signal** in the chain, not "the" root cause.

### Common use-cases

| I want to ...                                              | Skill + command                                                  |
|------------------------------------------------------------|------------------------------------------------------------------|
| Find where a signal is driven from                         | `sv-query trace fanin --signal <path> --depth 5`                  |
| Find where a signal drives to                              | `sv-query trace fanout --signal <path> --depth 5`                 |
| Find every module touching a signal                        | `sv-query trace impact --signal <path>`                            |
| Recover always-block / if-block source for a signal        | `sv-query trace evidence --signal <path> --context 3`              |
| Find all instances of a module + their ports               | `sv-query arch --module <mod_name>`                                |
| Cross-module trace                                          | `sv-query arch --from <mod.port> --to <mod.port>`                 |

### Bridge pattern

```
[symptom signal  s_path] →
    sv-query trace evidence s_path →
        [code line C1 producing s_path] →
        search upstream ports / always blocks →
            [upstream signal u_path] →
                sv-query trace fanin u_path →
                    ...
```

Each hop → one evidence node in the chain. **Always cite the actual return value of the tool**, not your interpretation.

### When `sv-query` is the wrong tool

- For runtime/cycle-accurate signals, `sv-query` (static analysis) will give you structural data, not values. Use waveform tools instead.
- For complex multi-driver arbitration, prefer `sv-query trace evidence` plus the original `.sv` for surrounding context.

---

## 3. Waveform access — VCD / FSDB

Out of scope of in-skill scripts (too vendor-specific), but here's the bridge contract:

```bash
# Example: dump signal values around the locked timestamp
python3 scripts/parse_wave.py \
    --format fsdb \
    --file run.fsdb \
    --signals tb.dut.cpu.alu.result tb.dut.cpu.alu.op \
    --time-range "8400ns:8500ns" \
    --output evidence/signal_snapshots/E0_window.csv
```

| Format  | Tooling                                              |
|---------|------------------------------------------------------|
| VCD     | `verilator --vcd`, GTKWave, `surfer`, `vcd2json`     |
| FSDB    | Verdi `nwave`, `fsdb2vcd` converter to VCD           |
| FST     | GTKWave, Surfer                                      |
| SHM     | `verilator --trace-fst`, Questa                       |

Each snapshot at a key timestamp becomes one evidence node. **Name snapshots after the node_id** so traceability holds.

---

## 4. SVA / assertion checkers

| Source                              | How to extract                                                                |
|-------------------------------------|--------------------------------------------------------------------------------|
| `$error("...")` in SVA              | log line; use `parse_uvm_log.py`                                              |
| Concurrent assertions in formal     | `jaspergold`, `synopsys formal`, `yosys sva` — counter-example gives the chain |
| Property fail in simulation         | typically log + wave; sometimes the failing property name itself is the link |

### Bridge contract for formal

```
formal counter-example → set of (cycle, signal, value) tuples →
    directly map 1:1 onto evidence_chain.json nodes
```

Formal is sometimes the BEST evidence source — the tool already does a directed search for the failing path. Use it as primary evidence when available.

---

## 5. Coverage report

Use to find **latent** anomalies:

| Cover type            | Failure mode                                |
|-----------------------|---------------------------------------------|
| Line / branch         | Untested code path that may harbor a bug.   |
| Toggle                | A signal never transitions.                 |
| Functional / cross    | Scenario combinations never exercised.      |
| Assertion             | Properties never assessed.                  |

Bridge:

```
coverage_gap.json →
    filter severity == low + bin == auto →
        run test on the gap →
            if new error → new evidence in chain
```

Coverage anomalies are **leading indicators** — they may detect bugs that haven't yet surfaced as E0. Worth listing as secondary anomalies to explain.

---

## 6. Version diff (git)

Often the **fastest** way to find an RC: what changed in the failing window?

```bash
# What files changed between last green and this red?
git diff --stat <last_green_sha>..<red_sha>

# Per-file blame around the locked time
git blame -L <line_range> <file>

# Bisect to localize in time (when RC is unknown)
git bisect run <reproducer.sh>
```

When the failing run is reproducible and you have CI artifacts, `git bisect` + the reproducer is **gold-standard evidence**. Add the bisect output as a decision-log entry.

---

## 7. Tool selection matrix

| You need ...                                | Primary tool                                |
|---------------------------------------------|---------------------------------------------|
| Earliest anomaly timestamp + path           | `parse_uvm_log.py`                          |
| Where a signal is read / written            | `sv-query trace evidence/fanin/fanout`       |
| Module instance graph for a hierarchical path | `sv-query arch`                            |
| Cycle-accurate signal values around time    | Waveform tool (VCD/FSDB/FST)                |
| Counter-example for a property              | Formal tool (Jasper/yosys sva)              |
| Coverage gaps                               | Coverage report (URM/IMC/xrun)              |
| What code changed between runs              | `git diff` / `git bisect`                   |
| Reproducer                                  | Tcl/Cocotb/UVM test runner                  |

---

## 8. Common anti-patterns in tool usage

- ❌ Tool returns a name you recognize → declare RC. **No.** Tool returns are **candidates**, not verdicts.
- ❌ `grep -R` returns 100 lines — "too noisy, must be...". **No.** Filter, score, then cite.
- ❌ Tool error itself — used as evidence without parsing. Always parse the actual return, not the error.
- ❌ "sv-query said the only driver is X" → jump to RC. **No.** That is structural data; you still need temporal data + toggle test.

---

## 9. Session-level patterns

- One tool call ≈ one evidence node (or a deliberate BFS scoring pass).
- Cache raw outputs to `1_evidence/signal_snapshots/` **before** parsing further. If you re-interpret, keep both.
- Record tool invocations with the actual command + raw return in `2_decisions/decision_log.json` for auditability.

---

## TL;DR

- Pick the right tool for the kind of evidence you need (see matrix).
- Cite raw return values, not your summary.
- Use `sv-query` and `sv-trace` as structural evidence; wave/coverage/formal as temporal evidence.
- Cache raw outputs — re-interpretation should never destroy history.
