# -*- coding: utf-8 -*-
"""DSH / 大肥鱼 Host Adapter（薄封装）— 仅经 HTTP/SDK 访问 Node。

场景 A 验收锚点：宿主负责编排；记忆权威在 Mnemosyne Node。
禁止：直连 SQLite / 导入 storage.db.Database / 直写 memory.db。
"""

from __future__ import annotations

from typing import Any

from cognitive_memory.sdk import MnemosyneClient

# 静态检查与契约测试共用的禁导名单
FORBIDDEN_IMPORT_PREFIXES: tuple[str, ...] = (
    "sqlite3",
    "cognitive_memory.storage.db",
    "cognitive_memory.storage.migrations",
    "cognitive_memory.core.service",
)


class DshHttpAdapter:
    """把 DSH 风格调用映射到 MnemosyneClient（无本地库）。"""

    def __init__(self, client: MnemosyneClient):
        self._client = client

    @classmethod
    def connect(cls, base_url: str, token: str, *, session: Any = None) -> "DshHttpAdapter":
        return cls(MnemosyneClient(base_url, token, session=session))

    def health(self) -> dict[str, Any]:
        return self._client.health()

    def contract(self) -> dict[str, Any]:
        return self._client.contract()

    def observe_dialog(
        self,
        content: str,
        *,
        producer: str = "dsh-host",
        agent_id: str = "agent:dsh",
        source_kind: str = "dialog",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._client.observe(
            {
                "source_kind": source_kind,
                "content": content,
                "producer": producer,
                "agent_id": agent_id,
                "metadata": dict(metadata or {}),
            }
        )

    def search(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        return self._client.search(query, limit=limit)

    def propose_from_host(
        self,
        content: str,
        *,
        source_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._client.propose(
            {
                "type": "semantic",
                "content": content,
                "status": "candidate",
                "source_ids": list(source_ids or []),
                "metadata": dict(metadata or {"host": "dsh"}),
            }
        )


def assert_no_forbidden_imports(module_globals: dict[str, Any]) -> None:
    """运行时粗检：模块 globals 不应持有禁导对象名。"""
    for name in ("sqlite3", "Database", "MemoryService"):
        if name in module_globals and module_globals[name] is not None:
            # allow typing-only None placeholders
            obj = module_globals[name]
            mod = getattr(obj, "__module__", "") or ""
            if name == "sqlite3" or mod.startswith("cognitive_memory.storage") or mod.startswith(
                "cognitive_memory.core"
            ):
                raise RuntimeError(f"DSH adapter must not bind {name} from {mod}")
