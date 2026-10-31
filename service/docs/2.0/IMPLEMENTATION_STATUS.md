# Mnemosyne 2.0 — Implementation Status

**更新：** 2026-10-31  
**仓库：** `canyueY/dsh-mnemosyne`  

> **编号说明：** 下表同时给出 **仓库阶段名** 与 **任务书阶段名**（`10.31更新方案.txt`）。二者不一致时以任务书为准。详见 [PLAN_COMPLETION_AUDIT.md](PLAN_COMPLETION_AUDIT.md)。

## 任务书阶段状态

| 任务书阶段 | 状态 |
|---|---|
| P0 / P0.5 / P1.5 | **COMPLETED** |
| P1 Contract Freeze | **NEAR COMPLETE**（核心契约含字段/算法；摘要契约已加厚） |
| P2 Claim Vertical Slice | **NEAR COMPLETE**（Merge/Split/Relation/S1–S20；生产语料评测外置） |
| P3 Evidence Independence | **COMPLETED**（代码层） |
| P4 Knowledge & TMS | **COMPLETED**（代码层） |
| P5 Experience & Strategy | **COMPLETED**（代码层） |
| P6 Strategy Eval & MetaController | **NEAR COMPLETE**（propensity/overlap fixtures + `rank_candidates` + gated offline eval；真实产线 prop 外置） |
| **P7 Fault Localization & Repair** | **NEAR COMPLETE**（4 类注入 + auto-repair + **可执行 rollback drill**） |
| **P8 Security Hardening（全链路）** | **NEAR COMPLETE**（推理泄漏、grant cache 撤销、删除传播、**跨 Bank Claim opaque 404**） |
| **P9 Migration & Release** | **NEAR COMPLETE（代码层）**（dry-run 门禁 + **scratch trial 写入/一致性/回滚**；生产写仍禁于 complete_rate≈0） |

## 仓库阶段名（易混，勿当任务书）

| 仓库旧称 | 实际含义 | 任务书对应 |
|---|---|---|
| P6 Knowledge | Knowledge 判别式节点 | 任务书 P4 下游 |
| P7 Claim-stack GA | `mnemosyne_claim_ga_check.py` | **不是**任务书 P7 |

## Judgment Supersession

- 已实现 Claim `superseded_at` / `retracted_at` / `expired_at` / `validity` / `last_confirmed_at`；
- 已实现 `claim_decision_records` 与 API；
- 已有时间测试；
- 仍未实现 as-of 历史重建、完整 Replay、下游自动重评。详见 [TEMPORAL_TRACEABILITY.md](TEMPORAL_TRACEABILITY.md)。

## 硬约束（仍生效）

- 禁止静默 / LLM Verified；`confirm` ≠ 授权
- 禁止生产 DB 回填；Claim forget → tombstone
- P9：生产库在 `provenance_complete_rate < 0.01` 时写路径阻断；scratch trial 仅临时库

## 本轮增量（补齐 P6 / P7 rollback / P8 跨 Bank / P9 trial）

- P6：`rank_candidates` + propensity/overlap 夹具测试 + gated offline eval
- P7：`fault/rollback.py` 可执行回滚演练（强制 unverified）
- P8：Agent Claim GET 不以对象 bank 作为 principal default；跨 Bank opaque 404 测试
- P9：`migration/claim_trial.py` scratch 试迁移 → 一致性 → 回滚
