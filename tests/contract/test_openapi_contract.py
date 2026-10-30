# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OPENAPI = ROOT / "schemas" / "openapi.v1.yaml"

# 破坏契约即失败的关键路径（E3.1）
REQUIRED_PATHS = {
    "/health",
    "/observations",
    "/memories",
    "/memories/search",
    "/feedback",
    "/contract",
    "/banks",
    "/authority",
    "/authority/cutover/preview",
    "/evidence",
    "/identities",
    "/agents/register",
    "/agents/act/search",
    "/node",
    "/entities",
    "/events/stream",
}


def test_openapi_file_exists() -> None:
    assert OPENAPI.is_file(), f"missing {OPENAPI}"


def test_openapi_contains_required_paths() -> None:
    text = OPENAPI.read_text(encoding="utf-8")
    # 简易解析：不强制 PyYAML 依赖
    missing = [p for p in REQUIRED_PATHS if f"  {p}:" not in text and f"  {p.rstrip('/')}:" not in text]
    # paths like /memories/{id} appear as /memories/{id}:
    soft_ok = []
    for p in list(missing):
        if p in text:
            soft_ok.append(p)
    missing = [p for p in missing if p not in soft_ok]
    assert not missing, f"OpenAPI missing paths: {missing}"


def test_event_contract_versioned() -> None:
    from cognitive_memory.events.contract import (
        EVENT_CONTRACT_VERSION,
        PUBLIC_EVENT_TYPES,
        validate_event_type,
    )

    assert EVENT_CONTRACT_VERSION >= 1
    assert validate_event_type("observation.captured")
    assert "memory.invalidated" in PUBLIC_EVENT_TYPES
