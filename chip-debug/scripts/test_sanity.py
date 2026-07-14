#!/usr/bin/env python3
"""test_sanity.py — Smoke / unit tests for chip-debug scripts.

Runs without dependencies. Exits 0 on success, non-zero on failure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE


# -----------------------------------------------------------------------------
# Sample log fixtures
# -----------------------------------------------------------------------------

UVM_LOG_SAMPLE = """\
[100 ns] UVM_INFO @ tb.env: starting test
[200 ns] UVM_INFO @ tb.env.agent.driver: sent addr 0x080
[210 ns] UVM_INFO @ tb.env.agent.driver: prdata expected 0xCAFEBABE
[8440 ns] UVM_INFO @ tb.dut.cpu: cycle 12 starting
[8450 ns] UVM_ERROR @ tb.env.apb_mst.scoreboard] read data mismatch: expected 0xCAFEBABE actual 0xDEADBEEF
[8460 ns] UVM_FATAL @ tb.env.apb_mst.scoreboard] too many errors, abort
[9999 ns] UVM_INFO @ tb.env: end of test
"""

VCS_LOG_SAMPLE = """\
Chronologic VCS simulator
$Time      Severity    Message
       0 ps     Info    Starting simulation
  100000 ps    Info    Reset done
  8450000 ps   Error   SVA fail: at apb_slave.sv:42 assertion prdata_match
 10000000 ps   Info    End of sim
