#!/usr/bin/env python3
"""test_iter_flow.py — Smoke / unit tests for iter-flow scripts.

Stdlib only. Exits 0 on success.
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
ROOT = HERE.parent
TEMPLATES = ROOT / "assets" / "templates"


def run(name: str, args: list, cwd: Path | None = None) -> tuple[int, str, str]:
    cmd = [sys.executable, str(HERE / name), *args]
    proc = subprocess.run(cmd, cwd=cwd or HERE, capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stdout, proc.stderr


class TestIterInit(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.mkdtemp()
        # Use a fresh workdir each test to avoid relying on cwd.
        self.workdir = Path(self.td) / "proj"
        self.workdir.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_init_creates_tree(self):
        code, out, err = run("iter_init.py",
                             ["debug_502_spike",
                              "--workdir", str(self.workdir),
                              "--background", "P99 latency spike",
                              "--hypotheses", "h1|h2|h3"])
        self.assertEqual(code, 0, err)
        task = self.workdir / "experiments" / "debug_502_spike"
        self.assertTrue((task / "card.md").is_file())
        self.assertTrue((task / "scripts").is_dir())
        self.assertTrue((task / "data").is_dir())
        body = (task / "card.md").read_text(encoding="utf-8")
        self.assertIn("P99 latency spike", body)
        self.assertIn("h1", body)
        self.assertIn("h3", body)

    def test_init_refuses_overwrite_without_force(self):
        run("iter_init.py", ["my_task", "--workdir", str(self.workdir)])
        code, out, err = run("iter_init.py",
                             ["my_task", "--workdir", str(self.workdir)])
        # Should refuse (exit 2 or 3)
        self.assertIn(code, (2, 3))


class TestIterNew(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.mkdtemp()
        self.workdir = Path(self.td) / "proj"
        self.workdir.mkdir()
        self.task_dir = self.workdir / "experiments" / "my_task"
        run("iter_init.py", ["my_task",
                             "--workdir", str(self.workdir),
                             "--background", "x",
                             "--hypotheses", "h1|h2"])

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def _iter_new(self, args2: list) -> tuple[int, str, str]:
        return run("iter_new.py", [str(self.task_dir), *args2])

    def test_first_iter_is_iter_01(self):
        code, out, err = self._iter_new(["--title", "first hypothesis",
                                          "--hypothesis", "H assumes X"])
        self.assertEqual(code, 0, err)
        created = list(self.task_dir.glob("iter_*.md"))
        self.assertEqual(len(created), 1)
        # Spaces in the title are coerced to hyphens for filename safety.
        self.assertEqual(created[0].name, "iter_01_first-hypothesis.md")
        body = created[0].read_text(encoding="utf-8")
        for section in ["回顾引用", "目的", "实验条件", "检查方法",
                        "结果", "Findings", "决策"]:
            self.assertIn(section, body)
        self.assertIn("首轮", body)  # review-refs section says first iter

    def test_sequential_iter_autoincrements(self):
        for title in ("h1", "h2", "h3"):
            code, _, err = self._iter_new(["--title", title, "--hypothesis", "x"])
            self.assertEqual(code, 0, err)
        names = sorted(p.name for p in self.task_dir.glob("iter_*.md"))
        self.assertEqual(names, ["iter_01_h1.md", "iter_02_h2.md", "iter_03_h3.md"])

    def test_review_refs_populated_when_iters_exist(self):
        for title in ("h1", "h2"):
            self._iter_new(["--title", title, "--hypothesis", "x"])
        # Now create iter_03 and check it references both
        self._iter_new(["--title", "h3", "--hypothesis", "x"])
        body = (self.task_dir / "iter_03_h3.md").read_text(encoding="utf-8")
        self.assertIn("iter_01", body)
        self.assertIn("iter_02", body)

    def test_force_number_overrides_auto(self):
        code, _, err = self._iter_new(["--title", "force_test",
                                       "--number", "5",
                                       "--hypothesis", "x"])
        self.assertEqual(code, 0, err)
        self.assertTrue((self.task_dir / "iter_05_force_test.md").exists())

    def test_refuses_overwrite_without_force(self):
        self._iter_new(["--title", "once", "--hypothesis", "x", "--number", "1"])
        # Same number + same title -> file collides. Without --force, refuse.
        code, _, err = self._iter_new(["--title", "once", "--hypothesis", "x",
                                       "--number", "1"])
        self.assertIn(code, (2, 3))


class TestIterReview(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.mkdtemp()
        self.workdir = Path(self.td) / "proj"
        self.workdir.mkdir()
        self.task_dir = self.workdir / "experiments" / "task"
        run("iter_init.py", ["task", "--workdir", str(self.workdir),
                             "--background", "x", "--hypotheses", "h1"])

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def _add_iter(self, n: int, title: str, body_findings: str = "(not filled yet)",
                  decision_done: str = "") -> None:
        path = self.task_dir / f"iter_{n:02d}_{title}.md"
        text = f"""# iter_{n:02d}: {title}

## 回顾引用

## 目的

(Purpose text for iter {n}.)

## 实验条件

- 脚本: scripts/x.sh

## 检查方法

执行 `bash scripts/x.sh`.

## 结果

(执行后填)

## Findings

{body_findings}

## 决策

- [ ] **启动 iter_{n + 1:02d}** — proceed
{('- [x] **' + decision_done + '**') if decision_done else ''}
"""
        path.write_text(text, encoding="utf-8")

    def test_no_iters_returns_1(self):
        code, out, err = run("iter_review.py", [str(self.task_dir)])
        self.assertEqual(code, 1)

    def test_summarizes_last_3(self):
        for i in (1, 2, 3, 4, 5):
            self._add_iter(i, f"iter_{i}",
                            body_findings=f"iter {i} finding line",
                            decision_done="进入修复轮" if i == 4 else "")
        code, out, err = run("iter_review.py", [str(self.task_dir)])
        self.assertEqual(code, 0, err)
        # Should show iter_03, iter_04, iter_05 (the last 3)
        self.assertIn("iter_03", out)
        self.assertIn("iter_04", out)
        self.assertIn("iter_05", out)
        # Should NOT show iter_01 (only last 3)
        self.assertNotIn("Purpose text for iter 1.", out)
        # decision_done for iter_04 should be checked
        self.assertIn("进入修复轮", out)

    def test_3_or_fewer_iters_all_shown(self):
        for i in (1, 2, 3):
            self._add_iter(i, f"iter_{i}",
                            body_findings=f"finding {i}",
                            decision_done="")
        code, out, err = run("iter_review.py", [str(self.task_dir)])
        self.assertEqual(code, 0, err)
        for i in (1, 2, 3):
            self.assertIn(f"finding {i}", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
