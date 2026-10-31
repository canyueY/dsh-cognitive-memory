# -*- coding: utf-8 -*-
"""MCP stdio 工具入口 — 全部委托 MemoryService（无第二套逻辑）。

若未安装 mcp SDK，提供最小 JSON-RPC 风格占位，便于契约测试。
"""

from __future__ import annotations

import json
import sys
from typing import Any

from mnemosyne.core.service import ConflictError, MemoryService, NotFoundError
from mnemosyne.domain.models import (
    ContextBuildIn,
    FeedbackIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    MemoryUpdateIn,
    SearchQuery,
)


TOOLS = [
    {
        "name": "memory_search",
        "description": "搜索相关记忆（FTS5，可降级 LIKE）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "types": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_get",
        "description": "获取记忆详情与证据",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "include_evidence": {"type": "boolean"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "memory_context",
        "description": "按 Token 预算组装当前对话上下文",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "token_budget": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_propose",
        "description": "提交候选记忆",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "type": {"type": "string"},
                "source_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["content"],
        },
    },
    {
        "name": "memory_feedback",
        "description": "反馈记忆是否有用或有误",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string"},
                "useful": {"type": "boolean"},
                "incorrect": {"type": "boolean"},
                "note": {"type": "string"},
            },
            "required": ["memory_id"],
        },
    },
    {
        "name": "memory_update",
        "description": "更新已有记忆（支持 expected_version）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "content": {"type": "string"},
                "status": {"type": "string"},
                "expected_version": {"type": "integer"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "memory_forget",
        "description": "删除或使记忆失效",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "hard": {"type": "boolean"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "memory_task_status",
        "description": "查询后台任务",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
]


def _dispatch(service: MemoryService, name: str, args: dict[str, Any]) -> Any:
    if name == "memory_search":
        types = None
        if args.get("types"):
            types = [MemoryType(t) for t in args["types"]]
        rows = service.search(
            SearchQuery(query=args.get("query") or "", limit=int(args.get("limit") or 10), types=types)
        )
        return {"items": [m.model_dump() for m in rows]}
    if name == "memory_get":
        return service.get_memory(args["id"], include_evidence=bool(args.get("include_evidence")))
    if name == "memory_context":
        return service.build_context(
            ContextBuildIn(query=args["query"], token_budget=args.get("token_budget"))
        ).model_dump()
    if name == "memory_propose":
        return service.propose_memory(
            MemoryProposeIn(
                content=args["content"],
                type=MemoryType(args["type"]) if args.get("type") else MemoryType.SEMANTIC,
                source_ids=list(args.get("source_ids") or []),
            )
        ).model_dump()
    if name == "memory_feedback":
        return service.feedback(
            FeedbackIn(
                memory_id=args["memory_id"],
                useful=args.get("useful"),
                incorrect=args.get("incorrect"),
                note=args.get("note") or "",
            )
        )
    if name == "memory_update":
        return service.update_memory(
            args["id"],
            MemoryUpdateIn(
                content=args.get("content"),
                status=MemoryStatus(args["status"]) if args.get("status") else None,
                expected_version=args.get("expected_version"),
            ),
        ).model_dump()
    if name == "memory_forget":
        return service.forget_memory(args["id"], hard=bool(args.get("hard")))
    if name == "memory_task_status":
        return service.get_task(args["id"]).model_dump()
    raise ValueError(f"unknown tool: {name}")


def run_mcp_stdio(service: MemoryService) -> None:
    """极简 MCP-ish JSON-RPC over stdio（兼容测试；正式可换官方 SDK）。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        try:
            if method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                data = _dispatch(service, name, arguments)
                result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}
            elif method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "mnemosyne", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                }
            else:
                raise ValueError(f"unsupported method: {method}")
            resp = {"jsonrpc": "2.0", "id": rid, "result": result}
        except (NotFoundError, ConflictError, ValueError, KeyError) as exc:
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32000, "message": str(exc)},
            }
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()
