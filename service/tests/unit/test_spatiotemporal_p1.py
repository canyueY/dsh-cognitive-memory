# -*- coding: utf-8 -*-
"""P1 时空元数据：T-01 发生时间≠记录时间；ST-04 历史位置≠当前位置。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import (
    ContextBuildIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SearchQuery,
    SourceKind,
)
from cognitive_memory.domain.spatiotemporal import (
    attach_spatiotemporal,
    is_historical_space,
    spatiotemporal_score,
)
from cognitive_memory.events.bus import EventBus
from cognitive_memory.storage.db import Database


class SpatiotemporalP1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus(), spatiotemporal_enable=True)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_t01_occurred_at_independent_of_recorded_at(self) -> None:
        """T-01：发生时间与记录时间独立保存。"""
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.DIALOG,
                content="主人在工作室完成了分镜模块",
                occurred_at="2026-10-20T12:00:00Z",
                idempotency_key="t01-obs",
            )
        )
        self.assertEqual(obs.occurred_at, "2026-10-20T12:00:00Z")
        self.assertNotEqual(obs.occurred_at, obs.created_at)
        st = (obs.metadata or {}).get("spatiotemporal") or {}
        temporal = st.get("temporal") or {}
        self.assertEqual(temporal.get("occurredAt"), "2026-10-20T12:00:00Z")
        self.assertEqual(temporal.get("recordedAt"), obs.created_at)
        self.assertNotEqual(temporal.get("occurredAt"), temporal.get("recordedAt"))

    def test_st04_historical_space_not_treated_as_current(self) -> None:
        """ST-04：历史位置在 mode=current 下降权，不挤掉当前空间。"""
        past = self.svc.propose_memory(
            MemoryProposeIn(
                content="显示器位于房间A",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                metadata={
                    "spatial": {
                        "kind": "room",
                        "name": "房间A",
                        "spaceId": "room-a",
                        "precision": "exact",
                        "validFrom": "2026-01-01T00:00:00Z",
                        "validUntil": "2026-06-01T00:00:00Z",
                    }
                },
            )
        )
        current = self.svc.propose_memory(
            MemoryProposeIn(
                content="显示器位于房间B",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                metadata={
                    "spatial": {
                        "kind": "room",
                        "name": "房间B",
                        "spaceId": "room-b",
                        "precision": "exact",
                        "validFrom": "2026-06-01T00:00:00Z",
                    }
                },
            )
        )
        self.assertTrue(is_historical_space(past.metadata))
        self.assertFalse(is_historical_space(current.metadata))
        self.assertLess(
            spatiotemporal_score(past.metadata, mode="current"),
            spatiotemporal_score(current.metadata, mode="current"),
        )

        hits = self.svc.search(
            SearchQuery(query="显示器位于", limit=10, mode="current")
        )
        ids = [m.id for m in hits]
        self.assertIn(current.id, ids)
        self.assertIn(past.id, ids)
        # current 应排在 historical 之前
        self.assertLess(ids.index(current.id), ids.index(past.id))

        ctx = self.svc.build_context(
            ContextBuildIn(query="显示器位于", limit=5, mode="current")
        )
        self.assertTrue(ctx.fragments)
        self.assertEqual(ctx.fragments[0]["id"], current.id)

        # 历史模式：旧位置不应被当成「无效」而排到队尾
        hist = self.svc.search(
            SearchQuery(query="显示器位于", limit=10, mode="historical")
        )
        hist_ids = [m.id for m in hist]
        self.assertLessEqual(hist_ids.index(past.id), hist_ids.index(current.id))

    def test_attach_does_not_invent_space(self) -> None:
        meta = attach_spatiotemporal({}, occurred_at="2026-01-01T00:00:00Z", recorded_at="2026-01-02T00:00:00Z")
        self.assertIn("spatiotemporal", meta)
        self.assertNotIn("spatial", meta["spatiotemporal"])


if __name__ == "__main__":
    unittest.main()
