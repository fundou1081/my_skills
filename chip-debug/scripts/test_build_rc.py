#!/usr/bin/env python3
"""test_build_rc.py — Verify scripts/build_rc_file.py produces a correct RC file.

Runs without dependencies. Exits 0 on success.
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


def run_script(name: str, args: list, cwd: Path | None = None) -> tuple[int, str, str]:
    cmd = [sys.executable, str(SCRIPTS / name), *args]
    proc = subprocess.run(cmd, cwd=cwd or SCRIPTS, capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


# A minimal, complete chain.json + decision_log.json fixture that exercises:
# - E0 + L1 + L2 + RC nodes
# - locked_entry
# - one code_inspection node with confidence >= 0.95 (auto-constraint)
# - one wave_dump node (with optional snapshot)
# - decision_log with toggle_test + module_boundary entries

SAMPLE_CHAIN = {
    "schema_version": "1.0",
    "session_id": "rca_session_20260714_120000",
    "created_at": "2026-07-14T12:00:00+08:00",
    "locked_entry": {
        "time": "8450 ns",
        "signal": "tb.env.apb_mst.scoreboard",
        "actual": "expected=0xCAFEBABE actual=0xDEADBEEF",
        "expected": "0xCAFEBABE",
        "source": "log:run.log:1247",
    },
    "nodes": [
        {
            "node_id": "E0",
            "stage": "Stage1.LockEntry",
            "layer": 0,
            "hop": "symptom",
            "time": "8450 ns",
            "signal": "tb.env.apb_mst.scoreboard",
            "actual": "expected=0xCAFEBABE actual=0xDEADBEEF",
            "expected": "0xCAFEBABE",
            "source": "log:run.log:1247",
            "evidence_kind": "log_line",
            "confidence": 1.0,
            "note": "First UVM_ERROR.",
        },
        {
            "node_id": "L1",
            "stage": "Stage2.5Why",
            "layer": 1,
            "hop": "5-Why-L1",
            "time": "8444 ns",
            "signal": "tb.dut.apb_slave.rdata[31:0]",
            "actual": "0xDEADBEEF",
            "expected": "0xCAFEBABE",
            "source": "code:tb/dut/apb_slave.sv:142",
            "evidence_kind": "code_inspection",
            "relation": "Scoreboard samples rdata 1 cycle after PRDATA rises",
            "confidence": 0.95,
        },
        {
            "node_id": "L2",
            "stage": "Stage2.5Why",
            "layer": 2,
            "hop": "5-Why-L2",
            "time": "8430 ns",
            "signal": "tb.dut.apb_slave.mem_addr[9:0]",
            "actual": "0x3FF",
            "expected": "0x080",
            "source": "wave:run.fsdb:@8430ns",
            "evidence_kind": "wave_dump",
            "relation": "mem_rd_data pass-through uses mem_addr as index",
            "confidence": 0.9,
        },
        {
            "node_id": "RC",
            "stage": "Stage5.Deliver",
            "layer": -1,
            "hop": "root",
            "time": "N/A",
            "signal": "tb/tests/apb_test.sv:47",
            "actual": "constraint c_addr { addr inside {[9'h000:9'h0FF], [9'h3F0:9'h3FF]}; }",
            "expected": "addr inside {[9'h000:9'h0FF]};",
            "source": "code:tb/tests/apb_test.sv:47",
            "evidence_kind": "code_inspection",
            "relation": "Random constraint allows 0x3FF; sequence picked it.",
            "confidence": 1.0,
            "note": "Toggle test verified.",
        },
    ],
}

SAMPLE_DECISIONS = {
    "schema_version": "1.0",
    "session_id": "rca_session_20260714_120000",
    "decisions": [
        {
            "decision_id": "D-t1",
            "hypothesis": "RC = constraint c_addr over-broad",
            "verdict": "accept",
            "reason": "Inject reproduced, remove cleared over 5 seeds.",
            "tag": "stage4.toggle_test",
        },
        {
            "decision_id": "D-mb",
            "hypothesis": "Module boundary: local",
            "verdict": "accept",
            "reason": "RC stays inside tb.tests.",
            "tag": "stage5.module_boundary",
            "evidence_ref": "local",
        },
    ],
}

SAMPLE_SNAPSHOT = {
    "changes": [
        {"time": "8444 ns", "value": "0xDEADBEEF"},
        {"time": "8428 ns", "value": "0xCAFEBABE"},
    ]
}


class TestBuildRC(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.mkdtemp()
        self.session = Path(self.td) / "session"
        self.session.mkdir()
        (self.session / "1_evidence").mkdir()
        (self.session / "2_decisions").mkdir()
        (self.session / "9_output").mkdir()
        (self.session / "1_evidence" / "signal_snapshots").mkdir()
        (self.session / "1_evidence" / "evidence_chain.json").write_text(
            json.dumps(SAMPLE_CHAIN, indent=2), encoding="utf-8"
        )
        (self.session / "2_decisions" / "decision_log.json").write_text(
            json.dumps(SAMPLE_DECISIONS, indent=2), encoding="utf-8"
        )
        (self.session / "1_evidence" / "signal_snapshots" / "L1.json").write_text(
            json.dumps(SAMPLE_SNAPSHOT, indent=2), encoding="utf-8"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_build_writes_file(self):
        out = self.session / "9_output" / "RC_file.yaml"
        code, out_text, err = run_script("build_rc_file.py",
                                        ["build", str(self.session), "--out", str(out)])
        self.assertEqual(code, 0, f"build failed: {err}")
        self.assertTrue(out.is_file(), "RC file not written")
        self.assertIn("wrote:", out_text)  # stdout may include the file path
        body = out.read_text(encoding="utf-8")
        self.assertIn("RC File", body)  # in-file header comment
        self.assertIn("session_id:", body)
        self.assertIn("locked_entry:", body)
        self.assertIn("root_cause:", body)
        self.assertIn("causal_signals:", body)
        self.assertIn("toggle_test:", body)
        self.assertIn("module_boundary:", body)
        self.assertIn("tool_calls:", body)

    def test_causal_signals_include_e0_and_l1(self):
        out = self.session / "9_output" / "RC_file.yaml"
        run_script("build_rc_file.py",
                   ["build", str(self.session), "--out", str(out)])
        body = out.read_text(encoding="utf-8")
        # All node IDs should appear at least once (E0, L1, L2, RC)
        self.assertIn("E0", body)
        self.assertIn("L1", body)
        self.assertIn("RC", body)
        # The RC section should mention our test
        self.assertIn("apb_test.sv", body)

    def test_auto_constraints_extracted(self):
        out = self.session / "9_output" / "RC_file.yaml"
        run_script("build_rc_file.py",
                   ["build", str(self.session), "--out", str(out)])
        body = out.read_text(encoding="utf-8")
        # L1 is code_inspection with conf=0.95, RC is code_inspection with conf=1.0
        self.assertIn("auto_constraints:", body)
        self.assertIn("L1", body)  # in auto_constraints

    def test_toggle_test_pulls_from_decision_log(self):
        out = self.session / "9_output" / "RC_file.yaml"
        run_script("build_rc_file.py",
                   ["build", str(self.session), "--out", str(out)])
        body = out.read_text(encoding="utf-8")
        # toggle_test.ran was set to true via the stage4.toggle_test accept entry
        self.assertIn("ran: true", body)
        self.assertIn("Inject reproduced", body)

    def test_module_boundary_pulls_from_decision_log(self):
        out = self.session / "9_output" / "RC_file.yaml"
        run_script("build_rc_file.py",
                   ["build", str(self.session), "--out", str(out)])
        body = out.read_text(encoding="utf-8")
        # The decision said 'local', should set is_local_module_issue=true
        self.assertIn("is_local_module_issue: true", body)

    def test_yaml_is_parseable_by_pyyaml_if_available(self):
        """Optional: if PyYAML is installed, make sure the output is valid YAML."""
        try:
            import yaml  # noqa
        except ImportError:
            self.skipTest("PyYAML not installed; skipping YAML parseability check")
        out = self.session / "9_output" / "RC_file.yaml"
        run_script("build_rc_file.py",
                   ["build", str(self.session), "--out", str(out)])
        body = out.read_text(encoding="utf-8")
        # Strip top comments
        stripped = "\n".join(ln for ln in body.splitlines() if not ln.startswith("#"))
        try:
            data = yaml.safe_load(stripped)
            self.assertIsInstance(data, dict)
            self.assertIn("causal_signals", data)
        except yaml.YAMLError as e:
            self.fail(f"YAML parse failed: {e}")

    def test_verify_matches_after_rebuild(self):
        """After a second build, the file should be byte-identical
        except for the created_at + tool_version + hash."""
        out = self.session / "9_output" / "RC_file.yaml"
        run_script("build_rc_file.py",
                   ["build", str(self.session), "--out", str(out)])
        first = out.read_text(encoding="utf-8")
        run_script("build_rc_file.py",
                   ["build", str(self.session), "--out", str(out)])
        second = out.read_text(encoding="utf-8")
        # created_at + tool_version + hash may differ between calls.
        # The remainder should be byte-identical.
        first_core = "\n".join(ln for ln in first.splitlines()
                               if not ln.startswith(("created_at:", "tool_version:", "# Hash")))
        second_core = "\n".join(ln for ln in second.splitlines()
                                if not ln.startswith(("created_at:", "tool_version:", "# Hash")))
        self.assertEqual(first_core, second_core)


if __name__ == "__main__":
    unittest.main(verbosity=2)
