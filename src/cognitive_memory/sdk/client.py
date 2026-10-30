# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Protocol


class MnemosyneClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class _Session(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...

    def close(self) -> None: ...  # optional


class MnemosyneClient:
    """REST 薄封装：认证 → 观察 → 检索 → 反馈 → 失效。不依赖 DSH。

    ``session`` 可注入 FastAPI ``TestClient`` 或 ``httpx.Client``。
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 30.0,
        api_prefix: str = "/api/v1",
        session: Any | None = None,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token
        self.api_prefix = api_prefix.rstrip("/") or "/api/v1"
        self._owns_session = session is None
        if session is not None:
            self._client = session
        else:
            import httpx

            self._client = httpx.Client(
                base_url=self.base_url or "http://127.0.0.1",
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )

    def close(self) -> None:
        if self._owns_session:
            close = getattr(self._client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    def __enter__(self) -> "MnemosyneClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _url(self, path: str) -> str:
        # TestClient 通常要绝对 path；httpx Client 用相对 path
        return f"{self.api_prefix}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("Authorization", f"Bearer {self.token}")
        headers.setdefault("Content-Type", "application/json")
        url = self._url(path)
        resp = self._client.request(method, url, headers=headers, **kwargs)
        status = getattr(resp, "status_code", 0)
        if status >= 400:
            try:
                body = resp.json()
            except Exception:
                body = getattr(resp, "text", None)
            raise MnemosyneClientError(
                f"{method} {path} -> {status}",
                status_code=status,
                body=body,
            )
        if status == 204:
            return {}
        content = getattr(resp, "content", None)
        if content is not None and not content:
            return {}
        return resp.json()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def observe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/observations", json=payload)

    def propose(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/memories", json=payload)

    def search(self, query: str, **extra: Any) -> dict[str, Any]:
        body = {"query": query, **extra}
        return self._request("POST", "/memories/search", json=body)

    def feedback(
        self,
        memory_id: str,
        *,
        useful: bool | None = None,
        incorrect: bool | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/feedback",
            json={
                "memory_id": memory_id,
                "useful": useful,
                "incorrect": incorrect,
                "note": note,
                "producer": "mnemosyne-sdk",
            },
        )

    def forget(self, memory_id: str, *, hard: bool = False) -> dict[str, Any]:
        return self._request(
            "DELETE",
            f"/memories/{memory_id}",
            params={"hard": hard},
        )

    def contract(self) -> dict[str, Any]:
        return self._request("GET", "/contract")
