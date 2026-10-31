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
| P3 Evidence Objects | **IN PROGRESS**（对象 + 语义旁路已接通） |

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

### 下一步

合入 PR #1；P4 TMS 另立项；禁止 LLM Verified / 生产回填。
