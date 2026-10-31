# -*- coding: utf-8 -*-
"""FastAPI REST：统一前缀 /api/v1，全部委托 MemoryService。"""

from __future__ import annotations

import secrets
import uuid
from typing import Any, Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from cognitive_memory.governance.access import AccessContext, make_access_dep, resolve_access

from cognitive_memory.core.service import ConflictError, MemoryService, NotFoundError
from cognitive_memory.domain.models import (
    AuthorityTransitionIn,
    CapabilityCheckIn,
    CapabilitySetIn,
    ChangeDetectIn,
    ChangePlanApplyIn,
    ChangePlanBuildIn,
    ClaimEvidenceIn,
    ClaimProposeIn,
    ClaimRedirectIn,
    ClaimTransitionIn,
    ClaimVerifyIn,
    EvidenceIndependenceIn,
    EvidenceObjectCreateIn,
    AbAssignIn,
    AbOutcomeIn,
    AbReportIn,
    ExperienceCreateIn,
    KnowledgeFromSchemaIn,
    KnowledgeProposeIn,
    KnowledgeStatusIn,
    MetaControllerIn,
    StrategyLogIn,
    StrategyOfflineEvalIn,
    StrategyPropensityIn,
    StrategyProposeIn,
    TmsJustificationIn,
    TmsPropagateIn,
    ValueAdaptIn,
    CognitiveChangePlanApplyIn,
    CognitiveChangePlanIn,
    ContextBuildIn,
    EmotionExtractIn,
    EmotionPatternScanIn,
    EvidenceLink,
    FeedbackIn,
    MemoryProposeIn,
    MemoryRelationIn,
    MemoryUpdateIn,
    ObservationIn,
    PatternScanIn,
    ReevaluateIn,
    ReflectionIn,
    RetrieveIn,
    SchemaAccommodateIn,
    SchemaAssimilateIn,
    SchemaDiscoverIn,
    SearchQuery,
    TaskCreateIn,
    ValueAnalyzeIn,
)


