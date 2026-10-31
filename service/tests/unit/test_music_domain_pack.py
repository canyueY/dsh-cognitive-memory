# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import (
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    SearchQuery,
)
from cognitive_memory.domains.pack import load_domain_pack
from cognitive_memory.domains.registrar import register_domain_pack
from cognitive_memory.domains.retrieval import apply_domain_gate, detect_music_intent
from cognitive_memory.events.bus import EventBus
from cognitive_memory.storage.db import Database

_PACK = Path(__file__).resolve().parents[1] / "fixtures" / "music_domain_pack.v1.json"

def _pack_path() -> Path:
    return _PACK


class MusicDomainPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_load_and_register_idempotent(self) -> None:
        path = _pack_path()
        self.assertTrue(path.is_file(), f"missing pack: {path}")
        pack = load_domain_pack(path)
        self.assertEqual(pack.domain_id, "music")
        first = register_domain_pack(self.svc, pack, actor="test")
        self.assertTrue(first["ok"], first)
        self.assertIn("domain:music", first["created"])
        self.assertTrue(self.svc.get_cognitive_schema("domain:music"))
        self.assertTrue(self.svc.get_cognitive_schema("concept:music.track"))
        second = register_domain_pack(self.svc, pack, actor="test")
        self.assertTrue(second["ok"], second)
        self.assertEqual(second["created"], [])
        self.assertIn("domain:music", second["reused"])

    def test_domain_gate_excludes_music_on_unrelated_query(self) -> None:
        class M:
            def __init__(self, mid: str, domain: str = "") -> None:
                self.id = mid
                self.metadata = {"domain": domain} if domain else {}

        items = [M("a"), M("b", "music"), M("c", "code")]
        gated = apply_domain_gate(items, domain=None, query="帮我检查这段 Python 代码")
        ids = [x.id for x in gated]
        self.assertIn("a", ids)
        self.assertNotIn("b", ids)

    def test_domain_gate_keeps_music_on_intent(self) -> None:
        self.assertTrue(detect_music_intent("播放每日推荐里的歌"))
        class M:
            def __init__(self, mid: str, domain: str = "") -> None:
                self.id = mid
                self.metadata = {"domain": domain} if domain else {}

        items = [M("a"), M("b", "music")]
        gated = apply_domain_gate(items, domain=None, query="推荐几首晚上听的歌")
        self.assertEqual({x.id for x in gated}, {"a", "b"})

    def test_search_applies_domain_gate(self) -> None:
        self.svc.propose_memory(
            MemoryProposeIn(
                content="用户收藏了歌曲 At Least I Had Fun",
                type=MemoryType.EPISODIC,
                status=MemoryStatus.ACTIVE,
                metadata={"domain": "music", "data_kind": "user_action"},
            )
        )
        self.svc.propose_memory(
            MemoryProposeIn(
                content="用户偏好深色主题",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                metadata={"domain": ""},
            )
        )
        unrelated = self.svc.search(SearchQuery(query="主题", limit=10, domain=None))
        contents = [m.content for m in unrelated]
        self.assertTrue(any("深色主题" in c for c in contents))
        self.assertFalse(any("At Least I Had Fun" in c for c in contents))
        music = self.svc.search(SearchQuery(query="歌曲", limit=10, domain="music"))
        mcontents = [m.content for m in music]
        self.assertTrue(any("At Least I Had Fun" in c for c in mcontents))

    def test_music_instance_relations_saves_not_auto_likes(self) -> None:
        from cognitive_memory.domain.models import RelationKind

        user = self.svc.propose_memory(
            MemoryProposeIn(
                content="user:self anchor",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                metadata={"domain": "music", "role": "user_anchor"},
            )
        )
        track = self.svc.propose_memory(
            MemoryProposeIn(
                content="[music:observed] saved track",
                type=MemoryType.EPISODIC,
                status=MemoryStatus.CANDIDATE,
                metadata={"domain": "music", "data_kind": "user_action", "action": "saved"},
            )
        )
        link = self.svc.link_memories(
            from_id=user.id,
            to_id=track.id,
            relation=RelationKind.SAVES.value,
            note="observed save",
            metadata={"domain": "music", "status": "observed", "not": "likes"},
        )
        self.assertTrue(link.get("ok", True) or link.get("from_id"))
        rels = self.svc.list_relations(track.id)
        kinds = {r.get("relation") or getattr(r, "relation", "") for r in rels}
        self.assertIn("saves", kinds)
        self.assertNotIn("likes", kinds)
        # likes is allowed by schema but must not be written by acquisition auto-path
        self.assertIn(RelationKind.LIKES.value, self.svc._RELATION_TYPES)
        self.assertIn(RelationKind.LISTENED_TO.value, self.svc._RELATION_TYPES)


if __name__ == "__main__":
    unittest.main()
