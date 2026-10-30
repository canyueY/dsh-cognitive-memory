# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest

from cognitive_memory.bootstrap import build_context
from cognitive_memory.governance.authority import AuthorityState, transition_authority
from cognitive_memory.governance.cutover import execute_cutover, preview_cutover


class CutoverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="cutover-token")

    def tearDown(self) -> None:
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_preview_and_confirm_required(self) -> None:
        prev = preview_cutover(self.ctx.service)
        self.assertTrue(prev["ok"])
        self.assertIn("checklist", prev)
        denied = execute_cutover(self.ctx.service, confirm=False)
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"], "confirm_required")

    def test_path_external_to_primary(self) -> None:
        # default is mnemosyne_primary → importing → external_authoritative
        transition_authority(
            self.ctx.db, AuthorityState.IMPORTING, reason="to-import", actor="test"
        )
        transition_authority(
            self.ctx.db,
            AuthorityState.EXTERNAL_AUTHORITATIVE,
            reason="to-external",
            actor="test",
        )
        out = execute_cutover(
            self.ctx.service,
            target="mnemosyne_primary",
            confirm=True,
            reason="suite",
        )
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["authority"]["state"], "mnemosyne_primary")
        self.assertGreaterEqual(len(out["steps"]), 2)

    def test_dual_requires_flag(self) -> None:
        out = execute_cutover(
            self.ctx.service,
            target="dual_sync",
            confirm=True,
            allow_dual=False,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "dual_requires_explicit")
        ok = execute_cutover(
            self.ctx.service,
            target="dual_sync",
            confirm=True,
            allow_dual=True,
            reason="explicit dual",
        )
        self.assertTrue(ok["ok"], ok)
        self.assertEqual(ok["authority"]["state"], "dual_sync")


if __name__ == "__main__":
    unittest.main()
