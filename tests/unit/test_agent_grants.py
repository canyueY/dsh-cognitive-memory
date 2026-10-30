# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.bootstrap import build_context
from cognitive_memory.identity import (
    AgentAccessError,
    issue_grant,
    list_audit,
    register_agent,
    require_agent_access,
    revoke_grant,
)


class AgentGrantsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="node-token")
        self.db = self.ctx.db

    def tearDown(self) -> None:
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_register_not_authorize(self) -> None:
        out = register_agent(self.db, agent_id="agent:a", display_name="Agent A")
        self.assertTrue(out["registered"])
        self.assertFalse(out["authorized"])
        with self.assertRaises(AgentAccessError) as cm:
            require_agent_access(
                self.db, "agent:a", "nope", permission="memory.read", bank="personal"
            )
        self.assertEqual(cm.exception.code, "no_grant")

    def test_grant_bank_isolation(self) -> None:
        register_agent(self.db, agent_id="agent:a")
        register_agent(self.db, agent_id="agent:b")
        ga = issue_grant(
            self.db,
            "agent:a",
            permissions=["memory.read"],
            banks=["personal"],
        )
        gb = issue_grant(
            self.db,
            "agent:b",
            permissions=["memory.read"],
            banks=["shared"],
        )
        tok_a = ga["agent_token"]
        tok_b = gb["agent_token"]
        require_agent_access(
            self.db, "agent:a", tok_a, permission="memory.read", bank="personal"
        )
        with self.assertRaises(AgentAccessError) as cm:
            require_agent_access(
                self.db, "agent:a", tok_a, permission="memory.read", bank="shared"
            )
        self.assertEqual(cm.exception.code, "bank_denied")
        with self.assertRaises(AgentAccessError):
            require_agent_access(
                self.db, "agent:b", tok_b, permission="memory.read", bank="personal"
            )

    def test_revoke_and_audit(self) -> None:
        register_agent(self.db, agent_id="agent:c")
        g = issue_grant(self.db, "agent:c", permissions=["memory.read", "memory.write"])
        tok = g["agent_token"]
        require_agent_access(self.db, "agent:c", tok, permission="memory.write")
        rev = revoke_grant(self.db, "agent:c", reason="user_request")
        self.assertTrue(rev["ok"])
        with self.assertRaises(AgentAccessError) as cm:
            require_agent_access(self.db, "agent:c", tok, permission="memory.read")
        self.assertEqual(cm.exception.code, "revoked")
        rows = list_audit(self.db, agent_id="agent:c", limit=50)
        decisions = {r["decision"] for r in rows}
        actions = {r["action"] for r in rows}
        self.assertIn("ok", decisions)
        self.assertIn("deny", decisions)
        self.assertIn("revoke", actions)

    def test_permission_denied(self) -> None:
        register_agent(self.db, agent_id="agent:d")
        g = issue_grant(self.db, "agent:d", permissions=["memory.read"], banks=["personal"])
        with self.assertRaises(AgentAccessError) as cm:
            require_agent_access(
                self.db,
                "agent:d",
                g["agent_token"],
                permission="memory.write",
                bank="personal",
            )
        self.assertEqual(cm.exception.code, "permission_denied")

    def test_http_agent_act_search_isolation(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(self.ctx.app)
        h = {"Authorization": "Bearer node-token"}
        # seed memory in personal
        r = client.post(
            "/api/v1/memories",
            headers=h,
            json={
                "type": "semantic",
                "content": "多Agent隔离测试记忆",
                "status": "active",
                "bank_id": "personal",
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        ra = client.post(
            "/api/v1/agents/register",
            headers=h,
            json={"agent_id": "agent:http-a", "display_name": "HA"},
        )
        self.assertEqual(ra.status_code, 200)
        ga = client.post(
            "/api/v1/agents/agent:http-a/grants",
            headers=h,
            json={"permissions": ["memory.read"], "banks": ["personal"]},
        )
        self.assertEqual(ga.status_code, 200, ga.text)
        tok = ga.json()["agent_token"]
        ok = client.post(
            "/api/v1/agents/act/search",
            json={
                "agent_id": "agent:http-a",
                "agent_token": tok,
                "query": "隔离",
                "bank": "personal",
            },
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        denied = client.post(
            "/api/v1/agents/act/search",
            json={
                "agent_id": "agent:http-a",
                "agent_token": tok,
                "query": "隔离",
                "bank": "shared",
            },
        )
        self.assertEqual(denied.status_code, 403)


if __name__ == "__main__":
    unittest.main()
