# -*- coding: utf-8 -*-
"""崩溃恢复：未投递 outbox / pending tasks 在重启后可继续。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import ObservationIn, SourceKind
from cognitive_memory.events.bus import EventBus
from cognitive_memory.jobs.dispatcher import BackgroundRuntime
from cognitive_memory.storage.db import Database


class OutboxRecoveryTests(unittest.TestCase):
    def test_pending_outbox_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "memory.db"
            db1 = Database(db_path)
            svc1 = MemoryService(db1, EventBus())
            svc1.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.DIALOG,
                    content="恢复测试：主人喜欢抹茶",
                    producer="test",
                )
            )
            pending_before = db1.connect().execute(
                "SELECT COUNT(*) AS n FROM outbox WHERE status='pending'"
            ).fetchone()["n"]
            self.assertGreaterEqual(pending_before, 1)
            db1.close()

            # 模拟重启：新连接 + dispatcher
            db2 = Database(db_path)
            bus = EventBus()
            svc2 = MemoryService(db2, bus)
            rt = BackgroundRuntime(db2, bus, svc2, poll_interval_ms=50)
            delivered = rt.dispatch_outbox_once()
            self.assertGreaterEqual(delivered, 1)
            pending_after = db2.connect().execute(
                "SELECT COUNT(*) AS n FROM outbox WHERE status='pending'"
            ).fetchone()["n"]
            self.assertEqual(pending_after, 0)
            # 任务也可跑
            rt.run_tasks_once()
            rt.stop()
            db2.close()


if __name__ == "__main__":
    unittest.main()
