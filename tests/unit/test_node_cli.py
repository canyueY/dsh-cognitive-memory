# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from cognitive_memory.node_cli import main as node_main


def test_doctor_no_dsh(tmp_path: Path, capsys) -> None:
    rc = node_main(["--data-dir", str(tmp_path), "doctor"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["ok"] is True
    assert payload["host_dependency"] == "none_required"
    ids = {c["id"] for c in payload["checks"]}
    assert "imports" in ids
    assert "local_health" in ids
    assert "dsh_absent" in ids


def test_status_not_running(tmp_path: Path, capsys) -> None:
    rc = node_main(["--data-dir", str(tmp_path), "status"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["running"] is False
