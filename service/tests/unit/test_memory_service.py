# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from cognitive_memory.core.service import ConflictError, MemoryService
from cognitive_memory.domain.models import (
    ContextBuildIn,
    FeedbackIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    MemoryUpdateIn,
    ObservationIn,
    SearchQuery,
    SourceKind,
)
from cognitive_memory.events.bus import EventBus
from cognitive_memory.jobs.dispatcher import BackgroundRuntime
from cognitive_memory.storage.db import Database


class MemoryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self.tmp.name) / "memory.db"
        self.db = Database(db_path)
        self.bus = EventBus()
        self.svc = MemoryService(self.db, self.bus)
        self.rt = BackgroundRuntime(self.db, self.bus, self.svc, poll_interval_ms=50)
        self.rt.start()

    def tearDown(self) -> None:
        self.rt.stop(timeout=3.0)
        self.db.close()
        self.tmp.cleanup()

    def test_observation_idempotent_and_working_memory(self) -> None:
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.DIALOG,
                content="主人说喜欢吃番茄炒蛋",
                idempotency_key="obs-1",
            )
        )
        obs2 = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.DIALOG,
                content="主人说喜欢吃番茄炒蛋",
                idempotency_key="obs-1",
            )
        )
        self.assertEqual(obs.id, obs2.id)
        hits = self.svc.search(SearchQuery(query="番茄", types=[MemoryType.WORKING]))
        self.assertTrue(any("番茄" in m.content for m in hits))

    def test_version_conflict_and_search(self) -> None:
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                content="丛雨记得主人讨厌香菜",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        updated = self.svc.update_memory(
            mem.id,
            MemoryUpdateIn(content="丛雨记得主人不太喜欢香菜", expected_version=1),
        )
        self.assertEqual(updated.version, 2)
        with self.assertRaises(ConflictError):
            self.svc.update_memory(
                mem.id,
                MemoryUpdateIn(content="覆盖失败", expected_version=1),
            )
        found = self.svc.search(SearchQuery(query="香菜"))
        self.assertTrue(len(found) >= 1)

    def test_context_natural_language_query_matches_observation(self) -> None:
        self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.DIALOG,
                content="用户说他喜欢听夜航星",
            )
        )
        ctx = self.svc.build_context(
            ContextBuildIn(query="用户喜欢什么歌", token_budget=500)
        )
        self.assertTrue(ctx.fragments, "自然语言问句应能召回刚写入的观察")
        self.assertTrue(any("夜航星" in f["content"] for f in ctx.fragments))

    def test_context_and_feedback_invalidate(self) -> None:
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                content="主人喜欢雨天散步",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        ctx = self.svc.build_context(ContextBuildIn(query="散步", token_budget=500))
        self.assertTrue(ctx.fragments)
        self.svc.feedback(FeedbackIn(memory_id=mem.id, incorrect=True, note="说反了"))
        # wait worker
        for _ in range(40):
            trows = self.db.connect().execute(
                "SELECT status FROM tasks WHERE task_type='memory.review_feedback'"
            ).fetchall()
            if trows and all(r["status"] == "done" for r in trows):
                break
            self.rt.run_tasks_once()
            time.sleep(0.05)
        got = self.svc.get_memory(mem.id)
        self.assertEqual(got["status"], MemoryStatus.INVALIDATED.value)

    def test_outbox_recoverable(self) -> None:
        # 停后台循环，避免与手动 dispatch 抢同一批 pending
        self.rt.stop(timeout=3.0)
        self.svc.capture_observation(
            ObservationIn(source_kind=SourceKind.VIDEO_OBSERVATION, content="看了芙莉莲")
        )
        pending_before = self.db.connect().execute(
            "SELECT COUNT(*) AS n FROM outbox WHERE status='pending'"
        ).fetchone()["n"]
        self.assertGreaterEqual(pending_before, 1)
        n = self.rt.dispatch_outbox_once()
        self.assertGreaterEqual(n, 1)
        pending = self.db.connect().execute(
            "SELECT COUNT(*) AS n FROM outbox WHERE status='pending'"
        ).fetchone()["n"]
        self.assertEqual(pending, 0)


if __name__ == "__main__":
    unittest.main()
