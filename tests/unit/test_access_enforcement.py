# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient

from cognitive_memory.bootstrap import build_context
from cognitive_memory.governance.capability_gate import set_capability_level
from cognitive_memory.identity import issue_grant, register_agent


class AccessEnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="node-token")
        self.http = TestClient(self.ctx.app)
        self.h = {"Authorization": "Bearer node-token"}

    def tearDown(self) -> None:
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_agent_write_requires_grant(self) -> None:
        register_agent(self.ctx.db, agent_id="agent:writer")
        g = issue_grant(
            self.ctx.db,
            "agent:writer",
            permissions=["memory.write", "memory.read"],
            banks=["personal"],
        )
        tok = g["agent_token"]
        # agent-only headers (no node bearer) should work for propose
        r = self.http.post(
            "/api/v1/memories",
            headers={"X-Agent-Id": "agent:writer", "X-Agent-Token": tok},
            json={"type": "semantic", "content": "agent write ok", "status": "candidate"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json().get("_actor"), "agent:writer")

        bad = self.http.post(
            "/api/v1/memories",
            headers={"X-Agent-Id": "agent:writer", "X-Agent-Token": "wrong"},
            json={"type": "semantic", "content": "nope", "status": "candidate"},
        )
        self.assertEqual(bad.status_code, 403)

    def test_hard_delete_needs_capability_and_confirm(self) -> None:
        created = self.http.post(
            "/api/v1/memories",
            headers=self.h,
            json={"type": "semantic", "content": "to delete", "status": "active"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        mid = created.json()["id"]

        no_confirm = self.http.delete(f"/api/v1/memories/{mid}?hard=true", headers=self.h)
        self.assertEqual(no_confirm.status_code, 400)

        locked = self.http.delete(
            f"/api/v1/memories/{mid}?hard=true&confirm=true", headers=self.h
        )
        self.assertEqual(locked.status_code, 403)

        set_capability_level(
            self.ctx.db, "MEMORY_HARD_DELETE", level="ACTIVE", enabled=True, actor="test"
        )
        ok = self.http.delete(
            f"/api/v1/memories/{mid}?hard=true&confirm=true", headers=self.h
        )
        self.assertEqual(ok.status_code, 200, ok.text)

    def test_node_info_and_entities(self) -> None:
        n = self.http.get("/api/v1/node", headers=self.h)
        self.assertEqual(n.status_code, 200)
        self.assertTrue(n.json().get("ok"))
        e = self.http.post(
            "/api/v1/entities",
            headers=self.h,
            json={"name": "rain", "kind": "concept"},
        )
        self.assertEqual(e.status_code, 200, e.text)
        listed = self.http.get("/api/v1/entities", headers=self.h)
        self.assertGreaterEqual(listed.json().get("count", 0), 1)


if __name__ == "__main__":
    unittest.main()