def create_app(
    service: MemoryService,
    *,
    access_token: str,
    api_prefix: str = "/api/v1",
) -> FastAPI:
    app = FastAPI(title="DSH Cognitive Memory", version="0.1.0")
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
    def search(
        body: SearchQuery,
        request: Request,
    ) -> dict[str, Any]:
        # Node token OR agent grant (memory.read); agent 时按 bank 执法
        bank = None
        banks = getattr(body, "banks", None)
        if isinstance(banks, list) and banks:
            bank = str(banks[0])
        access = resolve_access(
            request, permission="memory.read", bank=bank, resource="memories.search"
        )
        rows = service.search(body)
        return {
            "items": [m.model_dump() for m in rows],
            "count": len(rows),
            "actor": access.actor_id,
            "actor_kind": access.kind,
        }

    @app.get(f"{pref}/memories/{{memory_id}}")
    def get_memory(
        memory_id: str,
        include_evidence: bool = False,
        access: AccessContext = Depends(make_access_dep(permission="memory.read", resource="memories.get")),
    ) -> dict[str, Any]:
        out = service.get_memory(memory_id, include_evidence=include_evidence)
        if isinstance(out, dict):
            out = dict(out)
            out["_actor"] = access.actor_id
        return out

    @app.post(f"{pref}/memories")
    def propose(
        body: MemoryProposeIn,
        access: AccessContext = Depends(make_access_dep(permission="memory.write", resource="memories.propose")),
    ) -> dict[str, Any]:
        from cognitive_memory.governance.policy import PolicyDeniedError

        try:
            dump = service.propose_memory(body).model_dump()
        except PolicyDeniedError as exc:
            raise HTTPException(
                status_code=403,
                detail={"code": exc.code, "message": str(exc), "policy": exc.policy},
            ) from exc
        dump["_actor"] = access.actor_id
        return dump

    @app.patch(f"{pref}/memories/{{memory_id}}")
    def update(
        memory_id: str,
        body: MemoryUpdateIn,
        access: AccessContext = Depends(make_access_dep(permission="memory.write", resource="memories.update")),
    ) -> dict[str, Any]:
        dump = service.update_memory(memory_id, body).model_dump()
        dump["_actor"] = access.actor_id
        return dump

    @app.delete(f"{pref}/memories/{{memory_id}}")
    def forget(
        request: Request,
        memory_id: str,
        hard: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        # soft delete: memory.write；hard: memory.delete + MEMORY_HARD_DELETE + confirm
        if hard:
            if not confirm:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "confirm_required", "message": "hard delete requires confirm=true"},
                )
            access = resolve_access(
                request,
                permission="memory.delete",
                resource="memories.forget.hard",
                require_capability_id="MEMORY_HARD_DELETE",
            )
        else:
            access = resolve_access(
                request,
                permission="memory.write",
                resource="memories.forget",
            )
        out = service.forget_memory(memory_id, hard=hard)
        if isinstance(out, dict):
            out = dict(out)
            out["_actor"] = access.actor_id
        return out

    @app.post(f"{pref}/observations")
    def observations(
        body: ObservationIn,
        access: AccessContext = Depends(make_access_dep(permission="memory.write", resource="observations.create")),
    ) -> dict[str, Any]:
        from cognitive_memory.ingestion import ingest_observation

        obs = ingest_observation(service, body)
        # P2：同事务写 SQLite+FTS → PERSISTED 与 INDEXED 同时成立；字段分列便于日后外置索引
        dump = obs.model_dump()
        dump["persisted_ok"] = True
        dump["retrieval_ready"] = True
        dump["write_stages"] = ["RECEIVED", "NORMALIZED", "PERSISTED", "INDEXED", "VERIFIED"]
        dump["_actor"] = access.actor_id
        return dump

    @app.get(f"{pref}/identities")
    def list_identities(
        kind: str | None = None,
        limit: int = 200,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        from cognitive_memory.identity import list_principals

        items = list_principals(service.db, kind=kind, limit=limit)
        return {"items": [p.model_dump() for p in items], "count": len(items)}

    @app.post(f"{pref}/identities")
    def upsert_identity(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.identity import PrincipalUpsert, upsert_principal

        principal = upsert_principal(service.db, PrincipalUpsert.model_validate(body))
        return principal.model_dump()

    @app.get(f"{pref}/identities/{{principal_id}}")
    def get_identity(principal_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.identity import get_principal

        p = get_principal(service.db, principal_id)
        if not p:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": f"identity {principal_id}"},
            )
        return p.model_dump()

    # --- 同 Node 多 Agent：登记 ≠ 授权；grant 含范围/有效期/撤销/审计 ---
    @app.post(f"{pref}/agents/register")
    def agents_register(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.identity import register_agent

        return register_agent(
            service.db,
            agent_id=body.get("agent_id") or body.get("id"),
            display_name=str(body.get("display_name") or ""),
            metadata=dict(body.get("metadata") or {}),
        )

    @app.post(f"{pref}/agents/{{agent_id}}/grants")
    def agents_issue_grant(
        agent_id: str, body: dict[str, Any], _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.identity import AgentAccessError, issue_grant

        try:
            return issue_grant(
                service.db,
                agent_id,
                permissions=list(body.get("permissions") or ["memory.read"]),
                banks=list(body.get("banks") or ["personal"]),
                expires_in_sec=body.get("expires_in_sec", 86400 * 30),
                consent=dict(body.get("consent") or {"user_consent": True}),
                rotate_token=bool(body.get("rotate_token", True)),
            )
        except AgentAccessError as exc:
            raise HTTPException(
                status_code=400, detail={"code": exc.code, "message": str(exc)}
            ) from exc

    @app.get(f"{pref}/agents/grants")
    def agents_list_grants(
        limit: int = 200, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.identity import list_grants

        items = list_grants(service.db, limit=limit)
        return {"items": items, "count": len(items)}

    @app.post(f"{pref}/agents/{{agent_id}}/revoke")
    def agents_revoke(
        agent_id: str, body: dict[str, Any] | None = None, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.identity import revoke_grant

        body = body or {}
        return revoke_grant(service.db, agent_id, reason=str(body.get("reason") or ""))

    @app.post(f"{pref}/agents/check")
    def agents_check(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        """运维侧试算：用明文 agent_token 检查权限（不替代业务入口）。"""
        from cognitive_memory.identity import AgentAccessError, require_agent_access

        try:
            grant = require_agent_access(
                service.db,
                str(body.get("agent_id") or ""),
                str(body.get("agent_token") or ""),
                permission=str(body.get("permission") or "memory.read"),
                bank=body.get("bank"),
                resource=str(body.get("resource") or "check"),
            )
            return {"ok": True, "grant": grant.to_dict()}
        except AgentAccessError as exc:
            return {"ok": False, "code": exc.code, "message": str(exc)}

    @app.get(f"{pref}/agents/audit")
    def agents_audit(
        agent_id: str | None = None,
        limit: int = 100,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        from cognitive_memory.identity import list_audit

        items = list_audit(service.db, agent_id=agent_id, limit=limit)
        return {"items": items, "count": len(items)}

    @app.post(f"{pref}/agents/act/search")
    def agents_act_search(body: dict[str, Any]) -> dict[str, Any]:
        """Agent 入口：须 agent_id + agent_token；按 grant 隔离 Bank。"""
        from cognitive_memory.identity import AgentAccessError, require_agent_access

        agent_id = str(body.get("agent_id") or "")
        token = str(body.get("agent_token") or "")
        bank = str(body.get("bank") or "personal")
        try:
            require_agent_access(
                service.db,
                agent_id,
                token,
                permission="memory.read",
                bank=bank,
                resource="memories.search",
            )
        except AgentAccessError as exc:
            raise HTTPException(
                status_code=403, detail={"code": exc.code, "message": str(exc)}
            ) from exc
        q = SearchQuery(
            query=str(body.get("query") or ""),
            limit=int(body.get("limit") or 20),
            banks=[bank],
        )
        memories = service.search(q)
        items = [m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in memories]
        return {
            "ok": True,
            "agent_id": agent_id,
            "bank": bank,
            "count": len(items),
            "items": items,
        }

    @app.post(f"{pref}/evidence")
    def evidence_attach(body: EvidenceLink, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.evidence import EvidenceAttachIn
        from cognitive_memory.evidence.object_store import EvidenceObjectStore

        legacy = service.attach_evidence(
            EvidenceAttachIn(
                memory_id=body.memory_id,
                observation_id=body.observation_id,
                relation=body.relation.value
                if hasattr(body.relation, "value")
                else str(body.relation),
                note=body.note,
                confidence=body.confidence,
                evidence_kind=body.evidence_kind,  # type: ignore[arg-type]
                validation_state=body.validation_state,  # type: ignore[arg-type]
                producer=body.producer,
                metadata=body.metadata,
            )
        )
        # P3: also materialize first-class Evidence (never invent observation_id)
        obj = EvidenceObjectStore(service.db).from_legacy_memory_link(
            memory_id=body.memory_id,
            observation_id=body.observation_id,
            relation=body.relation.value
            if hasattr(body.relation, "value")
            else str(body.relation),
            producer=body.producer or "",
        )
        pack = legacy.model_dump(mode="json") if hasattr(legacy, "model_dump") else dict(legacy)
        pack["evidence_object"] = obj.get("evidence")
        pack["evidence_object_ok"] = bool(obj.get("ok"))
        return pack

    @app.post(f"{pref}/evidences")
    def evidences_create(
        body: EvidenceObjectCreateIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="evidences.create")
        ),
    ) -> dict[str, Any]:
        _ = access
        from cognitive_memory.evidence.object_store import EvidenceObjectStore

        return EvidenceObjectStore(service.db).create(
            source_type=body.source_type,
            source_ref=body.source_ref,
            bank_id=body.bank_id,
            content_for_fingerprint=body.content,
            producer=body.producer,
            role_hint=body.role_hint,
            legacy_memory_id=body.legacy_memory_id,
        )

    @app.get(f"{pref}/evidences/{{evidence_id}}")
    def evidences_get(
        evidence_id: str,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="evidences.get")
        ),
    ) -> dict[str, Any]:
        _ = access
        from cognitive_memory.evidence.object_store import EvidenceObjectStore

        ev = EvidenceObjectStore(service.db).get(evidence_id)
        if not ev:
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "evidence"}
            )
        return {"ok": True, "evidence": ev}

    @app.post(f"{pref}/evidences/independence")
    def evidences_independence(
        body: EvidenceIndependenceIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="evidences.independence")
        ),
    ) -> dict[str, Any]:
        _ = access
        from cognitive_memory.evidence.object_store import EvidenceObjectStore

        return EvidenceObjectStore(service.db).independence_conflict(body.evidence_ids)

    @app.get(f"{pref}/memories/{{memory_id}}/evidence")
    def evidence_list(memory_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        items = service.list_evidence(memory_id)
        return {"items": items, "count": len(items)}

    @app.get(f"{pref}/banks")
    def banks(_: None = Depends(require_token)) -> dict[str, Any]:
        items = service.list_banks()
        return {"items": items, "count": len(items)}

    @app.get(f"{pref}/authority")
    def authority_get(_: None = Depends(require_token)) -> dict[str, Any]:
        return service.get_authority()

    @app.post(f"{pref}/authority/transition")
    def authority_transition(
        body: AuthorityTransitionIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        return service.transition_authority(
            body.state,
            reason=body.reason,
            allow_dual=body.allow_dual,
            actor=body.actor,
        )

    @app.get(f"{pref}/authority/cutover/preview")
    def authority_cutover_preview(_: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.governance.cutover import preview_cutover

        return preview_cutover(service)

    @app.post(f"{pref}/authority/cutover/execute")
    def authority_cutover_execute(
        body: dict[str, Any], _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.governance.cutover import execute_cutover

        return execute_cutover(
            service,
            target=body.get("target"),
            confirm=bool(body.get("confirm")),
            allow_dual=bool(body.get("allow_dual")),
            reason=str(body.get("reason") or ""),
            actor=str(body.get("actor") or "api"),
        )

    @app.post(f"{pref}/adoption/export")
    def adoption_export(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        """导出 Interchange JSONL（可选 bank 范围）；默认 enforce allow_forward。"""
        from pathlib import Path as _P

        from cognitive_memory.migration.export_interchange import (
            export_interchange_jsonl,
            memories_to_interchange,
        )

        limit = int(body.get("limit") or 500)
        out = str(body.get("path") or "")
        if not out:
            root = _P(service.db.path).resolve().parent.parent
            out = str(root / "exports" / "interchange-export.jsonl")
        enforce = body.get("enforce_forward_policy")
        if enforce is None:
            enforce = True
        records = memories_to_interchange(
            service, limit=limit, enforce_forward_policy=bool(enforce)
        )
        banks = body.get("banks")
        if isinstance(banks, list) and banks:
            allow = {str(b) for b in banks}
            records = [r for r in records if str((r.extensions or {}).get("bank_id") or "personal") in allow]
        result = export_interchange_jsonl(records, _P(out))
        skipped = getattr(service, "_last_export_policy_skipped", []) or []
        result["policy_skipped"] = skipped
        result["policy_skipped_count"] = len(skipped)
        return result

    @app.get(f"{pref}/contract")
    def contract(_: None = Depends(require_token)) -> dict[str, Any]:
        return service.service_contract()

    @app.post(f"{pref}/feedback")
    def feedback(body: FeedbackIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.feedback(body)

    @app.post(f"{pref}/contexts/build")
    def contexts(body: ContextBuildIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.build_context(body).model_dump()

    @app.post(f"{pref}/retrieve")
    def retrieve(body: RetrieveIn, _: None = Depends(require_token)) -> dict[str, Any]:
        """统一检索：Planner → 召回/过滤/排序；结果态含 NOT_NEEDED/FAILED。"""
        from cognitive_memory.retrieval.pipeline import run_retrieve

        return run_retrieve(
            service,
            query=body.query,
            force=body.force,
            limit=body.limit,
            mode=body.mode,
            spatiotemporal_rerank=body.spatiotemporal_rerank,
            emotion_rerank=body.emotion_rerank,
            semantic_assist=bool(body.semantic_assist),
            semantic_weight=float(body.semantic_weight),
            ab_experiment=bool(body.ab_experiment),
            ab_subject_key=str(body.ab_subject_key or ""),
            token_budget=body.token_budget,
            types=body.types,
        )

    @app.post(f"{pref}/tasks")
    def create_task(body: TaskCreateIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.create_task(body).model_dump()

    @app.get(f"{pref}/tasks/{{task_id}}")
    def get_task(task_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.get_task(task_id).model_dump()

    # ---- P2–P5 spatiotemporal ----
    @app.post(f"{pref}/relations")
    def create_relation(body: MemoryRelationIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.link_memories(
            from_id=body.from_id,
            to_id=body.to_id,
            relation=body.relation,
            note=body.note,
            valid_from=body.valid_from,
            valid_until=body.valid_until,
            confidence=body.confidence,
            metadata=body.metadata,
        )

    @app.get(f"{pref}/memories/{{memory_id}}/relations")
    def get_relations(memory_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        items = service.list_relations(memory_id)
        return {"items": items, "count": len(items)}

    @app.post(f"{pref}/changes/detect")
    def changes_detect(body: ChangeDetectIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.change_detect import detect_changes_for_observation

        result = detect_changes_for_observation(
            service,
            body.observation_id,
            dry_run=body.dry_run,
            apply_l2=body.apply_l2,
        )
        service.store_change_candidates(
            observation_id=body.observation_id,
            candidates=list(result.get("candidates") or []),
            dry_run=body.dry_run,
            applied=list(result.get("applied") or []),
        )
        return result

    @app.get(f"{pref}/changes/candidates")
    def changes_candidates(
        limit: int = 40,
        applied: str | None = "false",
        types: str | None = None,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        applied_flag: bool | None
        if applied is None or str(applied).strip().lower() in ("", "any", "all"):
            applied_flag = None
        elif str(applied).strip().lower() in ("1", "true", "yes"):
            applied_flag = True
        else:
            applied_flag = False
        type_list = [t.strip() for t in str(types or "").split(",") if t.strip()] or None
        items = service.list_change_candidates(
            limit=limit, applied=applied_flag, change_types=type_list
        )
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/changes/plans")
    def changes_plans_build(body: ChangePlanBuildIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.change_plan import build_plans_for_observation

        return build_plans_for_observation(
            service,
            body.observation_id,
            dry_run=body.dry_run,
            persist=body.persist,
        )

    @app.get(f"{pref}/changes/plans")
    def changes_plans_list(
        limit: int = 40,
        execution_status: str | None = None,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        items = service.list_change_plans(limit=limit, execution_status=execution_status)
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/changes/plans/{{plan_id}}/apply")
    def changes_plans_apply(
        plan_id: str,
        body: ChangePlanApplyIn,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        from cognitive_memory.cognition.change_plan import apply_change_plan

    
        return apply_change_plan(service, plan_id, confirm=bool(body.confirm))


    @app.post(f"{pref}/changes/plans/{{plan_id}}/rollback")
    def changes_plans_rollback(plan_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.change_plan import rollback_change_plan

        return rollback_change_plan(service, plan_id)

    @app.post(f"{pref}/interests/trends")
    def interests_trends(body: PatternScanIn, _: None = Depends(require_token)) -> dict[str, Any]:
        """P4：兴趣/习惯趋势候选（不升格事实）。"""
        from cognitive_memory.cognition.persistence import scan_persistence_patterns

        return scan_persistence_patterns(
            service,
            limit_obs=body.limit_obs,
            min_days=body.min_days,
            min_count=body.min_count,
        )

    @app.post(f"{pref}/reevaluate")
    def reevaluate(body: ReevaluateIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.reevaluate import run_reevaluation

        return run_reevaluation(
            service,
            dry_run=body.dry_run,
            apply_l2=body.apply_l2,
            limit=body.limit,
        )

    @app.post(f"{pref}/patterns/scan")
    def patterns_scan(body: PatternScanIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.persistence import scan_persistence_patterns

        return scan_persistence_patterns(
            service,
            limit_obs=body.limit_obs,
            min_days=body.min_days,
            min_count=body.min_count,
        )

    # ---- Mnemosyne emotion (shadow by default) ----
    @app.post(f"{pref}/emotion/extract")
    def emotion_extract(body: EmotionExtractIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.emotion_extract import extract_emotion_for_observation

        return extract_emotion_for_observation(
            service,
            body.observation_id,
            shadow_only=body.shadow_only,
            write_enabled=body.write_enabled,
            min_confidence=body.min_confidence,
        )

    @app.get(f"{pref}/emotion/candidates")
    def emotion_candidates(
        limit: int = 40,
        written: str | None = "false",
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        written_flag: bool | None
        if written is None or str(written).strip().lower() in ("", "any", "all"):
            written_flag = None
        elif str(written).strip().lower() in ("1", "true", "yes"):
            written_flag = True
        else:
            written_flag = False
        items = service.list_emotion_candidates(limit=limit, written=written_flag)
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/emotion/patterns/scan")
    def emotion_patterns_scan(
        body: EmotionPatternScanIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.cognition.emotion_patterns import scan_emotion_behavior_patterns
        from cognitive_memory.domain.models import ObservationIn, SourceKind

        pack = scan_emotion_behavior_patterns(
            service,
            limit_obs=body.limit_obs,
            min_days=body.min_days,
            min_count=body.min_count,
        )
        if body.persist_summary and pack.get("pattern_candidates"):
            lines = ["【桌宠梳理·情绪行为模式候选】仅趋势，非已确认因果"]
            for c in (pack.get("pattern_candidates") or [])[:10]:
                lines.append(
                    f"- {c.get('emotion')}→{c.get('behavior')} "
                    f"days={c.get('day_count')} count={c.get('count')}"
                )
            service.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.SYSTEM,
                    content="\n".join(lines),
                    producer="mnemosyne.pattern_scan",
                    metadata={"mnemosyne_pattern_scan": True, "count": pack.get("count")},
                )
            )
        return pack

    # ---- Mnemosyne 2.0：Cognitive Schema + Capability Gate ----
    @app.post(f"{pref}/schemas/discover")
    def schemas_discover(body: SchemaDiscoverIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.schema_discovery import discover_schema_candidates

        return discover_schema_candidates(
            service,
            limit_memories=body.limit_memories,
            min_cluster=body.min_cluster,
            min_similarity=body.min_similarity,
            persist=body.persist,
        )

    # ---- P2 Claim vertical slice ----
    def _claim_store():
        from cognitive_memory.claims.store import ClaimStore

        if not hasattr(app.state, "claim_store"):
            app.state.claim_store = ClaimStore(service.db)
        return app.state.claim_store

    @app.post(f"{pref}/claims/propose")
    def claims_propose(
        body: ClaimProposeIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="claims.propose")
        ),
    ) -> dict[str, Any]:
        sec = access.to_security_context(default_bank=body.bank_id)
        if not sec.allows_bank(body.bank_id) and not access.is_node_admin:
            raise HTTPException(
                status_code=403,
                detail={"code": "bank_denied", "message": "claim bank not granted"},
            )
        return _claim_store().propose_from_text(
            body.text,
            bank_id=body.bank_id,
            source_memory_id=body.source_memory_id,
            persist_unresolved=body.persist_unresolved,
        )

    @app.get(f"{pref}/claims/{{claim_id}}")
    def claims_get(
        claim_id: str,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="claims.get")
        ),
    ) -> dict[str, Any]:
        # Peek bank without visibility first (node-only internal); then re-get with principal
        raw = _claim_store().get(claim_id, follow_redirect=False, principal=None)
        if not raw:
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "claim"}
            )
        bank = str(raw.get("bank_id") or "personal")
        if access.is_node_admin:
            # Node admin still evaluated against default personal unless grants list banks
            principal = access.to_security_context(default_bank=bank)
            # Node admin may read any bank
            principal.authorized_grants = list(
                set(principal.authorized_grants or []) | {f"bank:{bank}"}
            )
            principal.bank_id = bank
        else:
            principal = access.to_security_context(default_bank=bank)
        pack = _claim_store().get(claim_id, principal=principal)
        if not pack:
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "claim"}
            )
        return {"ok": True, "claim": pack}

    @app.post(f"{pref}/claims/{{claim_id}}/transition")
    def claims_transition(
        claim_id: str,
        body: ClaimTransitionIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="claims.transition")
        ),
    ) -> dict[str, Any]:
        return _claim_store().transition(
            claim_id,
            body.target_status,
            reason=body.reason,
            evidence_refs=body.evidence_refs,
            actor=body.actor or access.actor_id,
        )

    @app.post(f"{pref}/claims/{{claim_id}}/evidence")
    def claims_evidence(
        claim_id: str,
        body: ClaimEvidenceIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="claims.evidence")
        ),
    ) -> dict[str, Any]:
        _ = access
        return _claim_store().attach_evidence(
            claim_id,
            body.evidence_ref,
            role=body.role,
            independent=body.independent,
        )

    @app.post(f"{pref}/claims/{{claim_id}}/redirect")
    def claims_redirect(
        claim_id: str,
        body: ClaimRedirectIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="claims.redirect")
        ),
    ) -> dict[str, Any]:
        _ = access
        return _claim_store().redirect(claim_id, body.target_id, reason=body.reason)

    @app.post(f"{pref}/claims/{{claim_id}}/verify")
    def claims_verify(
        claim_id: str,
        body: ClaimVerifyIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="claims.verify")
        ),
    ) -> dict[str, Any]:
        return _claim_store().submit_verified(
            claim_id,
            evidence_refs=body.evidence_refs,
            actor=body.actor or access.actor_id,
            authorized=True,
            evidence_still_valid=body.evidence_still_valid,
        )

    @app.post(f"{pref}/claims/semantic-suggest")
    def claims_semantic_suggest(
        body: dict[str, Any],
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="claims.semantic_suggest")
        ),
    ) -> dict[str, Any]:
        _ = access
        return _claim_store().semantic_suggest(
            str(body.get("query") or ""),
            bank_id=str(body.get("bank_id") or "personal"),
            limit=int(body.get("limit") or 5),
            min_score=float(body.get("min_score") or 0.35),
        )

    # ---- P4 Truth Maintenance ----
    @app.post(f"{pref}/tms/justifications")
    def tms_add_justification(
        body: TmsJustificationIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="tms.justification")
        ),
    ) -> dict[str, Any]:
        return _claim_store().tms.add_and_persist(
            body.conclusion_id,
            body.premises,
            kind=body.kind,
            reason=body.reason,
            actor=body.actor or access.actor_id,
        )

    @app.post(f"{pref}/tms/propagate")
    def tms_propagate(
        body: TmsPropagateIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="tms.propagate")
        ),
    ) -> dict[str, Any]:
        _ = access
        eng = _claim_store().tms.engine
        result = eng.propagate(
            list(body.seed_ids),
            max_nodes=int(body.max_nodes),
            max_depth=int(body.max_depth),
        )
        return {"ok": True, "result": result.model_dump(mode="json")}

    @app.get(f"{pref}/tms/belief/{{node_id}}")
    def tms_belief(
        node_id: str,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="tms.belief")
        ),
    ) -> dict[str, Any]:
        _ = access
        bel = _claim_store().tms.get_belief(node_id)
        impact = _claim_store().tms.engine.impact(node_id)
        return {"ok": True, "belief": bel.model_dump(mode="json"), "impact": impact}

    # ---- P5 Experience / Strategy ----
    @app.post(f"{pref}/experiences")
    def experience_create(
        body: ExperienceCreateIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="experience.create")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.experience_store import ExperienceStore

        _ = access
        return ExperienceStore(service.db).create(
            context=body.context,
            action=body.action,
            outcome=body.outcome,
            memory_ids=body.memory_ids,
            claim_ids=body.claim_ids,
            reward=body.reward,
            bank_id=body.bank_id,
            source=body.source,
        )

    @app.get(f"{pref}/experiences")
    def experience_list(
        bank_id: str | None = None,
        limit: int = 50,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="experience.list")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.experience_store import ExperienceStore

        _ = access
        items = ExperienceStore(service.db).list(bank_id=bank_id, limit=limit)
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/strategies")
    def strategy_propose(
        body: StrategyProposeIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="strategy.propose")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.strategy_store import StrategyStore

        _ = access
        return StrategyStore(service.db).propose(
            body.name,
            description=body.description,
            scope=body.scope,
            status=body.status,
        )

    @app.get(f"{pref}/strategies")
    def strategy_list(
        status: str | None = None,
        limit: int = 50,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="strategy.list")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.strategy_store import StrategyStore

        _ = access
        items = StrategyStore(service.db).list(status=status, limit=limit)
        return {"ok": True, "items": items, "count": len(items)}

    @app.get(f"{pref}/strategies/{{strategy_id}}")
    def strategy_get(
        strategy_id: str,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="strategy.get")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.strategy_store import StrategyStore

        _ = access
        row = StrategyStore(service.db).get(strategy_id)
        if not row:
            raise HTTPException(status_code=404, detail="strategy_not_found")
        return {"ok": True, "strategy": row}

    @app.post(f"{pref}/strategies/{{strategy_id}}/log")
    def strategy_log(
        strategy_id: str,
        body: StrategyLogIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="strategy.log")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.strategy_store import StrategyStore

        _ = access
        return StrategyStore(service.db).log(
            strategy_id,
            experience_id=body.experience_id,
            decision=body.decision,
            outcome=body.outcome,
            propensity=body.propensity,
            overlap=body.overlap,
            detail=body.detail,
        )

    @app.post(f"{pref}/strategies/{{strategy_id}}/activate")
    def strategy_activate(
        strategy_id: str,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="strategy.activate")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.strategy_store import StrategyStore

        _ = access
        return StrategyStore(service.db).activate(strategy_id)

    @app.post(f"{pref}/strategies/{{strategy_id}}/retire")
    def strategy_retire(
        strategy_id: str,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="strategy.retire")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.strategy_store import StrategyStore

        _ = access
        return StrategyStore(service.db).retire(strategy_id)

    @app.post(f"{pref}/strategies/propensity")
    def strategy_propensity(
        body: StrategyPropensityIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="strategy.propensity")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.experience_store import ExperienceStore
        from cognitive_memory.strategy.propensity import compute_propensity
        from cognitive_memory.strategy.strategy_store import StrategyStore

        _ = access
        scope = dict(body.scope or {})
        if body.strategy_id:
            strat = StrategyStore(service.db).get(body.strategy_id)
            if not strat:
                return {"ok": False, "detail": "strategy_not_found"}
            if not scope:
                scope = dict(strat.get("scope") or {})
        store = ExperienceStore(service.db)
        exps: list[dict[str, Any]] = []
        if body.experience_ids:
            for eid in body.experience_ids:
                row = store.get(eid)
                if row:
                    exps.append(row)
        else:
            exps = store.list(limit=100)
        prop = compute_propensity(exps, strategy_scope=scope)
        return {"ok": True, "strategy_id": body.strategy_id, "propensity": prop}

    @app.post(f"{pref}/strategies/offline-eval")
    def strategy_offline_eval(
        body: StrategyOfflineEvalIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="strategy.offline_eval")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.offline_eval import run_offline_eval

        _ = access
        return run_offline_eval(
            service.db,
            body.strategy_id,
            persist_propensity=body.persist_propensity,
            log_result=body.log_result,
        )

    @app.post(f"{pref}/meta/schedule")
    def meta_schedule(
        body: MetaControllerIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="meta.schedule")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.strategy.metacontroller import schedule

        _ = access
        return schedule(
            service.db,
            action=body.action,
            strategy_id=body.strategy_id,
            ab_experiment=bool(body.ab_experiment),
        )

    @app.post(f"{pref}/ab/assign")
    def ab_assign(
        body: AbAssignIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="ab.assign")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.governance.ab_experiment import assign_arm

        _ = access
        return assign_arm(
            service.db,
            body.experiment_id,
            subject_key=body.subject_key,
            context=body.context,
        )

    @app.post(f"{pref}/ab/outcome")
    def ab_outcome(
        body: AbOutcomeIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="ab.outcome")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.governance.ab_experiment import record_outcome

        _ = access
        return record_outcome(
            service.db,
            body.exposure_id,
            reward=body.reward,
            label=body.label,
            detail=body.detail,
        )

    @app.post(f"{pref}/ab/report")
    def ab_report(
        body: AbReportIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="ab.report")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.governance.ab_experiment import report

        _ = access
        return report(service.db, body.experiment_id, limit=body.limit)

    # ---- Knowledge (Claim/Schema/Strategy downstream) ----
    @app.post(f"{pref}/knowledge")
    def knowledge_propose(
        body: KnowledgeProposeIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="knowledge.propose")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.knowledge.store import KnowledgeStore

        _ = access
        return KnowledgeStore(service.db).propose(
            kind=body.kind,
            name=body.name,
            description=body.description,
            claim_ids=body.claim_ids,
            schema_id=body.schema_id,
            strategy_id=body.strategy_id,
            payload=body.payload,
            scope=body.scope,
            security=body.security,
            status=body.status,
        )

    @app.get(f"{pref}/knowledge")
    def knowledge_list(
        kind: str | None = None,
        status: str | None = None,
        limit: int = 50,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="knowledge.list")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.knowledge.store import KnowledgeStore

        _ = access
        items = KnowledgeStore(service.db).list(kind=kind, status=status, limit=limit)
        return {"ok": True, "items": items, "count": len(items)}

    @app.get(f"{pref}/knowledge/{{knowledge_id}}")
    def knowledge_get(
        knowledge_id: str,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.read", resource="knowledge.get")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.knowledge.store import KnowledgeStore

        _ = access
        row = KnowledgeStore(service.db).get(knowledge_id)
        if not row:
            raise HTTPException(status_code=404, detail="knowledge_not_found")
        return {"ok": True, "knowledge": row}

    @app.post(f"{pref}/knowledge/{{knowledge_id}}/status")
    def knowledge_status(
        knowledge_id: str,
        body: KnowledgeStatusIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="knowledge.status")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.knowledge.store import KnowledgeStore

        _ = access
        return KnowledgeStore(service.db).set_status(knowledge_id, body.status)

    @app.post(f"{pref}/knowledge/from-schema")
    def knowledge_from_schema(
        body: KnowledgeFromSchemaIn,
        access: AccessContext = Depends(
            make_access_dep(permission="memory.write", resource="knowledge.from_schema")
        ),
    ) -> dict[str, Any]:
        from cognitive_memory.knowledge.store import KnowledgeStore

        _ = access
        return KnowledgeStore(service.db).from_schema(
            body.schema_id,
            name=body.name,
            as_pattern=body.as_pattern,
            payload=body.payload,
        )

    @app.get(f"{pref}/schemas")
    def schemas_list(
        limit: int = 40,
        state: str | None = None,
        schema_type: str | None = None,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        items = service.list_cognitive_schemas(
            limit=limit, state=state, schema_type=schema_type
        )
        return {"ok": True, "items": items, "count": len(items)}

    @app.get(f"{pref}/schemas/{{schema_id}}")
    def schemas_get(schema_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        sch = service.get_cognitive_schema(schema_id)
        if not sch:
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "schema"}
            )
        return sch

    @app.post(f"{pref}/schemas/{{schema_id}}/assimilate")
    def schemas_assimilate(
        schema_id: str,
        body: SchemaAssimilateIn,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        from cognitive_memory.cognition.schema_ops import assimilate_schema

        return assimilate_schema(
            service,
            schema_id,
            memory_ids=body.memory_ids,
            note=body.note,
            confirm=bool(body.confirm),
            preview=bool(body.preview),
        )

    @app.post(f"{pref}/schemas/{{schema_id}}/split")
    def schemas_split(
        schema_id: str,
        body: dict[str, Any],
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        from cognitive_memory.cognition.schema_network import split_schema

        return split_schema(
            service,
            schema_id,
            child_specs=list(body.get("child_specs") or []),
            note=str(body.get("note") or ""),
            confirm=bool(body.get("confirm")),
        )

    @app.post(f"{pref}/schemas/merge")
    def schemas_merge(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.schema_network import merge_schemas

        return merge_schemas(
            service,
            list(body.get("schema_ids") or []),
            name=body.get("name"),
            note=str(body.get("note") or ""),
            confirm=bool(body.get("confirm")),
        )

    @app.get(f"{pref}/schemas/{{schema_id}}/impact")
    def schemas_impact(schema_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.cognition.schema_network import impact_of_schema

        return impact_of_schema(service, schema_id)

    @app.post(f"{pref}/schemas/{{schema_id}}/accommodate")
    def schemas_accommodate(
        schema_id: str,
        body: SchemaAccommodateIn,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        from cognitive_memory.cognition.schema_ops import accommodate_schema

        return accommodate_schema(
            service,
            schema_id,
            memory_ids=body.memory_ids,
            counter_note=body.counter_note,
            propose_split=body.propose_split,
            confirm=bool(body.confirm),
            preview=bool(body.preview),
        )

    @app.post(f"{pref}/schemas/plans")
    def schemas_plans_create(
        body: CognitiveChangePlanIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        pid = service.store_cognitive_change_plan(
            {
                "operation": body.operation,
                "targetSchemaIds": body.target_schema_ids,
                "evidenceRefs": body.evidence_refs,
                "expectedImpact": body.expected_impact,
                "risk_level": body.risk_level,
                "approval_required": body.approval_required,
                "status": "PROPOSED",
                "reason": body.reason,
            }
        )
        return {"ok": True, "id": pid, "plan": service.get_cognitive_change_plan(pid)}

    @app.get(f"{pref}/schemas/plans")
    def schemas_plans_list(
        limit: int = 40,
        status: str | None = None,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        items = service.list_cognitive_change_plans(limit=limit, status=status)
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/schemas/plans/{{plan_id}}/apply")
    def schemas_plans_apply(
        plan_id: str,
        body: CognitiveChangePlanApplyIn,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        from cognitive_memory.cognition.schema_ops import apply_cognitive_change_plan

        return apply_cognitive_change_plan(
            service,
            plan_id,
            confirm=bool(body.confirm),
            preview=bool(getattr(body, "preview", False)),
        )

    @app.post(f"{pref}/metacognition/reflect")
    def metacognition_reflect(
        body: ReflectionIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.cognition.metacognition import reflect

        return reflect(
            service,
            judgment=body.judgment,
            schema_ids=body.schema_ids,
            memory_ids=body.memory_ids,
        )

    @app.get(f"{pref}/metacognition/impact/{{schema_id}}")
    def metacognition_impact(
        schema_id: str, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.cognition.metacognition import analyze_impact

        return analyze_impact(service, schema_id)

    @app.get(f"{pref}/capabilities")
    def capabilities_list(_: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.governance.capability_gate import list_capabilities

        items = list_capabilities(service.db)
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/capabilities/check")
    def capabilities_check(
        body: CapabilityCheckIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.governance.capability_gate import check_capability

        return check_capability(service.db, body.capability)

    @app.post(f"{pref}/capabilities/set")
    def capabilities_set(
        body: CapabilitySetIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        """外部治理专用；不向 Agent 工具暴露。"""
        from cognitive_memory.governance.capability_gate import set_capability_level

        return set_capability_level(
            service.db,
            body.capability,
            level=body.level,
            enabled=body.enabled,
            actor=body.actor or "external_governance",
        )

    @app.post(f"{pref}/rl/train")
    def rl_train(body: dict[str, Any] | None = None, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.governance.policy import PolicyDeniedError, assert_allow_train
        from cognitive_memory.governance.reinforcement_learning import run_offline_training

        req = dict(body or {})
        # 样本可带 metadata.policy；未显式允许 train 则拒绝（字段≠默认可训）
        samples = req.get("samples") if isinstance(req.get("samples"), list) else []
        if not samples and isinstance(req.get("metadata"), dict):
            samples = [{"metadata": req["metadata"]}]
        if not samples:
            # 无样本时仍走 Gate；策略层要求至少声明 allow_train 意图
            samples = [{"metadata": {"policy": {"allow_train": False}}}]
        try:
            for sample in samples:
                meta = sample.get("metadata") if isinstance(sample, dict) else None
                assert_allow_train(meta if isinstance(meta, dict) else {})
        except PolicyDeniedError as exc:
            raise HTTPException(
                status_code=403,
                detail={"code": exc.code, "message": str(exc), "policy": exc.policy},
            ) from exc
        return run_offline_training(service.db, req)

    @app.post(f"{pref}/rl/deploy")
    def rl_deploy(policy_id: str = "default", _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.governance.reinforcement_learning import deploy_policy

        return deploy_policy(service.db, policy_id)

    @app.post(f"{pref}/value/analyze")
    def value_analyze(body: ValueAnalyzeIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.governance.value_system import analyze_value_conflict_basic

        return analyze_value_conflict_basic(
            body.intent,
            stakeholders=body.stakeholders,
            proposed_action=body.proposed_action,
        )

    @app.post(f"{pref}/value/advanced")
    def value_advanced(
        body: dict[str, Any] | None = None, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from cognitive_memory.governance.value_system import run_advanced_value_evaluation

        return run_advanced_value_evaluation(service.db, dict(body or {}))

    @app.post(f"{pref}/value/adapt")
    def value_adapt(body: ValueAdaptIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from cognitive_memory.governance.value_system import adapt_value_model

        patch = dict(body.patch or {})
        patch["_actor"] = body.actor
        return adapt_value_model(service.db, patch)

    # --- D8 Component Manager（本地源；安装 ≠ 授权）---
    from pathlib import Path as _Path

    from cognitive_memory.components.manager import ComponentManager
    from cognitive_memory.components.profiles import get_profile, list_profiles

    _comp_root = _Path(service.db.path).resolve().parent.parent
    app.state.components = ComponentManager(_comp_root)

    def _components() -> ComponentManager:
        return app.state.components

    @app.get(f"{pref}/components")
    def components_list(_: None = Depends(require_token)) -> dict[str, Any]:
        return {"items": _components().list()}

    @app.get(f"{pref}/components/profiles")
    def components_profiles(_: None = Depends(require_token)) -> dict[str, Any]:
        return {"profiles": list_profiles()}

    @app.get(f"{pref}/components/profiles/{{profile_id}}")
    def components_profile(profile_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        p = get_profile(profile_id)
        if not p:
            raise HTTPException(status_code=404, detail={"code": "profile_not_found"})
        return p

    @app.post(f"{pref}/components/inspect")
    def components_inspect(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        return _components().inspect(str(body.get("source") or ""))

    @app.post(f"{pref}/components/resolve")
    def components_resolve(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        return _components().resolve(str(body.get("source") or ""))

    @app.post(f"{pref}/components/install")
    def components_install(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        return _components().install(
            str(body.get("source") or ""),
            force=bool(body.get("force")),
            skip_resolve=bool(body.get("skip_resolve")),
            authorize=bool(body.get("authorize")),
        )

    @app.get(f"{pref}/components/{{component_id}}")
    def components_get(component_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        item = _components().get(component_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "component_not_found"})
        return item

    @app.post(f"{pref}/components/{{component_id}}/configure")
    def components_configure(
        component_id: str, body: dict[str, Any], _: None = Depends(require_token)
    ) -> dict[str, Any]:
        return _components().configure(component_id, dict(body.get("config") or body))

    @app.post(f"{pref}/components/{{component_id}}/authorize")
    def components_authorize(component_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        return _components().authorize(component_id)

    @app.post(f"{pref}/components/{{component_id}}/enable")
    def components_enable(
        component_id: str, body: dict[str, Any] | None = None, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        body = body or {}
        return _components().enable(component_id, require_auth=bool(body.get("require_auth")))

    @app.post(f"{pref}/components/{{component_id}}/disable")
    def components_disable(component_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        return _components().disable(component_id)

    @app.get(f"{pref}/components/{{component_id}}/health")
    def components_health(component_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        return _components().health(component_id)

    @app.post(f"{pref}/components/{{component_id}}/remove")
    def components_remove(
        component_id: str, body: dict[str, Any] | None = None, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        body = body or {}
        return _components().remove(component_id, purge=bool(body.get("purge", True)))

    @app.get(f"{pref}/node")
    def node_info(_: None = Depends(require_token)) -> dict[str, Any]:
        h = service.health()
        return {
            "ok": True,
            "service": h.get("service"),
            "version": h.get("version"),
            "mnemosyne_version": h.get("mnemosyne_version"),
            "authority_state": h.get("authority_state"),
            "api_prefix": pref,
            "auth": {
                "node_bearer": "ops_admin",
                "agent_headers": ["X-Agent-Id", "X-Agent-Token"],
                "hard_delete_capability": "MEMORY_HARD_DELETE",
            },
        }

    @app.get(f"{pref}/entities")
    def entities_list(
        limit: int = 50,
        access: AccessContext = Depends(make_access_dep(permission="memory.read", resource="entities.list")),
    ) -> dict[str, Any]:
        from cognitive_memory.domain.entity import list_entities

        items = list_entities(service.db, limit=limit)
        return {"items": items, "count": len(items), "actor": access.actor_id}

    @app.post(f"{pref}/entities")
    def entities_upsert(
        body: dict[str, Any],
        access: AccessContext = Depends(make_access_dep(permission="memory.write", resource="entities.upsert")),
    ) -> dict[str, Any]:
        from cognitive_memory.domain.entity import upsert_entity

        out = upsert_entity(
            service.db,
            entity_id=body.get("id"),
            kind=str(body.get("kind") or "concept"),
            name=str(body.get("name") or ""),
            metadata=dict(body.get("metadata") or {}),
        )
        out["actor"] = access.actor_id
        return out

    @app.get(f"{pref}/events/stream")
    def events_stream(
        request: Request,
        limit: int = 50,
        _: None = Depends(require_token),
    ):
        """SSE 最小面：推送最近 outbox/events（一次性快照 + keep-alive 注释）。"""
        import json as _json
        import time as _time

        def _gen():
            conn = service.db.connect()
            try:
                rows = conn.execute(
                    """
                    SELECT e.event_id, e.event_type, e.payload_json, e.created_at
                    FROM events e
                    ORDER BY e.created_at DESC
                    LIMIT ?
                    """,
                    (max(1, min(200, int(limit))),),
                ).fetchall()
            except Exception:
                rows = []
            for r in reversed(list(rows)):
                try:
                    payload = _json.loads(r["payload_json"] or "{}")
                except Exception:
                    payload = {}
                envelope = {
                    "event_id": r["event_id"],
                    "event_type": r["event_type"],
                    "payload": payload,
                    "created_at": r["created_at"],
                }
                yield f"event: memory\ndata: {_json.dumps(envelope, ensure_ascii=False)}\n\n"
            yield ": keepalive\n\n"
            # short hold so clients see stream semantics without hanging tests forever
            _time.sleep(0.05)
            yield "event: done\ndata: {\"ok\": true}\n\n"

        return StreamingResponse(_gen(), media_type="text/event-stream")



    return app
