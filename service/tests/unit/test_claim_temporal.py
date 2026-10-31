# -*- coding: utf-8 -*-
"""Judgment supersession / retraction / expiry temporal traceability."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.storage.db import Database


class ClaimTemporalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        self.store = ClaimStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def _claim(self, text: str, **kwargs):
        return self.store.propose_from_text(text, **kwargs)

    def test_supersede_preserves_old_and_sets_temporal_decision(self) -> None:
        old = self._claim("我喜欢夜航星", validity_from="2026-01-01T00:00:00Z")
        new = self._claim("我喜欢别的歌")
        result = self.store.supersede(
            old["claim_id"],
            new["claim_id"],
            reason="preference changed",
            evidence_refs=["obs_new"],
            actor="user",
            confidence=0.93,
        )
        self.assertTrue(result.get("ok"), result)
        old_pack = self.store.get(old["claim_id"], follow_redirect=False)
        self.assertEqual(old_pack["lifecycle"], "superseded")
        self.assertEqual(old_pack["superseded_by"], new["claim_id"])
        self.assertTrue(old_pack["superseded_at"])
        self.assertTrue(old_pack["validity_to"])
        self.assertEqual(old_pack["validity_from"], "2026-01-01T00:00:00Z")
        # Old claim remains queryable; new claim is not silently rewritten.
        self.assertIsNotNone(self.store.get(old["claim_id"], follow_redirect=False))
        self.assertEqual(self.store.get(new["claim_id"], follow_redirect=False)["lifecycle"], "proposed")

        decisions = self.store.list_decisions(old["claim_id"])
        d = next(x for x in decisions if x["operation"] == "superseded")
        self.assertEqual(d["operation"], "superseded")
        self.assertEqual(d["replacement_claim_id"], new["claim_id"])
        self.assertEqual(d["trigger_evidence"], ["obs_new"])
        self.assertEqual(d["actor"], "user")
        self.assertTrue(d["trace_id"])

    def test_retract_without_replacement(self) -> None:
        c = self._claim("用户说过喜欢某个东西")
        result = self.store.retract(
            c["claim_id"],
            reason="misattributed third-party opinion",
            evidence_refs=["obs_correction"],
            actor="user",
        )
        self.assertTrue(result.get("ok"), result)
        pack = self.store.get(c["claim_id"], follow_redirect=False)
        self.assertEqual(pack["lifecycle"], "retracted")
        self.assertTrue(pack["retracted_at"])
        self.assertIsNone(pack["superseded_by"])
        self.assertTrue(pack["validity_to"])
        decisions = self.store.list_decisions(c["claim_id"])
        d = next(x for x in decisions if x["operation"] == "retracted")
        self.assertEqual(d["operation"], "retracted")
        self.assertIsNone(d["replacement_claim_id"])

    def test_expire_is_not_retraction(self) -> None:
        c = self._claim("用户本周在出差")
        result = self.store.expire(c["claim_id"], reason="trip ended")
        self.assertTrue(result.get("ok"), result)
        pack = self.store.get(c["claim_id"], follow_redirect=False)
        self.assertEqual(pack["lifecycle"], "expired")
        self.assertTrue(pack["expired_at"])
        self.assertFalse(pack["retracted_at"])
        self.assertFalse(pack["superseded_at"])
        decisions = self.store.list_decisions(c["claim_id"])
        d = next(x for x in decisions if x["operation"] == "expired")
        self.assertEqual(d["operation"], "expired")

    def test_verified_sets_last_confirmed(self) -> None:
        c = self._claim("用户喜欢夜航星")
        self.store.attach_evidence(c["claim_id"], "obs_1", role="support")
        up = self.store.transition(c["claim_id"], "supported", reason="support")
        self.assertTrue(up.get("ok"), up)
        ok = self.store.transition(
            c["claim_id"], "verified", reason="verified", evidence_refs=["obs_1"]
        )
        self.assertTrue(ok.get("ok"), ok)
        pack = self.store.get(c["claim_id"], follow_redirect=False)
        self.assertEqual(pack["lifecycle"], "verified")
        self.assertTrue(pack["last_confirmed_at"])

    def test_invalid_replacement_does_not_mutate(self) -> None:
        c = self._claim("用户喜欢夜航星")
        before = self.store.get(c["claim_id"], follow_redirect=False)
        result = self.store.supersede(c["claim_id"], "clm_missing", reason="bad")
        self.assertFalse(result.get("ok"))
        after = self.store.get(c["claim_id"], follow_redirect=False)
        self.assertEqual(before["lifecycle"], after["lifecycle"])
        self.assertFalse(after["superseded_at"])


if __name__ == "__main__":
    unittest.main()

class ClaimTemporalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient
        from cognitive_memory.bootstrap import build_context

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="node-token")
        self.http = TestClient(self.ctx.app)
        self.headers = {"Authorization": "Bearer node-token"}

    def tearDown(self) -> None:
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_supersede_and_decisions_api(self) -> None:
        a = self.http.post(
            "/api/v1/claims/propose",
            headers=self.headers,
            json={"text": "我喜欢夜航星", "validity_from": "2026-01-01T00:00:00Z"},
        )
        self.assertEqual(a.status_code, 200, a.text)
        aid = a.json()["claim_id"]
        b = self.http.post(
            "/api/v1/claims/propose",
            headers=self.headers,
            json={"text": "我喜欢别的歌"},
        )
        self.assertEqual(b.status_code, 200, b.text)
        bid = b.json()["claim_id"]
        r = self.http.post(
            f"/api/v1/claims/{aid}/supersede",
            headers=self.headers,
            json={
                "replacement_claim_id": bid,
                "reason": "preference changed",
                "evidence_refs": ["obs_api"],
                "actor": "user",
                "confidence": 0.9,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(r.json()["to_status"], "superseded")
        self.assertTrue(r.json()["decision_id"])
        claims = self.http.get(f"/api/v1/claims/{aid}", headers=self.headers)
        self.assertEqual(claims.status_code, 200, claims.text)
        self.assertEqual(claims.json()["claim"]["superseded_by"], bid)
        self.assertTrue(claims.json()["claim"]["superseded_at"])
        decisions = self.http.get(f"/api/v1/claims/{aid}/decisions", headers=self.headers)
        self.assertEqual(decisions.status_code, 200, decisions.text)
        ops = [x["operation"] for x in decisions.json()["items"]]
        self.assertIn("superseded", ops)

    def test_retract_api(self) -> None:
        a = self.http.post(
            "/api/v1/claims/propose",
            headers=self.headers,
            json={"text": "用户说过喜欢某个东西"},
        )
        aid = a.json()["claim_id"]
        r = self.http.post(
            f"/api/v1/claims/{aid}/retract",
            headers=self.headers,
            json={"reason": "misattributed"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["to_status"], "retracted")
        c = self.http.get(f"/api/v1/claims/{aid}", headers=self.headers).json()["claim"]
        self.assertEqual(c["lifecycle"], "retracted")
        self.assertTrue(c["retracted_at"])



if __name__ == "__main__":
    unittest.main()
