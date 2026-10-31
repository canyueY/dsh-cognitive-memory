# -*- coding: utf-8 -*-
"""领域模型与枚举（与 SQLite / API 契约对齐）。"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


class SourceKind(str, Enum):
    USER_STATEMENT = "user_statement"
    DIALOG = "dialog"
    VIDEO_OBSERVATION = "video_observation"
    AGENT_INFERENCE = "agent_inference"
    SYSTEM = "system"
    FEEDBACK = "feedback"


class RelationKind(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVES = "derives"
    SUPERSEDES = "supersedes"
    # P3 时空/时序关联（写入 memory_relations）
    BEFORE = "before"
    AFTER = "after"
    CONTINUES = "continues"
    OCCURRED_IN = "occurred_in"
    LOCATED_AT = "located_at"
    DEPENDS_ON = "depends_on"
    OBSERVED_DURING = "observed_during"


class MemoryRelationIn(BaseModel):
    from_id: str
    to_id: str
    relation: str
    note: str = ""
    valid_from: str | None = None
    valid_until: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChangeDetectIn(BaseModel):
    observation_id: str
    dry_run: bool = True
    apply_l2: bool = False


class ChangePlanBuildIn(BaseModel):
    observation_id: str
    dry_run: bool = True
    persist: bool = True


class ChangePlanApplyIn(BaseModel):
    confirm: bool = False


class ReevaluateIn(BaseModel):
    dry_run: bool = True
    apply_l2: bool = False
    limit: int = 40


class PatternScanIn(BaseModel):
    limit_obs: int = 400
    min_days: int = 3
    min_count: int = 3


class EmotionExtractIn(BaseModel):
    observation_id: str
    shadow_only: bool = True
    write_enabled: bool = False
    min_confidence: float = 0.35


class EmotionPatternScanIn(BaseModel):
    limit_obs: int = 400
    min_days: int = 2
    min_count: int = 2
    persist_summary: bool = False


class ObservationIn(BaseModel):
    source_kind: SourceKind
    content: str
    occurred_at: str | None = None
    producer: str = "dsh"
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_ref: str | None = None
    idempotency_key: str | None = None
    # Identity 附着（E1.6）；缺省由 ingestion 归一化填充
    agent_id: str | None = None
    subject_id: str | None = None
    node_id: str | None = None


class Observation(ObservationIn):
    id: str
    created_at: str


class MemoryProposeIn(BaseModel):
    type: MemoryType = MemoryType.SEMANTIC
    content: str
    source_ids: list[str] = Field(default_factory=list)
    status: MemoryStatus = MemoryStatus.CANDIDATE
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    expires_at: str | None = None
    idempotency_key: str | None = None
    bank_id: str = "personal"


class MemoryUpdateIn(BaseModel):
    content: str | None = None
    status: MemoryStatus | None = None
    metadata: dict[str, Any] | None = None
    confidence: float | None = None
    expires_at: str | None = None
    expected_version: int | None = None


class Memory(BaseModel):
    id: str
    type: MemoryType
    status: MemoryStatus
    content: str
    source_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    last_confirmed_at: str | None = None
    version: int = 1
    confidence: float | None = None
    expires_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    bank_id: str = "personal"


class EvidenceLink(BaseModel):
    memory_id: str
    observation_id: str
    relation: RelationKind = RelationKind.SUPPORTS
    note: str = ""
    confidence: float | None = None
    evidence_kind: str = "observation"
    validation_state: str = "unverified"
    producer: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthorityTransitionIn(BaseModel):
    state: str
    reason: str = ""
    allow_dual: bool = False
    actor: str = "api"


class FeedbackIn(BaseModel):
    memory_id: str
    useful: bool | None = None
    incorrect: bool | None = None
    note: str = ""
    producer: str = "dsh.agent"


class SearchQuery(BaseModel):
    query: str = ""
    types: list[MemoryType] | None = None
    status: list[MemoryStatus] | None = None
    limit: int = 10
    include_evidence: bool = False
    # None → 仅 personal；须显式列入 shared/public
    banks: list[str] | None = None
    # current：降权过期/历史空间；historical：偏历史；any：不时空重排
    mode: str = "current"
    spatiotemporal_rerank: bool = True
    # Mnemosyne P5：按查询情绪信号对带 mnemosyne 的记忆重排
    emotion_rerank: bool = False


class ContextBuildIn(BaseModel):
    query: str
    token_budget: int | None = None
    types: list[MemoryType] | None = None
    limit: int = 12
    mode: str = "current"
    spatiotemporal_rerank: bool = True
    emotion_rerank: bool = False


class ContextBuildOut(BaseModel):
    fragments: list[dict[str, Any]]
    token_estimate: int
    brief: str


class RetrieveIn(BaseModel):
    """Mnemosyne P1：统一检索入口（含触发规划）。"""

    query: str = ""
    force: bool = False
    limit: int = 8
    mode: str = "current"
    spatiotemporal_rerank: bool = True
    emotion_rerank: bool = False
    token_budget: int | None = None
    types: list[MemoryType] | None = None


class TaskCreateIn(BaseModel):
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class Task(BaseModel):
    id: str
    task_type: str
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    attempts: int = 0
    last_error: str = ""
    created_at: str
    updated_at: str


# ---- Mnemosyne 2.0 schema / gate ----


class SchemaDiscoverIn(BaseModel):
    limit_memories: int = 200
    min_cluster: int = 3
    min_similarity: float = 0.22
    persist: bool = True


class ClaimProposeIn(BaseModel):
    text: str
    bank_id: str = "personal"
    source_memory_id: str | None = None
    persist_unresolved: bool = True


class ClaimTransitionIn(BaseModel):
    target_status: str
    reason: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    actor: str = ""


class ClaimEvidenceIn(BaseModel):
    evidence_ref: str
    role: str = "support"
    independent: bool = False


class ClaimRedirectIn(BaseModel):
    target_id: str
    reason: str = "merge"


class ClaimVerifyIn(BaseModel):
    evidence_refs: list[str] = Field(default_factory=list)
    actor: str = ""
    evidence_still_valid: bool = True


class SchemaAssimilateIn(BaseModel):
    memory_ids: list[str] = Field(default_factory=list)
    note: str = ""
    # P1.5：confirm  alone 不足；落盘另需 SCHEMA_MUTATION
    confirm: bool = False
    preview: bool = False


class SchemaAccommodateIn(BaseModel):
    memory_ids: list[str] = Field(default_factory=list)
    counter_note: str = ""
    propose_split: bool = True
    confirm: bool = False
    preview: bool = False


class CognitiveChangePlanIn(BaseModel):
    operation: str = "UPDATE"
    target_schema_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    expected_impact: list[str] = Field(default_factory=list)
    risk_level: str = "MEDIUM"
    approval_required: bool = True
    reason: str = ""


class CognitiveChangePlanApplyIn(BaseModel):
    confirm: bool = False
    preview: bool = False


class CapabilityCheckIn(BaseModel):
    capability: str


class CapabilitySetIn(BaseModel):
    """仅外部治理；Agent 不得调用。"""

    capability: str
    level: str
    enabled: bool | None = None
    actor: str = "external_governance"


class ReflectionIn(BaseModel):
    judgment: str = ""
    schema_ids: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)


class ValueAnalyzeIn(BaseModel):
    intent: str
    stakeholders: list[str] = Field(default_factory=list)
    proposed_action: str = ""
