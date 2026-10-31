# -*- coding: utf-8 -*-
"""Windows / 跨平台数据目录。"""

from __future__ import annotations

import os
from pathlib import Path


def default_data_root() -> Path:
    override = (
        os.environ.get("DSH_MNEMOSYNE_DATA_DIR", "").strip()
        or os.environ.get("DSH_MEMORY_DATA_DIR", "").strip()
    )
    if override:
        return Path(override).expanduser().resolve()
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if local:
        root = Path(local) / "DSH"
        next_dir = root / "mnemosyne"
        legacy = root / "cognitive-memory"
        if not next_dir.exists() and (legacy / "data" / "memory.db").exists():
            return legacy
        return next_dir
    return Path.home() / ".local" / "share" / "DSH" / "mnemosyne"


def ensure_layout(root: Path | None = None) -> dict[str, Path]:
    base = (root or default_data_root()).resolve()
    paths = {
        "root": base,
        "runtime": base / "runtime",
        "data": base / "data",
        "logs": base / "logs",
        "cache": base / "cache",
        "db": base / "data" / "memory.db",
        "service_json": base / "runtime" / "service.json",
        "service_lock": base / "runtime" / "service.lock",
    }
    for key in ("runtime", "data", "logs", "cache"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths
