# -*- coding: utf-8 -*-
"""分层检索管线：plan → recall → filter → score → optional deepen。"""

from __future__ import annotations

import time
import traceback
from typing import Any

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import (
    ContextBuildIn,
    Memory,
    MemoryStatus,
    SearchQuery,
)
from cognitive_memory.retrieval.planner import QueryPlan, plan_retrieval
from cognitive_memory.retrieval.scoring import score_memory

RESULT_FOUND = "FOUND"
RESULT_PARTIAL = "PARTIAL"
RESULT_NO_MATCH = "NO_MATCH"
RESULT_FAILED = "FAILED"
RESULT_NOT_NEEDED = "NOT_NEEDED"


def _filter_candidates(memories: list[Memory], plan: QueryPlan) -> list[Memory]:
    out: list[Memory] = []
    for m in memories:
        if m.status == MemoryStatus.INVALIDATED:
            continue
        if plan.mode == "current" and m.status == MemoryStatus.SUPERSEDED:
            continue
        out.append(m)
    return out


def _rank(
    memories: list[Memory],
    query: str,
    *,
    mode: str,
) -> list[tuple[Memory, dict[str, Any]]]:
    scored: list[tuple[Memory, dict[str, Any]]] = []
    for m in memories:
        sc = score_memory(m, query, mode=mode)
        scored.append((m, sc))
    scored.sort(key=lambda x: x[1]["total"], reverse=True)
    return scored


def run_retrieve(
    service: MemoryService,
    *,
    query: str,
    force: bool = False,
    limit: int = 8,
    mode: str = "current",
    spatiotemporal_rerank: bool = True,
    emotion_rerank: bool = False,
    semantic_assist: bool = True,
    semantic_weight: float = 0.25,
    token_budget: int | None = None,
    types: list | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    plan = plan_retrieval(
        query,
        force=force,
        default_mode=mode,
        default_limit=limit,
    )
    trace: dict[str, Any] = {
        "plan": plan.to_dict(),
        "channels": [],
        "deepened": False,
        "error": None,
    }

    if not plan.should_retrieve:
        return {
            "status": RESULT_NOT_NEEDED,
            "plan": plan.to_dict(),
            "items": [],
            "count": 0,
            "brief": "",
            "fragments": [],
            "token_estimate": 0,
            "persisted_ok": True,
            "retrieval_ready": False,
            "trace": {**trace, "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
        }

    try:
        fetch_n = max(plan.limit, min(40, plan.limit * 2))
        hits = service.search(
            SearchQuery(
                query=query,
                types=types,
                limit=fetch_n,
                mode=plan.mode,
                spatiotemporal_rerank=spatiotemporal_rerank,
                emotion_rerank=emotion_rerank,
            )
        )
        trace["channels"].append({"name": "fts_like", "raw_hits": len(hits)})
        filtered = _filter_candidates(hits, plan)
        ranked = _rank(filtered, query, mode=plan.mode)

        # 按需加深：命中不足且 depth!=shallow
        if len(ranked) < plan.expected_min_hits and plan.depth in ("normal", "deep"):
            deep_hits = service.search(
                SearchQuery(
                    query=query,
                    types=types,
                    limit=min(50, fetch_n * 2),
                    mode="any",
                    spatiotemporal_rerank=spatiotemporal_rerank,
                    emotion_rerank=emotion_rerank,
                )
            )
            trace["deepened"] = True
            trace["channels"].append({"name": "deepen_any", "raw_hits": len(deep_hits)})
            seen = {m.id for m, _ in ranked}
            for m in _filter_candidates(deep_hits, plan):
                if m.id not in seen:
                    ranked.append((m, score_memory(m, query, mode="any")))
                    seen.add(m.id)
            ranked.sort(key=lambda x: x[1]["total"], reverse=True)

        ranked = ranked[: plan.limit]
        items = []
        for m, sc in ranked:
            items.append(
                {
                    "id": m.id,
                    "type": m.type.value,
                    "status": m.status.value,
                    "content": m.content,
                    "version": m.version,
                    "source_ids": m.source_ids,
                    "score": sc,
                    "metadata": m.metadata,
                    "authoritative": True,
                }
            )

        if semantic_assist and items:
            from cognitive_memory.retrieval.semantic_sidepath import assist_rerank

            assisted = assist_rerank(
                query, items, weight=float(semantic_weight)
            )
            items = assisted.get("items") or items
            trace["channels"].append(
                {
                    "name": "semantic_assist",
                    "assistive_only": True,
                    "authoritative": False,
                    "weight": float(semantic_weight),
                    "note": "never_verification",
                }
            )

        # 复用 context 打包（与 brief 一致）
        ctx = service.build_context(
            ContextBuildIn(
                query=query,
                token_budget=token_budget,
                types=types,
                limit=plan.limit,
                mode=plan.mode,
                spatiotemporal_rerank=spatiotemporal_rerank,
                emotion_rerank=emotion_rerank,
            )
        )

        if not items:
            status = RESULT_NO_MATCH
        elif len(items) < plan.expected_min_hits or (
            items and items[0]["score"]["total"] < 0.25
        ):
            status = RESULT_PARTIAL
        else:
            status = RESULT_FOUND

        return {
            "status": status,
            "plan": plan.to_dict(),
            "items": items,
            "count": len(items),
            "brief": ctx.brief if items else "",
            "fragments": ctx.fragments if items else [],
            "token_estimate": ctx.token_estimate if items else 0,
            "persisted_ok": True,
            "retrieval_ready": True,
            "trace": {**trace, "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
        }
    except Exception as exc:
        trace["error"] = f"{type(exc).__name__}: {exc}"
        trace["traceback"] = traceback.format_exc(limit=3)
        return {
            "status": RESULT_FAILED,
            "plan": plan.to_dict(),
            "items": [],
            "count": 0,
            "brief": "",
            "fragments": [],
            "token_estimate": 0,
            "persisted_ok": True,
            "retrieval_ready": False,
            "trace": {**trace, "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
            "error": str(exc),
        }
