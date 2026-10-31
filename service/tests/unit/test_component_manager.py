# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.components.contract import UnauthorizedComponentError
from cognitive_memory.components.manager import ComponentManager
from cognitive_memory.components.manifest import load_manifest, parse_manifest
from cognitive_memory.components.profiles import get_profile, list_profiles
from cognitive_memory.components.resolver import resolve_dependencies


def _write_component(root: Path, *, cid: str, requires: list[str] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "component_id": cid,
        "name": cid,
        "version": "1.0.0",
        "type": "extension",
        "provider": "local",
        "interfaces": {
            "provides": [f"{cid}.capability"],
            "requires": list(requires or []),
        },
        "protocols": ["mnemosyne-component-v1"],
        "permissions": ["memory.read"],
        "banks": ["personal"],
        "compatibility": {"mnemosyne": ">=2.0.0"},
        "lifecycle": {"health_check": True},
        "extra_unknown": {"kept": True},
    }
    path = root / "mnemosyne.component.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "README.md").write_text(f"# {cid}\n", encoding="utf-8")
    return root


class ComponentManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.data = Path(self.tmp.name) / "node-data"
        self.data.mkdir(parents=True, exist_ok=True)
        self.mgr = ComponentManager(self.data)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_parse_keeps_unknown_extensions(self) -> None:
        src = _write_component(Path(self.tmp.name) / "pkg-a", cid="demo.echo")
        m = load_manifest(src)
        self.assertEqual(m.component_id, "demo.echo")
        self.assertIn("extensions", m.metadata)
        self.assertEqual(m.metadata["extensions"].get("extra_unknown"), {"kept": True})

    def test_install_does_not_authorize(self) -> None:
        src = _write_component(Path(self.tmp.name) / "pkg-b", cid="demo.reader")
        out = self.mgr.install(src)
        self.assertTrue(out["ok"])
        self.assertFalse(out["component"]["authorized"])
        self.assertFalse(self.mgr.registry.is_authorized("demo.reader"))
        with self.assertRaises(UnauthorizedComponentError):
            self.mgr.registry.require("demo.reader", "memory.read")

    def test_lifecycle_enable_health_disable_remove(self) -> None:
        src = _write_component(Path(self.tmp.name) / "pkg-c", cid="demo.lifecycle")
        self.assertTrue(self.mgr.install(src)["ok"])
        auth = self.mgr.authorize("demo.lifecycle")
        self.assertTrue(auth["ok"])
        en = self.mgr.enable("demo.lifecycle", require_auth=True)
        self.assertTrue(en["ok"])
        self.assertEqual(en["component"]["state"], "enabled")
        self.assertTrue(en["health"]["ok"])
        dis = self.mgr.disable("demo.lifecycle")
        self.assertEqual(dis["component"]["state"], "disabled")
        rm = self.mgr.remove("demo.lifecycle")
        self.assertTrue(rm["ok"])
        self.assertEqual(rm["component"]["state"], "removed")
        self.assertEqual(self.mgr.get("demo.lifecycle")["state"], "removed")

    def test_resolve_missing_requires(self) -> None:
        src = _write_component(
            Path(self.tmp.name) / "pkg-d",
            cid="demo.needs",
            requires=["missing.iface"],
        )
        out = self.mgr.install(src)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "unresolved_requires")

    def test_resolve_with_peer(self) -> None:
        a = _write_component(Path(self.tmp.name) / "pkg-e", cid="demo.provider")
        self.assertTrue(self.mgr.install(a)["ok"])
        # peer requires demo.provider.capability
        b = _write_component(
            Path(self.tmp.name) / "pkg-f",
            cid="demo.consumer",
            requires=["demo.provider.capability"],
        )
        out = self.mgr.install(b)
        self.assertTrue(out["ok"], out)

    def test_failed_install_invalid_manifest(self) -> None:
        src = Path(self.tmp.name) / "broken"
        src.mkdir()
        (src / "mnemosyne.component.json").write_text(
            json.dumps({"component_id": "x", "type": "nope"}),
            encoding="utf-8",
        )
        out = self.mgr.install(src)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "invalid_type")

    def test_profiles(self) -> None:
        ids = {p["id"] for p in list_profiles()}
        self.assertIn("standalone", ids)
        self.assertIn("dsh", ids)
        self.assertIsNotNone(get_profile("standalone"))

    def test_builtin_provides_satisfy(self) -> None:
        m = parse_manifest(
            {
                "component_id": "demo.builtin",
                "type": "adapter",
                "interfaces": {"provides": [], "requires": ["memory.read"]},
                "permissions": [],
            }
        )
        rr = resolve_dependencies(m, installed=[], builtin_provides=["memory.read"])
        self.assertTrue(rr.ok)


if __name__ == "__main__":
    unittest.main()
