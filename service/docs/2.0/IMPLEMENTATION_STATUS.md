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
| P3 Evidence Objects | **NEAR COMPLETE**（live eval 已通） |
| P4 Truth Maintenance | **IN PROGRESS**（Justification/SCC/预算传播 + Claim 接线） |

## P2 Claim Vertical Slice — COMPLETED

- Claim 表 `009_claims_v1` + ClaimStore + API + S1–S14 + shadow RO
- JudgmentTrace 接入 propose / same_as / transition / verify / redirect / attach_evidence
- VerificationRecord 持久化；`confirm`/`Verified` 无静默路径
- 全量单测 130→137（含 P3 新增）
- Live shadow：100 样本，atoms 26 / unresolved 74
- PR：https://github.com/canyueY/dsh-mnemosyne/pull/1

## P3 Evidence Objects — IN PROGRESS

### 已完成

- 草案：`docs/2.0/EVIDENCE_OBJECT_DRAFT.md` + `SEMANTIC_SIDEPATH.md`
- 迁移 `010_evidence_objects_v1`
- `EvidenceObjectStore` + Verified 前 independence gate
- Claim attach 物化 `evd_*`；legacy `/evidence` 同步物化
- 语义旁路：`assist_rerank` / `pool_suggest` / `evaluate_assist`；retrieve 默认 `semantic_assist`
- `ClaimStore.semantic_suggest` + `POST /claims/semantic-suggest`（永不 Verified）
- 测试：`test_p3_evidence_objects` + `test_p3_semantic_sidepath`

### 已完成（续）

- Live RO eval：`retrieval/live_eval.py` + 报告  
  `docs/2.0/fixtures/shadow_replay/P3_LIVE_EVAL_REPORT.md`  
  paraphrase 25 查询：fts_recall_avg=0.80，assist_novel_rate=0.12；evidence 50→partial 50，complete=0

### 未完成

- 语义旁路 online A/B 指标（可选）
- 合入 PR #1（需确认）

## P4 Truth Maintenance — IN PROGRESS

### 已完成

- 契约：`docs/2.0/contracts/tms.md` + `TMS_DRAFT.md`
- `tms/`：Justification AND/OR、Tarjan SCC、预算传播、impact preview
- 迁移 `011_tms_v1` + `TmsStore` 持久化
- Claim 接线：verify→support justification；dispute/redirect→invalidate+propagate
- API：`POST /tms/justifications`、`POST /tms/propagate`、`GET /tms/belief/{id}`
- 测试：`test_p4_tms.py`（9 passed）；全量 **153** passed

### 未完成

- Schema impact 全量替换 `analyze_impact` stub
- 删除/tombstone 级联（R17）
- 合入 PR #1

### 下一步

Schema/Evidence 级联与 tombstone；合入 PR；禁止 LLM Verified / 生产回填。
