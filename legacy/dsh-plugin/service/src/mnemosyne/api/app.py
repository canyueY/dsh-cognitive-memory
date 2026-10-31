# -*- coding: utf-8 -*-
"""FastAPI REST：统一前缀 /api/v1，全部委托 MemoryService。"""

from __future__ import annotations

import secrets
import uuid
from typing import Any, Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from mnemosyne.core.service import ConflictError, MemoryService, NotFoundError
from mnemosyne.domain.models import (
    ContextBuildIn,
    FeedbackIn,
    MemoryProposeIn,
    MemoryUpdateIn,
    ObservationIn,
    SearchQuery,
    TaskCreateIn,
)


def create_app(
    service: MemoryService,
    *,
    access_token: str,
    api_prefix: str = "/api/v1",
) -> FastAPI:
    app = FastAPI(title="Mnemosyne", version="0.1.0")
    app.state.service = service
    app.state.access_token = access_token

    def require_token(
        authorization: str | None = Header(default=None),
        x_memory_token: str | None = Header(default=None),
    ) -> None:
        token = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        elif x_memory_token:
            token = x_memory_token.strip()
        expected = app.state.access_token
        if not expected or not token or not secrets.compare_digest(token, expected):
            raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "invalid token"})

    @app.middleware("http")
    async def add_request_id(request: Request, call_next: Callable):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(NotFoundError)
    async def _nf(_req: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"code": exc.code, "message": str(exc)})

    @app.exception_handler(ConflictError)
    async def _cf(_req: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"code": exc.code, "message": str(exc)})

    pref = api_prefix.rstrip("/") or "/api/v1"

    @app.get(f"{pref}/health")
    def health(_: None = Depends(require_token)) -> dict[str, Any]:
        return service.health()

    # 启动握手可无 token 探测进程存活（仅返回 ok，不含业务数据）
    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"ok": "true"}

    @app.post(f"{pref}/memories/search")
    def search(body: SearchQuery, _: None = Depends(require_token)) -> dict[str, Any]:
        rows = service.search(body)
        return {"items": [m.model_dump() for m in rows], "count": len(rows)}

    @app.get(f"{pref}/memories/{{memory_id}}")
    def get_memory(
        memory_id: str,
        include_evidence: bool = False,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        return service.get_memory(memory_id, include_evidence=include_evidence)

    @app.post(f"{pref}/memories")
    def propose(body: MemoryProposeIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.propose_memory(body).model_dump()

    @app.patch(f"{pref}/memories/{{memory_id}}")
    def update(memory_id: str, body: MemoryUpdateIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.update_memory(memory_id, body).model_dump()

    @app.delete(f"{pref}/memories/{{memory_id}}")
    def forget(memory_id: str, hard: bool = False, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.forget_memory(memory_id, hard=hard)

    @app.post(f"{pref}/observations")
    def observations(body: ObservationIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.capture_observation(body).model_dump()

    @app.post(f"{pref}/feedback")
    def feedback(body: FeedbackIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.feedback(body)

    @app.post(f"{pref}/contexts/build")
    def contexts(body: ContextBuildIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.build_context(body).model_dump()

    @app.post(f"{pref}/tasks")
    def create_task(body: TaskCreateIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.create_task(body).model_dump()

    @app.get(f"{pref}/tasks/{{task_id}}")
    def get_task(task_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.get_task(task_id).model_dump()

    return app
