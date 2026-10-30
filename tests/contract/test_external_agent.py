# -*- coding: utf-8 -*-
"""Phase 3 退出：非 DSH 测试 Agent（SDK）完成认证/观察/检索/反馈/撤销。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cognitive_memory.bootstrap import build_context
from cognitive_memory.components.contract import (
    ComponentManifest,
    ComponentRegistry,
    UnauthorizedComponentError,
)
from cognitive_memory.sdk import MnemosyneClient, MnemosyneClientError


class ExternalAgentInteropTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="test-token-phase3")
        self.http = TestClient(self.ctx.app)
        self.client = MnemosyneClient(
            "http://test",
            "test-token-phase3",
            session=self.http,
        )

    def tearDown(self) -> None:
        self.client.close()
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_unauthorized_rejected(self) -> None:
        bad = MnemosyneClient("http://test", "wrong", session=self.http)
        with self.assertRaises(MnemosyneClientError) as cm:
            bad.health()
        self.assertEqual(cm.exception.status_code, 401)

    def test_standalone_agent_loop(self) -> None:
        h = self.client.health()
        self.assertTrue(h.get("ok"))
        obs = self.client.observe(
            {
                "source_kind": "user_statement",
                "content": "外部 Agent：我喜欢夜航星",
                "producer": "external-agent-a",
                "agent_id": "agent:standalone",
            }
        )
        self.assertTrue(obs.get("id"))
        mem = self.client.propose(
            {
                "type": "semantic",
                "content": "用户喜欢夜航星",
                "status": "active",
                "source_ids": [obs["id"]],
                "metadata": {"epistemic": "fact", "from_user": True},
            }
        )
        self.assertEqual(mem.get("status"), "active")
        found = self.client.search("夜航星")
        self.assertGreaterEqual(found.get("count", 0), 1)
        fb = self.client.feedback(mem["id"], useful=True, note="ok")
        self.assertTrue(fb.get("ok"))
        revoked = self.client.forget(mem["id"], hard=False)
        self.assertEqual(revoked.get("status"), "invalidated")
        contract = self.client.contract()
        self.assertFalse(contract.get("adapter_may_bypass_service"))
        self.assertEqual(contract.get("sdk"), "cognitive_memory.sdk.MnemosyneClient")

    def test_component_register_not_authorize(self) -> None:
        reg = ComponentRegistry()
        m = ComponentManifest(
            component_id="ext.agent.a",
            name="External Agent A",
            permissions=["memory.read", "memory.write"],
            banks=["personal"],
        )
        reg_out = reg.register(m)
        self.assertTrue(reg_out["registered"])
        self.assertFalse(reg_out["authorized"])
        with self.assertRaises(UnauthorizedComponentError):
            reg.require("ext.agent.a", "memory.read")
        reg.authorize("ext.agent.a")
        reg.require("ext.agent.a", "memory.read", bank="personal")
        with self.assertRaises(UnauthorizedComponentError):
            reg.require("ext.agent.a", "memory.read", bank="shared")


if __name__ == "__main__":
    unittest.main()
