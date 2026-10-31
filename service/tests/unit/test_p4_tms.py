# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.judgment.truth_value import TruthValue
from cognitive_memory.storage.db import Database
from cognitive_memory.tms.engine import TruthMaintenanceEngine
from cognitive_memory.tms.models import BeliefStatus
from cognitive_memory.tms.scc import strongly_connected_components


class TmsEngineTests(unittest.TestCase):
    def test_and_or_support(self) -> None:
        eng = TruthMaintenanceEngine()
        eng.set_premise_truth("e1", TruthValue.TRUE)
        eng.set_premise_truth("e2", TruthValue.TRUE)
        eng.add_justification("c1", ["e1", "e2"], kind="support")
        prop = eng.propagate(["e1", "e2", "c1"])
        self.assertTrue(prop.ok)
        self.assertEqual(eng.belief("c1").status, BeliefStatus.IN)

        eng.set_premise_truth("e1", TruthValue.FALSE)
        eng.propagate(["e1", "c1"])
        self.assertEqual(eng.belief("c1").status, BeliefStatus.OUT)

    def test_alternate_justification_keeps_in(self) -> None:
        eng = TruthMaintenanceEngine()
        eng.set_premise_truth("e1", TruthValue.TRUE)
        eng.set_premise_truth("e2", TruthValue.TRUE)
        eng.add_justification("c1", ["e1"], kind="support")
        eng.add_justification("c1", ["e2"], kind="support")
        eng.propagate(["e1", "e2", "c1"])
        self.assertEqual(eng.belief("c1").status, BeliefStatus.IN)
        eng.set_premise_truth("e1", TruthValue.FALSE)
        eng.propagate(["e1", "c1"])
        self.assertEqual(eng.belief("c1").status, BeliefStatus.IN)

    def test_contradict_forces_out(self) -> None:
        eng = TruthMaintenanceEngine()
        eng.set_premise_truth("e1", TruthValue.TRUE)
        eng.set_premise_truth("counter", TruthValue.TRUE)
        eng.add_justification("c1", ["e1"], kind="support")
        eng.add_justification("c1", ["counter"], kind="contradict")
        eng.propagate(["e1", "counter", "c1"])
        self.assertEqual(eng.belief("c1").status, BeliefStatus.OUT)

    def test_scc_marks_unknown(self) -> None:
        eng = TruthMaintenanceEngine()
        eng.add_justification("a", ["b"], kind="support")
        eng.add_justification("b", ["a"], kind="support")
        eng.propagate(["a", "b"])
        marked = eng.mark_scc_unknown()
        self.assertTrue(set(marked) >= {"a", "b"})
        self.assertEqual(eng.belief("a").status, BeliefStatus.UNKNOWN)

    def test_budget_exhausted(self) -> None:
        eng = TruthMaintenanceEngine(max_nodes=2, max_depth=8)
        eng.set_premise_truth("p0", TruthValue.TRUE)
        prev = "p0"
        for i in range(1, 6):
            nid = f"n{i}"
            eng.add_justification(nid, [prev], kind="support")
            prev = nid
        prop = eng.propagate(["p0"], max_nodes=2)
        self.assertTrue(prop.budget_exhausted)

    def test_tarjan_components(self) -> None:
        edges = {"a": {"b"}, "b": {"a"}, "c": set()}
        comps = strongly_connected_components(["a", "b", "c"], edges)
        sizes = sorted(len(c) for c in comps)
        self.assertEqual(sizes, [1, 2])


class TmsClaimWireTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.store = ClaimStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_verify_adds_tms_justification(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星")
        cid = r["claim_id"]
        ok = self.store.submit_verified(cid, evidence_refs=["obs_tms_1"], actor="u")
        self.assertTrue(ok.get("ok"))
        self.assertTrue(ok.get("tms", {}).get("ok"))
        bel = self.store.tms.engine.belief(cid)
        self.assertEqual(bel.status, BeliefStatus.IN)

    def test_dispute_invalidates_belief(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星")
        cid = r["claim_id"]
        self.store.submit_verified(cid, evidence_refs=["obs_tms_2"], actor="u")
        self.assertEqual(self.store.tms.engine.belief(cid).status, BeliefStatus.IN)
        self.store.transition(cid, "disputed", reason="counter", evidence_refs=["c1"])
        self.assertEqual(self.store.tms.engine.belief(cid).status, BeliefStatus.OUT)

    def test_impact_preview(self) -> None:
        eng = self.store.tms.engine
        eng.set_premise_truth("e1", TruthValue.TRUE)
        eng.add_justification("c1", ["e1"])
        eng.add_justification("c2", ["c1"])
        eng.propagate(["e1", "c1", "c2"])
        impact = eng.impact("e1")
        self.assertIn("c1", impact["affected"])
        self.assertIn("c2", impact["affected"])


if __name__ == "__main__":
    unittest.main()