"""


# -----------------------------------------------------------------------------
# Helper: run a script as a subprocess, capture stdout/stderr
# -----------------------------------------------------------------------------

def run_script(name: str, args: list, cwd: Path | None = None) -> tuple[int, str, str]:
    cmd = [sys.executable, str(SCRIPTS / name), *args]
    proc = subprocess.run(cmd, cwd=cwd or SCRIPTS, capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


# -----------------------------------------------------------------------------
# Tests for parse_uvm_log.py
# -----------------------------------------------------------------------------

class TestParseUvmLog(unittest.TestCase):
    def test_first_error_extraction(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "run.log"
            log.write_text(UVM_LOG_SAMPLE)
            code, out, err = run_script("parse_uvm_log.py", [str(log), "--first-error"])
            self.assertEqual(code, 0, f"non-zero exit, stderr={err}")
            # Earliest error is UVM_ERROR @ 8450 ns (UVM_FATAL fires later at 8460 ns).
            self.assertIn("UVM_ERROR", out)
            # --first-error returns exactly one block.
            self.assertEqual(out.count("--- ["), 1)
            # Offset (+N more) tells the user there are additional errors not shown.
            self.assertIn("more errors not shown", out)

    def test_all_errors(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "run.log"
            log.write_text(UVM_LOG_SAMPLE)
            code, out, err = run_script("parse_uvm_log.py", [str(log), "--all-errors", "--context", "1"])
            self.assertEqual(code, 0, err)
            self.assertGreaterEqual(out.count("--- ["), 2)

    def test_vcs_format(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "trace.log"
            log.write_text(VCS_LOG_SAMPLE)
            code, out, err = run_script("parse_uvm_log.py", [str(log), "--first-error"])
            self.assertEqual(code, 0, err)
            self.assertIn("SVA", out)  # "SVA fail" should be detected

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "run.log"
            log.write_text(UVM_LOG_SAMPLE)
            code, out, err = run_script("parse_uvm_log.py",
                                        [str(log), "--all-errors", "--format", "json"])
            self.assertEqual(code, 0, err)
            payload = json.loads(out)
            self.assertIn("errors", payload)
            self.assertGreaterEqual(len(payload["errors"]), 2)
            self.assertTrue(any(e["severity"] == "UVM_FATAL" for e in payload["errors"]))

    def test_no_errors(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "empty.log"
            log.write_text("[0 ns] UVM_INFO @ tb: nothing to report\n")
            code, out, err = run_script("parse_uvm_log.py", [str(log), "--first-error"])
            self.assertEqual(code, 0, err)
            self.assertIn("No UVM_ERROR", out)

    def test_detect_vcs(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "trace.log"
            log.write_text(VCS_LOG_SAMPLE)
            code, out, err = run_script("parse_uvm_log.py", [str(log), "--detect"])
            self.assertEqual(code, 0, err)
            self.assertEqual(out.strip(), "vcs")


# -----------------------------------------------------------------------------
# Tests for evidence_chain.py
# -----------------------------------------------------------------------------

class TestEvidenceChain(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.mkdtemp()
        self.session_dir = Path(self.td) / "session"
        self.session_dir.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_init_creates_file(self):
        code, out, err = run_script("evidence_chain.py", ["init", str(self.session_dir)])
        self.assertEqual(code, 0, err)
        chain = self.session_dir / "1_evidence" / "evidence_chain.json"
        self.assertTrue(chain.exists())

    def test_add_and_validate(self):
        run_script("evidence_chain.py", ["init", str(self.session_dir), "--force"])
        chain = self.session_dir / "1_evidence" / "evidence_chain.json"

        # Seed the locked-entry block (normally populated at Stage 1)
        with open(chain, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["locked_entry"] = {
            "time": "8450 ns",
            "signal": "tb.env.apb_mst.scoreboard",
            "actual": "expected=0xCAFEBABE actual=0xDEADBEEF",
            "expected": "0xCAFEBABE",
            "source": "log:run.log:1247",
        }
        with open(chain, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # E0 — symptom
        code, out, err = run_script("evidence_chain.py",
                                    ["add", str(chain),
                                     "--node-id", "E0", "--stage", "Stage1.LockEntry",
                                     "--layer", "0", "--hop", "symptom",
                                     "--time", "8450 ns",
                                     "--signal", "tb.env.sc.mismatch",
                                     "--actual", "expected=0xCAFEBABE actual=0xDEADBEEF",
                                     "--expected", "0xCAFEBABE",
                                     "--source", "log:run.log:1247",
                                     "--evidence-kind", "log_line",
                                     "--relation", "",
                                     "--confidence", "1.0",
                                     "--note", "first UVM_ERROR"])
        self.assertEqual(code, 0, err)

        # L1 — must have a relation
        code, out, err = run_script("evidence_chain.py",
                                    ["add", str(chain),
                                     "--node-id", "L1", "--stage", "Stage2.5Why",
                                     "--layer", "1", "--hop", "5-Why-L1",
                                     "--time", "8444 ns",
                                     "--signal", "tb.dut.apb_slave.rdata[31:0]",
                                     "--actual", "0xDEADBEEF",
                                     "--expected", "0xCAFEBABE",
                                     "--source", "wave:run.fsdb:@8444ns",
                                     "--evidence-kind", "wave_dump",
                                     "--relation", "Scoreboard samples rdata 1 cycle earlier",
                                     "--confidence", "0.97"])
        self.assertEqual(code, 0, err)

        # validate (no-strict so warnings are advisory)
        code, out, err = run_script("evidence_chain.py", ["validate", str(chain), "--no-strict"])
        self.assertEqual(code, 0, err)
        self.assertIn("OK", out)

        # validate (strict by default — E0 missing relation is fine (root), L1 is fine)
        code, out, err = run_script("evidence_chain.py", ["validate", str(chain)])
        self.assertEqual(code, 0, err)
        self.assertIn("OK", out)

    def test_forward_check_detects_missing_relation(self):
        run_script("evidence_chain.py", ["init", str(self.session_dir), "--force"])
        chain = self.session_dir / "1_evidence" / "evidence_chain.json"

        # Add a node WITHOUT relation (use --no-strict to bypass add-time check)
        run_script("evidence_chain.py",
                   ["add", str(chain),
                    "--node-id", "L1", "--stage", "Stage2.5Why",
                    "--layer", "1", "--hop", "5-Why-L1",
                    "--time", "8444 ns",
                    "--signal", "tb.dut.foo",
                    "--actual", "X",
                    "--source", "wave:run.fsdb",
                    "--evidence-kind", "wave_dump",
                    "--relation", "",     # intentionally empty
                    "--confidence", "0.5",
                    "--no-strict"])
        code, out, err = run_script("evidence_chain.py", ["forward-check", str(chain)])
        self.assertEqual(code, 1, f"expected non-zero; out={out} err={err}")
        self.assertIn("missing relation", out + err)


# -----------------------------------------------------------------------------
# Tests for evidence_chain.time-check (time-unidirectional invariant)
# -----------------------------------------------------------------------------

class TestTimeCheck(unittest.TestCase):
    """Verify the new `time-check` subcommand and the auto-parse of
    `--time '8450 ns'` -> `timestamp_ns: 8450.0`."""

    def setUp(self) -> None:
        self.td = tempfile.mkdtemp()
        self.session_dir = Path(self.td) / "session"
        self.session_dir.mkdir()
        run_script("evidence_chain.py", ["init", str(self.session_dir), "--force"])
        chain = self.session_dir / "1_evidence" / "evidence_chain.json"
        d = json.loads(chain.read_text(encoding="utf-8"))
        d["locked_entry"] = {
            "time": "8450 ns", "signal": "tb.env.sc",
            "actual": "wrong", "expected": "right",
            "source": "log:run.log:1247",
        }
        chain.write_text(json.dumps(d), encoding="utf-8")
        self.chain = chain

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def _add(self, nid, layer, time_str, signal):
        return run_script("evidence_chain.py",
                          ["add", str(self.chain),
                           "--node-id", nid, "--stage", "Stage2.5Why",
                           "--layer", str(layer), "--hop", "wh",
                           "--time", time_str, "--signal", signal,
                           "--actual", "x", "--expected", "y",
                           "--source", "wave:fsdb:@0ns",
                           "--evidence-kind", "wave_dump",
                           "--confidence", "0.9",
                           "--relation", "drives"])

    def test_add_auto_parses_timestamp_ns(self):
        self._add("L1", 1, "8444 ns", "tb.dut.foo")
        d = json.loads(self.chain.read_text(encoding="utf-8"))
        l1 = next(n for n in d["nodes"] if n["node_id"] == "L1")
        self.assertEqual(l1.get("timestamp_ns"), 8444.0)

    def test_time_check_passes_for_monotonic_chain(self):
        self._add("E0_sim", 0, "8450 ns", "tb.env.sc")
        self._add("L1", 1, "8444 ns", "tb.dut.foo")
        self._add("L2", 2, "8430 ns", "tb.dut.bar")
        self._add("RC", -1, "N/A", "tb/tests/x.sv:1")
        code, out, err = run_script("evidence_chain.py",
                                    ["time-check", str(self.chain)])
        self.assertEqual(code, 0, err)
        self.assertIn("monotonically non-decreasing", out)

    def test_time_check_fails_on_violation(self):
        self._add("E0_sim", 0, "8450 ns", "tb.env.sc")
        self._add("L1", 1, "8444 ns", "tb.dut.foo")
        self._add("L2", 2, "9000 ns", "tb.dut.bar")     # LATER than E0 -> violation
        code, out, err = run_script("evidence_chain.py",
                                    ["time-check", str(self.chain)])
        self.assertEqual(code, 1, f"expected non-zero; out={out} err={err}")
        combined = out + err
        self.assertIn("VIOLATION", combined)
        self.assertIn("DECREASES", combined)

    def test_RC_without_timestamp_is_fine(self):
        self._add("E0_sim", 0, "8450 ns", "tb.env.sc")
        self._add("L1", 1, "8444 ns", "tb.dut.foo")
        self._add("RC", -1, "N/A", "tb/tests/x.sv:1")
        code, out, err = run_script("evidence_chain.py",
                                    ["time-check", str(self.chain)])
        self.assertEqual(code, 0, err)


# -----------------------------------------------------------------------------
# Tests for decision_log.py
# -----------------------------------------------------------------------------

class TestDecisionLog(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.mkdtemp()
        self.session_dir = Path(self.td) / "session"
        self.session_dir.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_init_and_add_and_summary(self):
        code, out, err = run_script("decision_log.py",
                                    ["init", str(self.session_dir), "--force"])
        self.assertEqual(code, 0, err)
        log = self.session_dir / "2_decisions" / "decision_log.json"
        self.assertTrue(log.exists())

        code, out, err = run_script("decision_log.py",
                                    ["add", str(log),
                                     "--hypothesis", "Locked UVM_ERROR @ 8450 ns",
                                     "--evidence-ref", "log:run.log:1247",
                                     "--verdict", "accept",
                                     "--reason", "First UVM_ERROR, will reverse-trace.",
                                     "--tag", "stage1.lock_entry"])
        self.assertEqual(code, 0, err)

        code, out, err = run_script("decision_log.py", ["summary", str(log), "--recent"])
        self.assertEqual(code, 0, err)
        self.assertIn("accept", out)


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
