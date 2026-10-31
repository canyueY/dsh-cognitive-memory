# Mnemosyne 2.0 — Implementation Status

**更新：** 2026-10-31  
**仓库：** `canyueY/dsh-mnemosyne`  

> **编号说明：** 下表同时给出 **仓库阶段名** 与 **任务书阶段名**（`10.31更新方案.txt`）。二者不一致时以任务书为准。详见 [PLAN_COMPLETION_AUDIT.md](PLAN_COMPLETION_AUDIT.md)。

## 任务书阶段状态

| 任务书阶段 | 状态 |
|---|---|
| P0 / P0.5 / P1.5 | **COMPLETED** |
| P1 Contract Freeze | **NEAR COMPLETE**（核心契约已补字段/算法冻结；其余摘要契约可继续加厚） |
| P2 Claim Vertical Slice | **NEAR COMPLETE**（Merge/Split/Relation/S1–S20 已补；并发+幂等已测） |
| P3 Evidence Independence | **COMPLETED**（代码层） |
| P4 Knowledge & TMS | **COMPLETED**（代码层） |
| P5 Experience & Strategy | **COMPLETED**（代码层） |
| P6 Strategy Eval & MetaController | **PARTIAL**（真实 prop 数据不足） |
| **P7 Fault Localization & Repair** | **NEAR COMPLETE**（`fault/` pipeline + 4 类注入 + auto-repair；回滚仍为记录型演练） |
| **P8 Security Hardening（全链路）** | **NEAR COMPLETE**（推理泄漏守卫、grant cache 即时撤销、Memory→…→cache 删除传播） |
| **P9 Migration & Release** | **PARTIAL**（provenance 门禁 dry-run 已落地；**禁止**在 complete_rate=0 时写生产） |

## 仓库阶段名（易混，勿当任务书）

| 仓库旧称 | 实际含义 | 任务书对应 |
|---|---|---|
| P6 Knowledge | Knowledge 判别式节点 | 任务书 P4 下游 |
| P7 Claim-stack GA | `mnemosyne_claim_ga_check.py` | **不是**任务书 P7 |

## Judgment Supersession

- 已实现 Claim `superseded_at` / `retracted_at` / `expired_at` / `validity` / `last_confirmed_at`；
- 已实现 `claim_decision_records` 与 API；
- 已有 7 项时间测试；
- 仍未实现 as-of 历史重建、完整 Replay、下游自动重评。详见 [TEMPORAL_TRACEABILITY.md](TEMPORAL_TRACEABILITY.md)。

## 硬约束（仍生效）

- 禁止静默 / LLM Verified；`confirm` ≠ 授权
- 禁止生产 DB 回填；Claim forget → tombstone
- P9：`provenance_complete_rate < 0.01` → 写路径阻断；仅 dry-run / Unresolved 策略

## 本轮增量（任务书 P7 加深 + P8 + P9 dry-run + P1 契约）

- P7：`fault/inject.py` + `fault/repair.py`；四类注入（redirect tombstone / verified无证据 / silent verified / lifecycle mismatch）+ auto_repair 全链路 stage
- P8：`security/disclosure.py` 推理泄漏守卫；`identity/grant_cache.py` 撤销即失效；`tms/tombstone.py` 扩展 Knowledge/Strategy/Experience/cache 传播
- P9：`migration/claim_dry_run.py` provenance 门禁只读计划（never Verified、never invent sources）
- P1：加厚 visibility / security / relation / verification / evidence-provenance 契约字段与算法
