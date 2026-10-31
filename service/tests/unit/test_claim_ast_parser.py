# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from cognitive_memory.claims.ast import AST_VERSION, Atom, ClaimAST, Negation, Unresolved
from cognitive_memory.claims.normalize import normalize_ast, normalized_hash
from cognitive_memory.claims.parser import parse_memory_text


class ClaimAstParserTests(unittest.TestCase):
    def test_preference_atom(self) -> None:
        r = parse_memory_text("我喜欢 YOASOBI")
        self.assertEqual(r.status, "parsed")
        self.assertEqual(r.ast.root.kind, "atom")
        assert isinstance(r.ast.root, Atom)
        self.assertEqual(r.ast.root.modality, "preference")
        self.assertEqual(r.ast.ast_version, AST_VERSION)

    def test_music_inference_preference(self) -> None:
        r = parse_memory_text(
            "[music:inference] 用户可能偏好艺术家「LiSA」的作品（基于 4 首收藏）",
            metadata={"domain": "music", "data_kind": "preference_signal"},
        )
        self.assertEqual(r.status, "parsed")
        assert isinstance(r.ast.root, Atom)
        self.assertEqual(r.ast.root.arguments[0], "LiSA")
        self.assertEqual(r.ast.scope.get("epistemic"), "inferred_signal")

    def test_music_saved_behavior(self) -> None:
        r = parse_memory_text(
            "[music:observed] 用户在音乐应用中收藏了歌曲《旅の終わり》(550138197)",
            metadata={"domain": "music"},
        )
        self.assertEqual(r.status, "parsed")
        assert isinstance(r.ast.root, Atom)
        self.assertEqual(r.ast.root.predicate, "收藏")

    def test_negation_preference(self) -> None:
        r = parse_memory_text("我不喜欢香菜")
        self.assertIn(r.status, ("parsed", "needs_review"))
        self.assertEqual(r.ast.root.kind, "negation")
        assert isinstance(r.ast.root, Negation)

    def test_conditional(self) -> None:
        r = parse_memory_text("如果下雨就带伞")
        self.assertEqual(r.ast.root.kind, "conditional")

    def test_unresolved_long_noise(self) -> None:
        r = parse_memory_text("嗯……那个……随便聊聊天气吧哈哈哈" * 3)
        self.assertEqual(r.status, "unresolved")
        self.assertTrue(r.ast.is_unresolved())

    def test_normalize_deterministic(self) -> None:
        a = ClaimAST(root=Atom(subject="用户", predicate="喜欢", arguments=["YOASOBI"], modality="preference"))
        b = ClaimAST(root=Atom(subject="用户", predicate="喜爱", arguments=["yoasobi"], modality="preference"))
        self.assertEqual(normalize_ast(a)["root"]["predicate"], "likes")
        self.assertEqual(normalized_hash(a), normalized_hash(b))

    def test_different_args_not_same_hash(self) -> None:
        a = ClaimAST(root=Atom(subject="用户", predicate="喜欢", arguments=["A"]))
        b = ClaimAST(root=Atom(subject="用户", predicate="喜欢", arguments=["B"]))
        self.assertNotEqual(normalized_hash(a), normalized_hash(b))

    def test_unresolved_serializable(self) -> None:
        u = ClaimAST(root=Unresolved(raw_text="x", missing_fields=["subject"], reason_codes=["no_rule_match"]))
        dump = u.model_dump(mode="json")
        self.assertEqual(dump["root"]["kind"], "unresolved")


if __name__ == "__main__":
    unittest.main()
