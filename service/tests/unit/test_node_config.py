# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from cognitive_memory.node_cli import main as node_main
from cognitive_memory.node_config import load_node_config, validate_config, write_default_config


def test_write_and_load_json(tmp_path: Path) -> None:
    path = write_default_config(tmp_path / "node.config.json", data_dir=str(tmp_path))
    cfg = load_node_config(config_path=path, data_dir_hint=str(tmp_path))
    assert cfg.node_id == "local-node"
    assert cfg.host == "127.0.0.1"
    assert Path(cfg.data_dir) == tmp_path.resolve()


def test_remote_access_guard() -> None:
    raw = {
        "node": {"id": "x", "mode": "standalone"},
        "runtime": {"host": "0.0.0.0", "port": 8765},
        "storage": {"provider": "sqlite", "data_dir": ""},
        "security": {"remote_access": "disabled", "token_env": "DSH_MEMORY_TOKEN"},
        "components": {"profiles": ["core-default"]},
    }
    errs = validate_config(raw)
    assert any("remote_access" in e for e in errs)


def test_cli_config_init_show(tmp_path: Path, capsys) -> None:
    rc = node_main(["--data-dir", str(tmp_path), "config", "init"])
    assert rc == 0
    assert (tmp_path / "node.config.json").is_file()
    capsys.readouterr()
    rc = node_main(["--data-dir", str(tmp_path), "config", "validate"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["ok"] is True


def test_cli_backup_roundtrip_via_node(tmp_path: Path) -> None:
    assert node_main(["--data-dir", str(tmp_path), "doctor"]) == 0
    bak = tmp_path / "backups"
    assert node_main(["--data-dir", str(tmp_path), "backup", "-o", str(bak)]) == 0
    files = list(bak.glob("memory-*.db"))
    assert files
    rst = tmp_path / "restored"
    rst.mkdir()
    assert node_main(["--data-dir", str(rst), "restore", str(files[0]), "--force"]) == 0
