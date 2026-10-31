# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.shadow_replay import run_shadow_replay
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.storage.db import Database


class ShadowReplayTests(unittest.TestCase):
    def test_writes_only_to_shadow(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            src_path = Path(td) / "source.db"
            shadow_path = Path(td) / "shadow.db"
            src = Database(src_path)
            svc = MemoryService(src, EventBus())
            svc.propose_memory(
                MemoryProposeIn(
                    content="我喜欢夜航星",
                    type=MemoryType.SEMANTIC,
                    status=MemoryStatus.ACTIVE,
                )
            )
            svc.propose_memory(
                MemoryProposeIn(
                    content="随便聊聊今天天气系统摘要无关内容填充",
                    type=MemoryType.EPISODIC,
                    status=MemoryStatus.ACTIVE,
                )
            )
            src.close()

            report = run_shadow_replay(src_path, shadow_path, limit=10)
            self.assertTrue(report.ok)
            self.assertGreaterEqual(report.scanned, 2)
            self.assertGreaterEqual(report.proposed + report.same_as, 1)

            # source has no claims table writes — open RO and ensure claims absent or empty
            import sqlite3

            conn = sqlite3.connect(f"file:{src_path.as_posix()}?mode=ro", uri=True)
            try:
                tables = {
                    r[0]
                    for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if "claims" in tables:
                    n = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
                    self.assertEqual(n, 0)
            finally:
                conn.close()

            shadow = Database(shadow_path)
            shadow.ensure_schema()
            with shadow.exclusive() as c:
                n = c.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
                if c.in_transaction:
                    c.commit()
            shadow.close()
            self.assertGreaterEqual(n, 1)

            sidecar = shadow_path.with_suffix(".shadow_report.json")
            self.assertTrue(sidecar.is_file())
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertTrue(data.get("ok"))


if __name__ == "__main__":
    unittest.main()
