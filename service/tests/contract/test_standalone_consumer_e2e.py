# -*- coding: utf-8 -*-
"""非 DSH 独立 Consumer 契约 E2E：仅 SDK + HTTP，不依赖 Murasame / 桌宠宿主。

覆盖：鉴权、契约、观察/提案/检索/反馈、多 Agent grant 隔离检索、Cutover preview。
"""

from __future__ import annotations

import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

from cognitive_memory.bootstrap import build_context
from cognitive_memory.sdk import MnemosyneClient, MnemosyneClientError


class StandaloneConsumerE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        # 契约：本文件导入图不得拉入 DSH 宿主
        banned = [n for n in sys.modules if n == "Murasame" or n.startswith("Murasame.")]
        self.assertEqual(banned, [], f"DSH host modules leaked into contract E2E: {banned}")

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="standalone-e2e-token")
        self.http = TestClient(self.ctx.app)
        self.client = MnemosyneClient(
            "http://test",
            "standalone-e2e-token",
            session=self.http,
        )
        self.headers = {"Authorization": "Bearer standalone-e2e-token"}

    def tearDown(self) -> None:
        self.client.close()
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_sdk_full_loop_without_dsh(self) -> None:
        contract = self.client.contract()
        self.assertFalse(contract.get("adapter_may_bypass_service"))
        self.assertIn("sdk", contract)

        health = self.client.health()
        self.assertTrue(health.get("ok"))

        banks = self.http.get("/api/v1/banks", headers=self.headers)
        self.assertEqual(banks.status_code, 200)
        self.assertGreaterEqual(banks.json().get("count", 0), 1)

        obs = self.client.observe(
            {
                "source_kind": "user_statement",
                "content": "独立 Consumer：偏好雨声白噪声",
                "producer": "standalone-consumer",
                "agent_id": "agent:external-consumer",
            }
        )
        self.assertTrue(obs.get("id"))
        mem = self.client.propose(
            {
                "type": "semantic",
                "content": "用户偏好雨声白噪声",
                "status": "active",
                "source_ids": [obs["id"]],
                "metadata": {"consumer": "standalone"},
            }
        )
        found = self.client.search("雨声白噪声")
        self.assertGreaterEqual(found.get("count", 0), 1)
        fb = self.client.feedback(mem["id"], useful=True, note="standalone-ok")
        self.assertTrue(fb.get("ok"))

        auth = self.http.get("/api/v1/authority", headers=self.headers)
        self.assertEqual(auth.status_code, 200)
        preview = self.http.get("/api/v1/authority/cutover/preview", headers=self.headers)
        self.assertEqual(preview.status_code, 200)
        body = preview.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("checklist", body)

    def test_agent_token_isolation_via_http(self) -> None:
        reg = self.http.post(
            "/api/v1/agents/register",
            headers=self.headers,
            json={"agent_id": "agent:ext-a", "display_name": "Ext A"},
        )
        self.assertEqual(reg.status_code, 200)
        self.assertFalse(reg.json().get("authorized"))

        grant = self.http.post(
            "/api/v1/agents/agent:ext-a/grants",
            headers=self.headers,
            json={
                "permissions": ["memory.read"],
                "banks": ["personal"],
                "consent": {"user_consent": True},
            },
        )
        self.assertEqual(grant.status_code, 200)
        token = grant.json().get("agent_token")
        self.assertTrue(token)

        # seed a memory as node
        obs = self.client.observe(
            {
                "source_kind": "system",
                "content": "grant-isolation marker alpha",
                "producer": "e2e",
            }
        )
        self.client.propose(
            {
                "type": "semantic",
                "content": "grant-isolation marker alpha",
                "status": "active",
                "source_ids": [obs["id"]],
            }
        )

        ok = self.http.post(
            "/api/v1/agents/act/search",
            json={
                "agent_id": "agent:ext-a",
                "agent_token": token,
                "bank": "personal",
                "query": "grant-isolation",
            },
        )
        self.assertEqual(ok.status_code, 200)

        denied = self.http.post(
            "/api/v1/agents/act/search",
            json={
                "agent_id": "agent:ext-a",
                "agent_token": token,
                "bank": "shared",
                "query": "grant-isolation",
            },
        )
        self.assertIn(denied.status_code, (401, 403, 400))

        # wrong token
        with self.assertRaises(MnemosyneClientError):
            MnemosyneClient("http://test", "nope", session=self.http).health()


if __name__ == "__main__":
    unittest.main()
