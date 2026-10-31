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
| P3 Evidence Objects | **COMPLETED** |
| P4 Truth Maintenance | **COMPLETED** |
| P5 Strategy / Experience | **COMPLETED**（online A/B + 有界 MetaController） |

## 硬约束（仍生效）

- 禁止静默 / LLM Verified
- 禁止生产 DB 回填 / Memory·Bank 重建
- `confirm` ≠ 授权；Claim forget → tombstone 不硬删
- Strategy `ACTIVE` / RL train·deploy / A/B 写入需 Capability Gate（默认 LOCKED）

## P3 Evidence Objects — COMPLETED

- Evidence objects + independence gate + semantic side-path（assistive only）
- Live RO eval 报告；online A/B 指标经 `BANDIT_EXPERIMENT`（`013_ab_v1` + `/ab/*`）

## P4 Truth Maintenance — COMPLETED

- TMS AND/OR + SCC + budget；Schema impact 预览；forget → Claim/Evidence tombstone + TMS OUT

## P5 Strategy / Experience — COMPLETED

- `012` Experience/Strategy/StrategyLog；propensity；门控 offline eval
- 有界 MetaController：`reflect|reevaluate|reevaluate_all|propose_retire|recommend_activate|activate_if_authorized|ab_assign`
- Online A/B：exposures/outcomes/report；retrieve `ab_experiment` opt-in
- **永不**在 A/B 或 MetaController 中静默 ACTIVE / Verified

## 下一步（仓库外）

- 合入 PR #1 → `main`
- 生产解锁 Gate 需外部治理显式操作
