# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from pydantic import ValidationError

from cognitive_memory.claims.ast import Atom, ClaimAST, Unresolved
from cognitive_memory.judgment.relations import (
    ClaimRelation,
    RelationDecision,
    RelationResult,
    evaluate_same_as,
)
from cognitive_memory.judgment.truth_value import TruthValue, tv_and, tv_not, tv_or


class TruthValueTests(unittest.TestCase):
    def test_and_table(self) -> None:
        T, F, U = TruthValue.TRUE, TruthValue.FALSE, TruthValue.UNKNOWN
        cases = [
            (T, T, T),
            (T, F, F),
            (T, U, U),
            (F, F, F),
            (F, U, F),
            (U, U, U),
            (F, T, F),
            (U, T, U),
            (U, F, F),
        ]
        for a, b, expect in cases:
            self.assertEqual(tv_and(a, b), expect, (a, b))

    def test_or_table(self) -> None:
        T, F, U = TruthValue.TRUE, TruthValue.FALSE, TruthValue.UNKNOWN
        cases = [
            (T, T, T),
            (T, F, T),
            (T, U, T),
            (F, F, F),
            (F, U, U),
            (U, U, U),
            (F, T, T),
            (U, T, T),
            (U, F, U),
        ]
        for a, b, expect in cases:
            self.assertEqual(tv_or(a, b), expect, (a, b))

    def test_not(self) -> None:
        self.assertEqual(tv_not(TruthValue.TRUE), TruthValue.FALSE)
        self.assertEqual(tv_not(TruthValue.FALSE), TruthValue.TRUE)
        self.assertEqual(tv_not(TruthValue.UNKNOWN), TruthValue.UNKNOWN)


class RelationResultTests(unittest.TestCase):
    def _atom(self, arg: str, *, scope: dict | None = None) -> ClaimAST:
        return ClaimAST(
            root=Atom(subject="user", predicate="喜欢", arguments=[arg], modality="preference"),
            scope=scope or {},
        )

    def test_same_as_reflexive_symmetric_transitive(self) -> None:
        a = self._atom("YOASOBI")
        b = self._atom("yoasobi")  # normalize
        c = ClaimAST(root=Atom(subject="用户", predicate="喜爱", arguments=["YOASOBI"], modality="preference"))
        r_aa = evaluate_same_as(a, a)
        self.assertEqual(r_aa.final_relation, ClaimRelation.SAME_AS)
        r_ab = evaluate_same_as(a, b)
        r_ba = evaluate_same_as(b, a)
        self.assertEqual(r_ab.decision, RelationDecision.ACCEPTED)
        self.assertEqual(r_ba.decision, RelationDecision.ACCEPTED)
        r_ac = evaluate_same_as(a, c)
        r_bc = evaluate_same_as(b, c)
        self.assertEqual(r_ac.final_relation, ClaimRelation.SAME_AS)
        self.assertEqual(r_bc.final_relation, ClaimRelation.SAME_AS)

    def test_semantic_similar_not_same_as(self) -> None:
        a = self._atom("YOASOBI")
        b = self._atom("夜に駆ける")  # related but not equal
        r = evaluate_same_as(a, b)
        self.assertEqual(r.decision, RelationDecision.REJECTED)
        self.assertNotEqual(r.final_relation, ClaimRelation.SAME_AS)

    def test_scope_mismatch(self) -> None:
        a = self._atom("茶", scope={"domain": "food"})
        b = self._atom("茶", scope={"domain": "music"})
        r = evaluate_same_as(a, b)
        self.assertEqual(r.decision, RelationDecision.REJECTED)
        self.assertIn("scope_mismatch", r.reason_codes)

    def test_unresolved_abstain(self) -> None:
        a = ClaimAST(root=Unresolved(raw_text="...", reason_codes=["x"]))
        b = self._atom("茶")
        r = evaluate_same_as(a, b)
        self.assertEqual(r.decision, RelationDecision.ABSTAINED)
        self.assertEqual(r.final_relation, ClaimRelation.UNKNOWN)

    def test_illegal_combo_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RelationResult(
                candidate_relation=ClaimRelation.SAME_AS,
                decision=RelationDecision.ACCEPTED,
                final_relation=ClaimRelation.UNKNOWN,
            )


if __name__ == "__main__":
    unittest.main()
