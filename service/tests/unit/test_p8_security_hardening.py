# -*- coding: utf-8 -*-
"""Task-book P8: inference leak, grant-cache revoke, delete cascade chain."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.identity import issue_grant, register_agent, require_agent_access, revoke_grant
from cognitive_memory.identity.grant_cache import DEFAULT_GRANT_CACHE, GrantCache
from cognitive_memory.identity.grants import AgentAccessError
from cognitive_memory.security.context import SecurityContext
from cognitive_memory.security.disclosure import (
    assert_no_existence_signal,
    claim_visible_to_principal,
    opaque_not_found,
    redact_claim_for_visibility,
    response_leaks_secret,
)
from cognitive_memory.storage.db import Database
from cognitive_memory.visibility.models import VisibilityDecision


class InferenceLeakTests(unittest.TestCase):
    def test_cross_bank_deny_hides_existence_and_text(self) -> None:
        secret = "我喜欢夜航星_SECRET_LEAK_PROBE"
        principal = SecurityContext(bank_id="personal", owner_id="u1")
        pack = claim_visible_to_principal(
            principal, claim_id="c_secret", bank_id="projects"
        )
        self.assertEqual(pack["decision"], VisibilityDecision.DENY.value)
        self.assertTrue(assert_no_existence_signal(pack))
        self.assertFalse(pack["existence_disclosed"])
        body = opaque_not_found(resource="claim")
        self.assertFalse(response_leaks_secret(body, secret))
        self.assertFalse(response_leaks_secret(pack, secret))

    def test_partial_redacts_verification_and_content(self) -> None:
        secret = "夜航星歌词全文"
        raw = {
            "id": "c1",
            "lifecycle": "verified",
            "verification_status": "verified",
            "normalized_text": secret,
            "ast": {"root": {"type": "Atom"}},
            "_evidence_refs": ["e1"],
        }
        redacted = redact_claim_for_visibility(
            raw,
            visible_fields=["claim_id", "lifecycle_status"],
            denied_fields=["verification_status", "content", "ast", "evidence_refs"],
        )
        self.assertNotIn("verification_status", redacted)
        self.assertNotIn("normalized_text", redacted)
        self.assertNotIn("ast", redacted)
        self.assertFalse(response_leaks_secret(redacted, secret))


class GrantCacheRevokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        DEFAULT_GRANT_CACHE.invalidate()

    def tearDown(self) -> None:
        DEFAULT_GRANT_CACHE.invalidate()
        self.db.close()
        self.tmp.cleanup()

    def test_revoke_drops_cache_immediately(self) -> None:
        register_agent(self.db, agent_id="agent:cache")
        g = issue_grant(
            self.db, "agent:cache", permissions=["memory.read"], banks=["personal"]
        )
        tok = g["agent_token"]
        require_agent_access(
            self.db, "agent:cache", tok, permission="memory.read", bank="personal"
        )
        self.assertIsNotNone(DEFAULT_GRANT_CACHE.get("agent:cache"))
        rev = revoke_grant(self.db, "agent:cache", reason="p8_test")
        self.assertTrue(rev["ok"])
        self.assertTrue(rev.get("cache_invalidated"))
        self.assertIsNone(DEFAULT_GRANT_CACHE.get("agent:cache"))
        with self.assertRaises(AgentAccessError) as cm:
            require_agent_access(
                self.db, "agent:cache", tok, permission="memory.read", bank="personal"
            )
        self.assertEqual(cm.exception.code, "revoked")

    def test_grant_cache_ttl_unit(self) -> None:
        cache = GrantCache(ttl_sec=60)
        cache.put("a", {"id": "g1", "token_hash": "x"})
        self.assertEqual(cache.size(), 1)
        self.assertEqual(cache.invalidate("a"), 1)
        self.assertEqual(cache.size(), 0)


class DeleteCascadeChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())
        self.claims = ClaimStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_forget_propagates_knowledge_strategy_experience(self) -> None:
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                content="我喜欢夜航星",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        prop = self.claims.propose_from_text("我喜欢夜航星", source_memory_id=mem.id)
        cid = prop["claim_id"]
        now = "2026-10-31T00:00:00Z"
        kid = "kn_p8_test"
        sid = "str_p8_test"
        eid = "exp_p8_test"
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO strategies(
                  id, name, description, scope_json, status, propensity_json,
                  version, created_at, updated_at
                ) VALUES (?, 's', '', '{}', 'active', '{}', 1, ?, ?)
                """,
                (sid, now, now),
            )
            conn.execute(
                """
                INSERT INTO knowledge_nodes(
                  id, kind, name, description, status, claim_ids_json,
                  schema_id, strategy_id, payload_json, scope_json, security_json,
                  validation_json, version, created_at, updated_at
                ) VALUES (?, 'fact', 'k', '', 'active', ?, NULL, ?, '{}', '{}', '{}',
                          '{}', 1, ?, ?)
                """,
                (kid, json.dumps([cid]), sid, now, now),
            )
            conn.execute(
                """
                INSERT INTO experiences(
                  id, bank_id, context_json, action_json, outcome_json,
                  memory_ids_json, claim_ids_json, reward, source, created_at
                ) VALUES (?, 'personal', '{}', '{}', '{}', ?, ?, NULL, 'test', ?)
                """,
                (eid, json.dumps([mem.id]), json.dumps([cid]), now),
            )

        out = self.svc.forget_memory(mem.id, hard=False)
        cascade = out.get("cascade") or {}
        self.assertTrue(cascade.get("ok"))
        self.assertEqual(
            cascade.get("chain"),
            [
                "memory",
                "evidence",
                "claim",
                "knowledge",
                "strategy",
                "experience",
                "tms",
                "cache",
            ],
        )
        self.assertIn(kid, cascade.get("knowledge_retired") or [])
        self.assertIn(sid, cascade.get("strategies_retired") or [])
        self.assertIn(eid, cascade.get("experiences_tombstoned") or [])
        claim = self.claims.get(cid, follow_redirect=False)
        self.assertEqual(claim["lifecycle"], "superseded")
        with self.db.transaction() as conn:
            kn = conn.execute(
                "SELECT status FROM knowledge_nodes WHERE id=?", (kid,)
            ).fetchone()
            st = conn.execute(
                "SELECT status FROM strategies WHERE id=?", (sid,)
            ).fetchone()
            ex = conn.execute(
                "SELECT outcome_json FROM experiences WHERE id=?", (eid,)
            ).fetchone()
        self.assertEqual(kn["status"], "retired")
        self.assertEqual(st["status"], "retired")
        self.assertTrue(json.loads(ex["outcome_json"]).get("tombstone"))


if __name__ == "__main__":
    unittest.main()
