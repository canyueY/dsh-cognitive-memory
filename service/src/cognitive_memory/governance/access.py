# -*- coding: utf-8 -*-
"""统一访问执法：Node Bearer（运维超管）或 Agent grant（范围权限）。

字段 ≠ 执法：memory CRUD 必须经本模块；硬删另受 capability_gate 约束。
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Literal

from fastapi import Header, HTTPException, Request

from cognitive_memory.governance.capability_gate import CapabilityLockedError, require_capability
from cognitive_memory.identity.grants import AgentAccessError, require_agent_access

ActorKind = Literal["node", "agent"]


@dataclass
class AccessContext:
    kind: ActorKind
    actor_id: str
    banks: list[str] | None = None
    permissions: list[str] | None = None
    grant_id: str | None = None

    @property
    def is_node_admin(self) -> bool:
        return self.kind == "node"


def _extract_bearer(authorization: str | None, x_memory_token: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if x_memory_token:
        return x_memory_token.strip()
    return None


def resolve_access(
    request: Request,
    *,
    permission: str,
    bank: str | None = None,
    resource: str = "",
    allow_node: bool = True,
    require_capability_id: str | None = None,
) -> AccessContext:
    """Header：Bearer node_token；或 X-Agent-Id + X-Agent-Token（有 Agent 头则必须过 grant）。"""
    app = request.app
    service = app.state.service
    authorization = request.headers.get("authorization")
    x_memory_token = request.headers.get("x-memory-token")
    agent_id = (request.headers.get("x-agent-id") or "").strip()
    agent_token = (request.headers.get("x-agent-token") or "").strip()

    if agent_id or agent_token:
        if not agent_id or not agent_token:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "agent_headers_incomplete",
                    "message": "X-Agent-Id and X-Agent-Token required together",
                },
            )
        try:
            grant = require_agent_access(
                service.db,
                agent_id,
                agent_token,
                permission=permission,
                bank=bank,
                resource=resource or permission,
            )
        except AgentAccessError as exc:
            raise HTTPException(
                status_code=403,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        ctx = AccessContext(
            kind="agent",
            actor_id=agent_id,
            banks=list(grant.banks),
            permissions=list(grant.permissions),
            grant_id=grant.id,
        )
    else:
        if not allow_node:
            raise HTTPException(
                status_code=401,
                detail={"code": "agent_required", "message": "agent credentials required"},
            )
        token = _extract_bearer(authorization, x_memory_token)
        expected = getattr(app.state, "access_token", "") or ""
        if not expected or not token or not secrets.compare_digest(token, expected):
            raise HTTPException(
                status_code=401,
                detail={"code": "unauthorized", "message": "invalid token"},
            )
        ctx = AccessContext(kind="node", actor_id="node:admin")

    if require_capability_id:
        try:
            require_capability(service.db, require_capability_id)
        except CapabilityLockedError as exc:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "capability_locked",
                    "capability": exc.capability,
                    "message": str(exc),
                },
            ) from exc

    return ctx


def make_access_dep(
    *,
    permission: str,
    resource: str = "",
    require_capability_id: str | None = None,
):
    def _dep(
        request: Request,
        authorization: str | None = Header(default=None),
        x_memory_token: str | None = Header(default=None),
        x_agent_id: str | None = Header(default=None),
        x_agent_token: str | None = Header(default=None),
    ) -> AccessContext:
        _ = (authorization, x_memory_token, x_agent_id, x_agent_token)
        return resolve_access(
            request,
            permission=permission,
            resource=resource or permission,
            require_capability_id=require_capability_id,
        )

    return _dep
