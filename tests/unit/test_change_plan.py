# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.cognition.change_plan import (
    apply_change_plan,
    build_plans_for_observation,
    rollback_change_plan,
)
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import (
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SourceKind,
)
from cognitive_memory.events.bus import EventBus
from cognitive_memory.storage.db import Database


class ChangePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus(), spatiotemporal_enable=True)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_build_and_block_high_risk_apply(self) -> None:
        self.svc.propose_memory(
            MemoryProposeIn(
                content="主人喜欢番茄炒蛋",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.DIALOG,
                content="主人说其实不再喜欢番茄炒蛋了",
                idempotency_key="obs-plan-1",
            )
        )
        pack = build_plans_for_observation(self.svc, obs.id, dry_run=True, persist=True)
        self.assertTrue(pack.get("ok"))
        self.assertGreaterEqual(pack.get("count") or 0, 1)
        plans = self.svc.list_change_plans(limit=10)
        self.assertTrue(plans)

        pid = plans[0]["change_id"]
        denied = apply_change_plan(self.svc, pid, confirm=False)
        self.assertFalse(denied.get("ok"))
        self.assertEqual(denied.get("detail"), "confirm_required")

    def test_observation_write_receipt_fields_via_service(self) -> None:
        # 服务层同步落库；API 包装字段在集成测；此处确认幂等
        o1 = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.DIALOG,
                content="主人: 测试幂等\n丛雨: 好",
                idempotency_key="stable-key-abc",
            )
        )
        o2 = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.DIALOG,
                content="主人: 测试幂等\n丛雨: 好",
                idempotency_key="stable-key-abc",
            )
        )
        self.assertEqual(o1.id, o2.id)

    def test_merge_and_rollback(self) -> None:
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.USER_STATEMENT,
                content="主人喜欢滑板，周末常去滑板公园",
            )
        )
        a = self.svc.propose_memory(
            MemoryProposeIn(
                content="主人喜欢滑板",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                source_ids=[obs.id],
            )
        )
        b = self.svc.propose_memory(
            MemoryProposeIn(
                content="主人周末常去滑板公园",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                source_ids=[obs.id],
            )
        )
        plan = {
            "change_id": "cpl_test_merge",
            "observation_id": "obs_x",
            "target_memory_ids": [a.id, b.id],
            "change_type": "MERGE",
            "risk_level": "medium",
            "confidence": 0.8,
            "approval_requirement": "human",
            "execution_status": "proposed",
            "verification_status": "pending",
            "expected_changes": {},
        }
        self.svc.store_change_plan(plan)
        applied = apply_change_plan(self.svc, "cpl_test_merge", confirm=True)
        self.assertTrue(applied.get("ok"), applied)
        drop = self.svc.get_memory(a.id)
        self.assertEqual(drop.get("status"), MemoryStatus.SUPERSEDED.value)
        rb = rollback_change_plan(self.svc, "cpl_test_merge")
        self.assertTrue(rb.get("ok"), rb)
        restored = self.svc.get_memory(a.id)
        self.assertEqual(restored.get("status"), MemoryStatus.ACTIVE.value)


if __name__ == "__main__":
    unittest.main()
