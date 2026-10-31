# -*- coding: utf-8 -*-
"""P8: cross-bank Claim GET — opaque 404, no text leak."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cognitive_memory.bootstrap import build_context
from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.security.disclosure import response_leaks_secret


class P8CrossBankClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="node-token")
        self.client = TestClient(self.ctx.app)
        self.h = {"Authorization": "Bearer node-token"}
        self.secret = "跨Bank机密夜航星歌词_LEAK_PROBE"
        store = ClaimStore(self.ctx.db)
        self.claim = store.propose_from_text(self.secret, bank_id="projects")
        self.cid = self.claim["claim_id"]

    def tearDown(self) -> None:
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_agent_personal_cannot_see_projects_claim(self) -> None:
        ra = self.client.post(
            "/api/v1/agents/register",
            headers=self.h,
            json={"agent_id": "agent:bank-a", "display_name": "A"},
        )
        self.assertEqual(ra.status_code, 200, ra.text)
        ga = self.client.post(
            "/api/v1/agents/agent:bank-a/grants",
            headers=self.h,
            json={"permissions": ["memory.read"], "banks": ["personal"]},
        )
        self.assertEqual(ga.status_code, 200, ga.text)
        tok = ga.json()["agent_token"]
        denied = self.client.get(
            f"/api/v1/claims/{self.cid}",
            headers={
                "X-Agent-Id": "agent:bank-a",
                "X-Agent-Token": tok,
            },
        )
        self.assertEqual(denied.status_code, 404)
        body = denied.json()
        self.assertFalse(response_leaks_secret(body, self.secret))
        detail = body.get("detail") or body
        self.assertEqual(detail.get("code"), "not_found")
        # missing claim uses same opaque shape
        missing = self.client.get(
            "/api/v1/claims/clm_does_not_exist",
            headers={
                "X-Agent-Id": "agent:bank-a",
                "X-Agent-Token": tok,
            },
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            (missing.json().get("detail") or {}).get("code"),
            "not_found",
        )

    def test_agent_with_projects_grant_can_read(self) -> None:
        self.client.post(
            "/api/v1/agents/register",
            headers=self.h,
            json={"agent_id": "agent:bank-b", "display_name": "B"},
        )
        gb = self.client.post(
            "/api/v1/agents/agent:bank-b/grants",
            headers=self.h,
            json={"permissions": ["memory.read"], "banks": ["projects"]},
        )
        tok = gb.json()["agent_token"]
        ok = self.client.get(
            f"/api/v1/claims/{self.cid}",
            headers={
                "X-Agent-Id": "agent:bank-b",
                "X-Agent-Token": tok,
            },
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["claim"]["id"], self.cid)


if __name__ == "__main__":
    unittest.main()
