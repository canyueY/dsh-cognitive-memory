# Mnemosyne 2.0 — Implementation Status

**更新：** 2026-10-31  
**仓库：** `canyueY/dsh-mnemosyne`  
**基线：** `c82d47e` → 分支 `feat/p2-claim-vertical-slice`（PR #1）

| 阶段 | 状态 |
|---|---|
| P0 Repository Audit | COMPLETED |
| P0.5 Migration Spike | **COMPLETED** |
| P1 Semantic Contract Freeze | **COMPLETED** |
| P1.5 Governance Closure | **COMPLETED** |
| P2 Claim Vertical Slice | **COMPLETED** |
| P3 Evidence Objects | **IN PROGRESS**（对象表 + store + API 首切片） |

## P2 Claim Vertical Slice — COMPLETED

- Claim 表 `009_claims_v1` + ClaimStore + API + S1–S14 + shadow RO
- JudgmentTrace 接入 propose / same_as / transition / verify / redirect / attach_evidence
- VerificationRecord 持久化；`confirm`/`Verified` 无静默路径
- 全量单测 130→137（含 P3 新增）
- Live shadow：100 样本，atoms 26 / unresolved 74
- PR：https://github.com/canyueY/dsh-mnemosyne/pull/1

## P3 Evidence Objects — IN PROGRESS

### 已完成

- 草案：`docs/2.0/EVIDENCE_OBJECT_DRAFT.md`
- 迁移 `010_evidence_objects_v1`
- `EvidenceObjectStore`：create / from_observation / legacy map / fingerprint dedupe / independence_key
- Claim attach 物化 `evd_*`；legacy `/evidence` 同步物化
- API：`POST /evidences`、`GET /evidences/{id}`、`POST /evidences/independence`
- 测试：`test_p3_evidence_objects.py`（7 passed）
- 约束：不伪造 provenance；不自动 `complete`

### 未完成

- Evidence→Verification 独立性硬门（提交 Verified 前强制 independence check）
- 语义检索主路径评估（不替代证据）
- 生产库只读 Evidence shadow 抽样

### 下一步

Verified 路径接入 independence gate；语义检索旁路实验；禁止 LLM Verified / 生产回填。
