# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from pydantic import ValidationError

from cognitive_memory.claims.lifecycle import ClaimLifecycle, ClaimLifecycleEngine
from cognitive_memory.security.context import SecurityContext
from cognitive_memory.tracing.service import JudgmentTraceService
from cognitive_memory.verification.engine import VerificationEngine
from cognitive_memory.verification.models import VerificationRecord, VerificationStatus
from cognitive_memory.visibility.models import VisibilityDecision
from cognitive_memory.visibility.service import evaluate_visibility, filter_and_justifications


class VisibilityTests(unittest.TestCase):
    def test_allow_and_cross_bank_deny(self) -> None:
        p = SecurityContext(bank_id="personal", owner_id="u1")
        ok = evaluate_visibility(p, object_ref="c1", object_bank="personal", requested_fields=["claim_id"])
        self.assertEqual(ok.decision, VisibilityDecision.ALLOW)
        deny = evaluate_visibility(p, object_ref="c2", object_bank="projects", requested_fields=["claim_id"])
        self.assertEqual(deny.decision, VisibilityDecision.DENY)
        self.assertFalse(deny.existence_disclosed)

    def test_evidence_invisible_blocks_verified_mark(self) -> None:
        p = SecurityContext(bank_id="personal")
        r = evaluate_visibility(
            p,
            object_ref="c1",
            requested_fields=["claim_id", "verification_status", "content"],
            evidence_visible=False,
        )
        self.assertEqual(r.decision, VisibilityDecision.PARTIAL)
        self.assertIn("claim_id", r.visible_fields)
        self.assertIn("verification_status", r.denied_fields)

    def test_and_justification_requires_full_parts(self) -> None:
        js = [
            {
                "id": "j1",
                "and_parts": [
                    {"authorized": True},
                    {"authorized": False},
                ],
            },
            {
                "id": "j2",
                "and_parts": [{"authorized": True}, {"authorized": True}],
            },
        ]
        usable = filter_and_justifications(js, principal_can_see_all_and_parts=True)
        self.assertEqual([u["id"] for u in usable], ["j2"])


class VerificationTests(unittest.TestCase):
    def test_no_record_no_verified_status_object(self) -> None:
        eng = VerificationEngine()
        assessed = eng.assess(claim_id="c1", evidence_refs=["e1"])
        self.assertNotEqual(assessed.status, VerificationStatus.VERIFIED)
        self.assertIsNone(eng.get_latest("c1"))

    def test_submit_requires_auth_and_live_evidence(self) -> None:
        eng = VerificationEngine()
        denied = eng.submit_verified(
            claim_id="c1", evidence_refs=["e1"], actor="u", authorized=False
        )
        self.assertFalse(denied["ok"])
        revoked = eng.submit_verified(
            claim_id="c1",
            evidence_refs=["e1"],
            actor="u",
            evidence_still_valid=False,
        )
        self.assertEqual(revoked.get("error"), "evidence_revoked_before_commit")
        ok = eng.submit_verified(claim_id="c1", evidence_refs=["e1"], actor="u")
        self.assertTrue(ok["ok"])
        self.assertEqual(eng.get_latest("c1").status, VerificationStatus.VERIFIED)

    def test_verified_record_validation(self) -> None:
        with self.assertRaises(ValidationError):
            VerificationRecord(
                record_id="r1",
                claim_id="c1",
                status=VerificationStatus.VERIFIED,
                evidence_refs=[],
                verified_at="2026-01-01T00:00:00Z",
            )

    def test_expired_not_usable_as_verified(self) -> None:
        eng = VerificationEngine()
        eng.submit_verified(claim_id="c1", evidence_refs=["e1"], actor="u")
        rec = eng.get_latest("c1")
        assert rec is not None
        expired = eng.mark_expired(rec.record_id)
        self.assertEqual(expired.status, VerificationStatus.EXPIRED)

    def test_disputed_priority(self) -> None:
        eng = VerificationEngine()
        r = eng.assess(
            claim_id="c1",
            evidence_refs=["e1"],
            counterevidence_refs=["e2"],
        )
        self.assertEqual(r.status, VerificationStatus.DISPUTED)
        life = VerificationEngine.lifecycle_from_layers(
            parse_status="parsed",
            evidence_status="supported",
            verification_status="disputed",
        )
        self.assertEqual(life, "disputed")


class LifecycleTests(unittest.TestCase):
    def test_illegal_transition(self) -> None:
        eng = ClaimLifecycleEngine()
        r = eng.transition_claim(
            "c1", ClaimLifecycle.VERIFIED, reason="x", evidence_refs=["e1"]
        )
        # proposed -> verified not directly allowed
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "illegal_transition")

    def test_supported_to_verified(self) -> None:
        eng = ClaimLifecycleEngine()
        eng.transition_claim("c1", ClaimLifecycle.SUPPORTED, reason="ev")
        r = eng.transition_claim(
            "c1", ClaimLifecycle.VERIFIED, reason="ok", evidence_refs=["e1"], actor="u"
        )
        self.assertTrue(r.ok)
        self.assertEqual(eng.get("c1"), ClaimLifecycle.VERIFIED)
        self.assertEqual(len(eng.history("c1")), 2)

    def test_expired_not_rejected(self) -> None:
        eng = ClaimLifecycleEngine()
        eng.transition_claim("c1", ClaimLifecycle.SUPPORTED, reason="a")
        eng.transition_claim("c1", ClaimLifecycle.EXPIRED, reason="ttl")
        self.assertEqual(eng.get("c1"), ClaimLifecycle.EXPIRED)
        self.assertNotEqual(eng.get("c1"), ClaimLifecycle.REJECTED)


class TraceTests(unittest.TestCase):
    def test_governance_traces_kept(self) -> None:
        svc = JudgmentTraceService()
        svc.record("visibility", governance_critical=True, reason_codes=["deny"])
        svc.record("retrieve", governance_critical=False)
        self.assertEqual(len(svc.list_traces(governance_only=True)), 1)
        failed = svc.record("verify", governance_critical=True, fail_write=True)
        self.assertIsNone(failed)
        self.assertEqual(len(svc.failures()), 1)


if __name__ == "__main__":
    unittest.main()
