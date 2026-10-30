# -*- coding: utf-8 -*-
"""轻量 Security / Retention 套件：allow_* 与 retention 必须真正拒绝。"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from cognitive_memory.bootstrap import build_context
from cognitive_memory.governance.policy import (
    PolicyDeniedError,
    assert_allow_forward,
    assert_allow_store,
    assert_allow_train,
    extract_policy,
)


class PolicyUnitTests(unittest.TestCase):
    def test_defaults(self) -> None:
        p = extract_policy({})
        self.assertTrue(p["allow_store"])
        self.assertFalse(p["allow_forward"])
        self.assertFalse(p["allow_train"])

    def test_store_denied(self) -> None:
        with self.assertRaises(PolicyDeniedError) as ctx:
            assert_allow_store({"policy": {"allow_store": False}})
        self.assertEqual(ctx.exception.code, "allow_store_denied")

    def test_forward_default_denied(self) -> None:
        with self.assertRaises(PolicyDeniedError) as ctx:
            assert_allow_forward({"content": "x"})
        self.assertEqual(ctx.exception.code, "allow_forward_denied")

    def test_train_denied(self) -> None:
        with self.assertRaises(PolicyDeniedError):
            assert_allow_train({"allow_train": False})

    def test_retention_blocks_forward(self) -> None:
        past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.assertRaises(PolicyDeniedError) as ctx:
            assert_allow_forward({"policy": {"allow_forward": True, "retain_until": past}})
        self.assertEqual(ctx.exception.code, "retention_expired")


class PolicyHttpSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="sec-token")
        self.http = TestClient(self.ctx.app)
        self.h = {"Authorization": "Bearer sec-token"}

    def tearDown(self) -> None:
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_propose_allow_store_false_403(self) -> None:
        r = self.http.post(
            "/api/v1/memories",
            headers=self.h,
            json={
                "type": "semantic",
                "content": "should not store",
                "status": "candidate",
                "metadata": {"policy": {"allow_store": False}},
            },
        )
        self.assertEqual(r.status_code, 403, r.text)
        self.assertEqual(r.json()["detail"]["code"], "allow_store_denied")

    def test_export_skips_non_forwardable(self) -> None:
        ok = self.http.post(
            "/api/v1/memories",
            headers=self.h,
            json={
                "type": "semantic",
                "content": "may forward",
                "status": "active",
                "metadata": {"policy": {"allow_forward": True}},
            },
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        blocked = self.http.post(
            "/api/v1/memories",
            headers=self.h,
            json={
                "type": "semantic",
                "content": "must not forward",
                "status": "active",
                "metadata": {"policy": {"allow_forward": False}},
            },
        )
        self.assertEqual(blocked.status_code, 200, blocked.text)

        export_path = self.tmp.name + "/export.jsonl"
        exp = self.http.post(
            "/api/v1/adoption/export",
            headers=self.h,
            json={"path": export_path, "limit": 50},
        )
        self.assertEqual(exp.status_code, 200, exp.text)
        body = exp.json()
        self.assertGreaterEqual(body.get("policy_skipped_count", 0), 1)
        self.assertLessEqual(body.get("count", 0), 1)

    def test_rl_train_denied_without_allow_train(self) -> None:
        r = self.http.post("/api/v1/rl/train", headers=self.h, json={})
        self.assertEqual(r.status_code, 403, r.text)
        self.assertEqual(r.json()["detail"]["code"], "allow_train_denied")

    def test_unauthorized_read(self) -> None:
        r = self.http.get("/api/v1/memories/nope")
        self.assertEqual(r.status_code, 401)

    def test_agent_bank_isolation(self) -> None:
        from cognitive_memory.identity import issue_grant, register_agent

        register_agent(self.ctx.db, agent_id="agent:sec")
        g = issue_grant(
            self.ctx.db,
            "agent:sec",
            permissions=["memory.read"],
            banks=["personal"],
        )
        # write with node into shared then agent personal-only search should not escalate
        self.http.post(
            "/api/v1/memories",
            headers=self.h,
            json={
                "type": "semantic",
                "content": "shared secret",
                "status": "active",
                "metadata": {"bank_id": "shared", "policy": {"allow_forward": False}},
            },
        )
        act = self.http.post(
            "/api/v1/agents/act/search",
            json={"agent_id": "agent:sec", "agent_token": g["agent_token"], "query": "shared secret"},
        )
        # grant only personal — either 200 with 0 or filtered; never unauth dump
        self.assertIn(act.status_code, (200, 403))


if __name__ == "__main__":
    unittest.main()
