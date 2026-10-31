# -*- coding: utf-8 -*-
"""Compatibility Gateway（E4.6）：只读 / 单向；双向默认关闭。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CompatMode(str, Enum):
    DISABLED = "disabled"
    READ_ONLY = "read_only"  # 旧库权威，Mnemosyne 只读窥视
    ONE_WAY = "one_way"  # 旧 → Mnemosyne 单向
    DUAL = "dual"  # 显式启用才允许


@dataclass
class CompatGateway:
    mode: CompatMode = CompatMode.READ_ONLY
    dual_enabled: bool = False  # 硬默认关

    def allow_read_legacy(self) -> bool:
        return self.mode in (
            CompatMode.READ_ONLY,
            CompatMode.ONE_WAY,
            CompatMode.DUAL,
        )

    def allow_write_mnemosyne_from_legacy(self) -> bool:
        return self.mode in (CompatMode.ONE_WAY, CompatMode.DUAL)

    def allow_write_legacy_from_mnemosyne(self) -> bool:
        return self.mode == CompatMode.DUAL and self.dual_enabled

    def set_mode(self, mode: str | CompatMode, *, allow_dual: bool = False) -> dict[str, Any]:
        m = mode if isinstance(mode, CompatMode) else CompatMode(str(mode).strip().lower())
        if m == CompatMode.DUAL and not allow_dual:
            raise PermissionError("dual mode requires allow_dual=true")
        self.mode = m
        if m == CompatMode.DUAL:
            self.dual_enabled = True
        elif m != CompatMode.DUAL:
            self.dual_enabled = False
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "dual_enabled": self.dual_enabled,
            "allow_read_legacy": self.allow_read_legacy(),
            "allow_write_mnemosyne_from_legacy": self.allow_write_mnemosyne_from_legacy(),
            "allow_write_legacy_from_mnemosyne": self.allow_write_legacy_from_mnemosyne(),
            "dual_default_forbidden": True,
        }


# 进程级默认网关（单测可重置）
GATEWAY = CompatGateway()
