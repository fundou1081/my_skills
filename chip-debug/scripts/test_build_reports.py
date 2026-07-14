#!/usr/bin/env python3
"""test_build_reports.py — Verify build_reports.py renders chain_report.md and exploration_log.md correctly.

Stdlib-only. Exits 0 on success.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def run_script(name: str, args: list, cwd: Path | None = None) -> tuple[int, str, str]:
    cmd = [sys.executable, str(HERE / name), *args]
    proc = subprocess.run(cmd, cwd=cwd or HERE, capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


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
            "confidence": 0.97,
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
        },
    ],
}

SAMPLE_DECISIONS = {
    "schema_version": "1.0",
    "session_id": "rca_session_20260714_120000",
    "decisions": [
        {
            "decision_id": "D-lock",
            "hypothesis": "Locked UVM_ERROR @ 8450 ns",
            "evidence_ref": "log:run.log:1247",
            "verdict": "accept",
            "reason": "First UVM_ERROR, target for reverse-tracing.",
            "tag": "stage1.lock_entry",
            "timestamp": "2026-07-14T12:01:00+08:00",
        },
        {
            "decision_id": "D-t1",
            "hypothesis": "RC = constraint c_addr over-broad",
            "verdict": "accept",
            "reason": "Inject reproduced, remove cleared over 5 seeds.",
            "tag": "stage4.toggle_test",
            "timestamp": "2026-07-14T13:00:00+08:00",
        },
        {
            "decision_id": "D-mb",
            "hypothesis": "Module boundary: local",
            "verdict": "accept",
            "reason": "RC stays inside tb.tests.",
            "tag": "stage5.module_boundary",
            "timestamp": "2026-07-14T13:01:00+08:00",
        },
    ],
}


class TestBuildReports(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.mkdtemp()
        self.session = Path(self.td) / "session"
        self.session.mkdir()
        (self.session / "1_evidence" / "signal_snapshots").mkdir(parents=True)
        (self.session / "2_decisions").mkdir()
        (self.session / "9_output").mkdir()
        (self.session / "1_evidence" / "evidence_chain.json").write_text(
            json.dumps(SAMPLE_CHAIN, indent=2), encoding="utf-8"
        )
        (self.session / "2_decisions" / "decision_log.json").write_text(
            json.dumps(SAMPLE_DECISIONS, indent=2), encoding="utf-8"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    # ---- chain-report ----

    def test_chain_report_writes_file(self):
        out = self.session / "9_output" / "chain_report.md"
        code, out_text, err = run_script("build_reports.py",
                                        ["chain-report", str(self.session)])
        self.assertEqual(code, 0, f"chain-report failed: {err}")
        self.assertTrue(out.is_file())
        body = out.read_text(encoding="utf-8")
        # All major sections present
        for sec in ["# Root Cause Report", "## 1. Symptom Summary",
                    "## 2. Causal Chain", "## 3. Per-hop Evidence",
                    "## 4. Falsification Evidence", "## 5. Suggested Fix",
                    "## 6. Self-Check Confirmation", "## 7. Appendix — Artifacts",
                    "## 8. Root Cause Elevation", "## TL;DR"]:
            self.assertIn(sec, body)

    def test_chain_report_includes_hops(self):
        out = self.session / "9_output" / "chain_report.md"
        run_script("build_reports.py",
                   ["chain-report", str(self.session)])
        body = out.read_text(encoding="utf-8")
        # All nodes should appear at least once
        for nid in ["RC", "E0", "L1", "L2"]:
            self.assertIn(f"[{nid}]", body)
        # Causal chain DAG should include both root and symptom terminal
        self.assertIn("(root)", body)
        self.assertIn("symptom", body)

    def test_chain_report_per_hop_section(self):
        out = self.session / "9_output" / "chain_report.md"
        run_script("build_reports.py",
                   ["chain-report", str(self.session)])
        body = out.read_text(encoding="utf-8")
        # Per-hop evidence: each hop should have its own h3 + key/value lines
        self.assertIn("### [RC] — root", body)
        self.assertIn("### [L1] — 5-Why-L1", body)
        self.assertIn("### [L2] — 5-Why-L2", body)
        self.assertIn("### [E0] — symptom", body)

    def test_chain_report_falsification_section_includes_toggle(self):
        out = self.session / "9_output" / "chain_report.md"
        run_script("build_reports.py",
                   ["chain-report", str(self.session)])
        body = out.read_text(encoding="utf-8")
        self.assertIn("### 4.1 Toggle test", body)
        # The decision text should appear under toggle test
        self.assertIn("reproduced", body.lower())
        # Time-unidirectional subsection heading present
        self.assertIn("### 4.4 Time-unidirectional check", body)

    def test_chain_report_uses_template_fields(self):
        out = self.session / "9_output" / "chain_report.md"
        run_script("build_reports.py",
                   ["chain-report", str(self.session),
                    "--author", "TestAuthor",
                    "--module", "tb/dut/apb_slave",
                    "--log-ref", "run.log"])
        body = out.read_text(encoding="utf-8")
        self.assertIn("**Author**: TestAuthor", body)
        self.assertIn("**Module / Project**: tb/dut/apb_slave", body)
        self.assertIn("**Reference run / log**: run.log", body)

    def test_chain_report_verify_matches_after_rebuild(self):
        out = self.session / "9_output" / "chain_report.md"
        run_script("build_reports.py",
                   ["chain-report", str(self.session)])
        first = out.read_text(encoding="utf-8")
        run_script("build_reports.py",
                   ["chain-report", str(self.session)])
        second = out.read_text(encoding="utf-8")
        # Drop the "Date:" line which changes per invocation
        def drop_date(text):
            lines = text.splitlines()
            return "\n".join(ln for ln in lines if not ln.startswith("**Date**"))
        self.assertEqual(drop_date(first), drop_date(second))

    # ---- exploration-log ----

    def test_exploration_log_writes_file(self):
        out = self.session / "9_output" / "exploration_log.md"
        code, out_text, err = run_script("build_reports.py",
                                        ["exploration-log", str(self.session)])
        self.assertEqual(code, 0, f"exploration-log failed: {err}")
        self.assertTrue(out.is_file())
        body = out.read_text(encoding="utf-8")
        self.assertIn("# Exploration Log", body)
        self.assertIn("## Branch / Hypothesis Index", body)
        self.assertIn("## Cross-Session Handoff", body)

    def test_exploration_log_includes_decisions(self):
        out = self.session / "9_output" / "exploration_log.md"
        run_script("build_reports.py",
                   ["exploration-log", str(self.session)])
        body = out.read_text(encoding="utf-8")
        # Each decision id should appear at least once
        for did in ["D-lock", "D-t1", "D-mb"]:
            self.assertIn(did, body)
        # Tags should appear
        self.assertIn("stage4.toggle_test", body)
        self.assertIn("stage5.module_boundary", body)

    # ---- all ----

    def test_all_subcommand_produces_both(self):
        cr = self.session / "9_output" / "chain_report.md"
        el = self.session / "9_output" / "exploration_log.md"
        code, out, err = run_script("build_reports.py",
                                    ["all", str(self.session)])
        self.assertEqual(code, 0, err)
        self.assertTrue(cr.is_file())
        self.assertTrue(el.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
