# Checklists — Discrimination, Self-Check, RC-Exclusion

These two checklists are the **gates** before a Root Cause can be declared. Any "No" answers require either another round of digging or an explicit demotion of the candidate to "intermediate cause".

---

## A. RC-Exclusion Conditions (REJECT if ANY holds)

A candidate is **not** the root cause the moment any of these is true. Reject and continue upstream.

| # | Condition                                         | Meaning                                                                                      |
|---|---------------------------------------------------|----------------------------------------------------------------------------------------------|
| 1 | **Insufficient explanatory power**                | Cannot explain at least one observed secondary anomaly.                                       |
| 2 | **Fails toggle test**                             | Injecting the condition does not reproduce the error, OR removing it does not eliminate it.  |
| 3 | **Temporal inversion**                            | The candidate event occurs **later** in time than the earliest anomaly record.                |
| 4 | **Counter-example exists**                        | A configuration has the same candidate condition but the system is healthy — fails necessity. |
| 5 | **Fix-miracle**                                   | Symptom disappears by adding prints, changing layout, restarting — without explaining why.   |
| 6 | **Causal inversion**                              | The candidate is itself a downstream effect — kept digging, "why?" still has answers.          |
| 7 | **Necessity / sufficiency failure**               | RC missing → error still occurs (necessity fail), OR RC present → error sometimes doesn't (sufficiency fail). |

> Rule: ONE condition failing → demote. Re-open Stage 2 from a layer above.

---

## B. Discrimination Checklist (every "Yes" required to be RC-eligible)

| # | Question                                                                                   | Yes | No  |
|---|--------------------------------------------------------------------------------------------|-----|-----|
| 1 | Can it explain **all** collected anomalies, including secondary ones?                      | ☐   | ☐   |
| 2 | Can I make the error **appear and disappear at will**, fully controlled by this candidate? | ☐   | ☐   |
| 3 | Does it occur **earlier in time** than every anomaly signal observed?                       | ☐   | ☐   |
| 4 | When the candidate condition is present, does the error **always** occur (necessity+sufficiency)? | ☐ | ☐ |
| 5 | When the candidate path is **completely avoided**, does the error **absolutely** not occur?   | ☐ | ☐ |
| 6 | Does the fix feel **principled**, with no "fix-miracle" smell?                              | ☐   | ☐   |

> Six "Yes" = strong candidate. Any "No" → back to Stage 2.

---

## C. Self-Check Checklist (final confirmation before declaring RC)

| # | Question                                                                                  | Yes | No |
|---|-------------------------------------------------------------------------------------------|-----|----|
| 1 | Can I reproduce and eliminate the issue with the **simplest possible 100% stable steps**? | ☐   | ☐ |
| 2 | Is the causal chain **free of logical jumps** from root cause to symptom?                  | ☐   | ☐ |
| 3 | After the fix, do **all** historical anomalies (including secondary ones) **disappear**?   | ☐   | ☐ |
| 4 | If I undo the fix, does the problem **guaranteed** reappear in original form?               | ☐   | ☐ |
| 5 | Is the fix **stable** across changes to compile flags, runtime options, timing, layout?    | ☐   | ☐ |
| 6 | Is there **no other independent suspect** that equally explains all the phenomena?        | ☐   | ☐ |
| 7 | Would an experienced colleague, after reviewing the chain, **agree the logic holds**?     | ☐   | ☐ |

> All seven "Yes" → ready to deliver. Any "No" → suspend delivery and dig more.

---

## D. Per-Stage Mini-Checklists (use WHILE working, not just at the end)

### After Stage 1 (Lock entry)

- [ ] Earliest `UVM_ERROR` / first anomaly timestamp captured?
- [ ] Earliest anomaly's full hierarchical path captured?
- [ ] This is NOT yet declared as root cause (correct posture)?
- [ ] E0 entry written into `evidence_chain.json`?

### After Stage 2 (5-Why)

- [ ] Every layer has at least one objective signal evidence?
- [ ] Every layer's `relation` field explains the link to the prior layer?
- [ ] No layer skipped without an explicit bridge node?
- [ ] DFS / BFS choice was justified by evidence, not by gut?
- [ ] BFS scoring (if used) kept high-score branches first?

### After Stage 3 (Build chain)

- [ ] Time monotonic (descending upstream)?
- [ ] Every hop has a `relation` field?
- [ ] Forward-derivation mental walkthrough reaches E0 bit-for-bit?
- [ ] No hop requires an untested precondition?

### After Stage 4 (Falsify)

- [ ] Toggle test done BOTH directions (inject + remove)?
- [ ] Toggle test ran multiple iterations, 100% reproducible?
- [ ] Counter-example search done (both directions)?
- [ ] All secondary anomalies explained by the RC?

### Before Stage 5 (Deliver)

- [ ] Section B (Discrimination) all "Yes"?
- [ ] Section C (Self-Check) all "Yes"?
- [ ] None of Section A (Exclusion) conditions triggered?

---

## E. Severity Tagging (recommended, not mandatory)

Tag each RC with a severity for downstream tracking:

| Severity  | Meaning                                                   | Example                                                |
|-----------|-----------------------------------------------------------|--------------------------------------------------------|
| **S0**    | Hangs boot-up, blocks CI gate, kills entire regression.   | Reset vector wrong; clock tree wrong.                  |
| **S1**    | Causes wrong-data signature on golden vectors.            | APB read returns wrong byte lane.                      |
| **S2**    | Causes rare miscompare on specific sequences / seeds.     | Constraint over-broad; hits reserved region.           |
| **S3**    | Cosmetic / lint / warning / coverage-only.                | A coverage hole that doesn't change behavior.          |

> Helps prioritize follow-ups.

---

## F. Common Pitfalls Mapped to Checklist Lines

| Pitfall                                              | Caught by                              |
|------------------------------------------------------|----------------------------------------|
| "We changed the seed and it passes"                  | C.5 (stability across changes)         |
| "Adding $display makes it work"                      | A.5 (fix-miracle)                      |
| "Earliest is also causal" (untested assumption)     | B.2 + B.3 (toggle + earliest)          |
| "It works on local but fails in CI"                 | C.5                                     |
| "Other team has different repro"                    | C.6 (no other independent suspect)     |
| "Constraint X is loose, let's tighten it, but unexplained why" | A.1 + C.2 (insufficient explanatory power) |

---

## G. Quick Decision Flowchart (when in doubt)

```
Is the candidate the EARLIEST anomaly on time axis?
  └─ No  → REJECT (A.3: temporal inversion)
  └─ Yes → continue
Does the candidate TOGGLE the error 100%?
  └─ No  → REJECT (A.2 + B.2: fails toggle)
  └─ Yes → continue
Does the candidate explain ALL secondary anomalies?
  └─ No  → REJECT (A.1 + B.1: insufficient power)
  └─ Yes → continue
Is there a fix-miracle smell?
  └─ Yes → REJECT (A.5)
  └─ No  → continue
Is the candidate itself derivable from something earlier?
  └─ Yes → CONTINUE UPSTREAM (A.6: causal inversion)
  └─ No  → RC CANDIDATE — proceed to Section C self-check
```

---

## TL;DR

- **Section A** rejects bad candidates early.
- **Section B** qualifies strong candidates.
- **Section C** finalizes RC.
- **Section D** keeps you honest during the process.
- **Sections E–G** are operational aids.

If you find yourself wanting to declare RC at any point without completing both B and C → DON'T. The discipline is the entire point of this skill.
