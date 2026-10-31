# Mnemosyne 2.0 — Implementation Status

**更新：** 2026-10-31  
**仓库：** `canyueY/dsh-mnemosyne`（目标）  
**远程 P0 基线：** `c82d47e` docs: complete 2.0 P0 repository audit  
**本地工作区：** `Desktop/桌宠/dsh-mnemosyne/service`（完整 clone 受阻，已用本地 service 树推进）

| 阶段 | 状态 |
|---|---|
| P0 Repository Audit | COMPLETED（远程文档） |
| P0.5 Migration Spike | **COMPLETED** |
| P1 Semantic Contract Freeze | **COMPLETED** |
| P1.5 Governance Closure | **COMPLETED** |
| P2 Claim Vertical Slice | **NEAR COMPLETE**（shadow 回放已通；待远程对齐 / 旧回归全量） |

## P1 Semantic Contract Freeze — COMPLETED

### 完成事项

- 契约文档：TruthValue / RelationResult / Visibility / Verification / Lifecycle / JudgmentTrace / SecurityContext / Evidence provenance / Claim AST / Parser
- 类型与引擎：`judgment/*`、`visibility/*`、`verification/*`、`tracing/*`、`security/context.py`、`claims/lifecycle.py`
- 单元测试：`test_judgment_contracts.py` + `test_p1_visibility_verification.py`（20 passed）

### 测试结果

```text
test_judgment* → 8 passed
test_p1* → 12 passed
```

## P1.5 Governance Closure — COMPLETED

### 完成事项

- 新增 capability `SCHEMA_MUTATION`（默认 LOCKED）
- `schema_governance.authorize_schema_mutation`：`confirm=true` ≠ 授权
- 收口旁路：`assimilate` / `accommodate` / `split` / `merge` / `apply` → LearningProposal + Gate
- API body 增加 `confirm` / `preview`
- 契约：`docs/2.0/contracts/schema-governance.md`
- 测试：`test_schema_gate` / `test_schema_network` 覆盖 confirm 不足与解锁后落盘

### 测试结果

```text
test_schema* → 7 passed
```

### 风险关闭

- R03 Schema mutation 旁路 → **CLOSED**（默认 LOCKED；confirm alone 拒绝）

## P2 Claim Vertical Slice — IN PROGRESS

### 已完成

- Claim 表草案：`docs/2.0/CLAIM_TABLE_DRAFT.md`
- 迁移 `009_claims_v1`：`claims` / `claim_evidence` / `claim_lifecycle_events` / `verification_records`
- `ClaimStore`：propose / same_as / evidence / transition / redirect / visibility / `submit_verified`
- `PersistentVerificationStore` + `POST /claims/{id}/verify`
- API 经 `AccessContext` → `SecurityContext`（Agent bank grant / Node）
- 测试：`test_p2_*` 共 20 passed（含 S1–S14、verify persist、shadow 只写旁路库）
- Shadow：`python -m cognitive_memory.claims.shadow_replay --source-db … --shadow-db …`（源库 RO）

### 验收续跑（2026-10-31 开动）

- 全量 `tests/unit`：**130 passed**（约 7s）
- 生产库 RO shadow（`LOCALAPPDATA/.../memory.db`，limit=100）：
  - scanned=100 / proposed=100 / atoms=26 / unresolved=74 / same_as=0 / errors=[]
  - 旁路库：`docs/2.0/fixtures/shadow_replay/live_shadow.db`（`*.db` 已 gitignore）
  - 报告：`docs/2.0/fixtures/shadow_replay/live_shadow.shadow_report.json`
  - **未写生产库 Claim 表、未 Verified、未回填**

### 未完成（P2 收尾）

- 远程 push / 与 `c82d47e` 对齐（本地 `dsh-mnemosyne` 尚无 commit，fetch 易超时）
- 禁止 LLM Verified / 生产回填（持续约束）

### 下一步

网络恢复后：先 `git fetch` 对齐 `origin/main`（`c82d47e`），再在分支上提交 service 增量并 push；勿用空本地仓覆盖远程。
