# -*- coding: utf-8 -*-
"""E2.1 黄金样本 + E2.2 冲突保留 + E2.3 晋升显式 + E2.5 Gate LOCKED。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.cognition.conflict import list_conflicts, record_conflict
from cognitive_memory.cognition.promote import PROMOTION_RULES, evaluate_promotion, maybe_promote
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import (
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SearchQuery,
    SourceKind,
)
from cognitive_memory.events.bus import EventBus
from cognitive_memory.governance.capability_gate import list_capabilities
from cognitive_memory.identity import ensure_default_principals
from cognitive_memory.memory.banks import ensure_default_banks
from cognitive_memory.storage.db import Database

FIXTURE = Path(__file__).parent / "fixtures" / "golden_samples.json"


def _load_samples() -> list[dict]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(data.get("samples") or [])


class GoldenSampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        ensure_default_principals(self.db)
        ensure_default_banks(self.db)
        self.svc = MemoryService(self.db, EventBus())

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def _ingest_propose(self, obs_spec: dict, prop_spec: dict):
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind(obs_spec["source_kind"]),
                content=obs_spec["content"],
                producer=obs_spec.get("producer") or "test",
                metadata=dict(obs_spec.get("metadata") or {}),
            )
        )
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                type=MemoryType(prop_spec.get("type") or "semantic"),
                content=prop_spec["content"],
                status=MemoryStatus(prop_spec.get("status") or "candidate"),
                source_ids=[obs.id],
                metadata=dict(prop_spec.get("metadata") or {}),
            )
        )
        return obs, mem

    def test_fixture_kinds_present(self) -> None:
        kinds = {s["kind"] for s in _load_samples()}
        self.assertEqual(
            kinds, {"fact", "inference", "external", "conflict", "unknown"}
        )

    def test_fact_and_unknown_and_external(self) -> None:
        by_id = {s["id"]: s for s in _load_samples()}
        for sid in ("fact_user_preference", "unknown_vague", "external_import"):
            s = by_id[sid]
            obs, mem = self._ingest_propose(s["observation"], s["propose"])
            self.assertEqual(
                (mem.metadata or {}).get("epistemic"), s["expect"]["epistemic"]
            )
            if sid == "unknown_vague":
                self.assertEqual(mem.status, MemoryStatus.CANDIDATE)
                self.assertFalse(maybe_promote(self.svc, mem.id))
            if sid == "external_import":
                ident = (obs.metadata or {}).get("identity") or {}
                self.assertEqual(
                    ident.get("agent_id"), s["expect"].get("identity_agent")
                )
            if sid == "fact_user_preference":
                # User-origin metadata is not database-backed verification.
                self.assertFalse(maybe_promote(self.svc, mem.id))
                after = self.svc.get_memory(mem.id)
                self.assertEqual(after["status"], MemoryStatus.CANDIDATE.value)

    def test_inference_coerced_without_sources_and_no_silent_promote(self) -> None:
        s = next(x for x in _load_samples() if x["id"] == "inference_agent_guess")
        # 无 source_ids：ACTIVE 必须被 coerce
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                type=MemoryType.SEMANTIC,
                content=s["propose"]["content"],
                status=MemoryStatus.ACTIVE,
                source_ids=[],
                metadata=dict(s["propose"].get("metadata") or {}),
            )
        )
        self.assertEqual(mem.status, MemoryStatus.CANDIDATE)
        self.assertIn("promotion_guard", mem.metadata)
        decision = evaluate_promotion(
            {
                "status": "candidate",
                "type": "semantic",
                "evidence": [],
                "metadata": mem.metadata,
            }
        )
        self.assertFalse(decision["promote"])

    def test_conflict_both_retained_and_searchable(self) -> None:
        s = next(x for x in _load_samples() if x["kind"] == "conflict")
        _, a = self._ingest_propose(s["a"]["observation"], s["a"]["propose"])
        _, b = self._ingest_propose(s["b"]["observation"], s["b"]["propose"])
        pack = record_conflict(self.svc, a.id, b.id, note="golden conflict")
        self.assertTrue(pack["ok"])
        confs = list_conflicts(self.svc, a.id)
        self.assertTrue(confs)
        hits_a = self.svc.search(SearchQuery(query="喜欢吃辣", limit=20))
        hits_b = self.svc.search(SearchQuery(query="不吃辣", limit=20))
        self.assertTrue(any(m.id == a.id for m in hits_a))
        self.assertTrue(any(m.id == b.id for m in hits_b))
        # 两侧状态仍非 deleted
        self.assertNotEqual(self.svc.get_memory(a.id)["status"], "invalidated")
        self.assertNotEqual(self.svc.get_memory(b.id)["status"], "invalidated")

    def test_promotion_rules_documented_and_gate_locked(self) -> None:
        self.assertIn("force_activate", str(PROMOTION_RULES))
        self.assertIn("silent_active_without_rule", PROMOTION_RULES["forbidden"])
        caps = list_capabilities(self.db)
        by = {c["capability"]: c for c in caps}
        for name in ("RL_OFFLINE_TRAINING", "RL_POLICY_DEPLOYMENT", "ADVANCED_VALUE_EVALUATION"):
            self.assertEqual(by[name]["level"], "LOCKED")
            self.assertFalse(by[name]["enabled"])


if __name__ == "__main__":
    unittest.main()
