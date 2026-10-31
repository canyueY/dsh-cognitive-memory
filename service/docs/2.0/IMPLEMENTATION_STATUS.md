# Mnemosyne 2.0 — Implementation Status

**更新：** 2026-10-31  
**仓库：** `canyueY/dsh-mnemosyne`  

> **编号说明：** 下表同时给出 **仓库阶段名** 与 **任务书阶段名**（`10.31更新方案.txt`）。二者不一致时以任务书为准。详见 [PLAN_COMPLETION_AUDIT.md](PLAN_COMPLETION_AUDIT.md)。

## 任务书阶段状态

| 任务书阶段 | 状态 |
|---|---|
| P0 / P0.5 / P1.5 | **COMPLETED** |
| P1 Contract Freeze | **PARTIAL**（契约仍偏摘要） |
| P2 Claim Vertical Slice | **NEAR COMPLETE**（Merge/Split/Relation/S1–S20 已补；并发+幂等已测） |
| P3 Evidence Independence | **COMPLETED**（代码层） |
| P4 Knowledge & TMS | **COMPLETED**（代码层） |
| P5 Experience & Strategy | **COMPLETED**（代码层） |
| P6 Strategy Eval & MetaController | **PARTIAL**（真实 prop 数据不足） |
| **P7 Fault Localization & Repair** | **IN PROGRESS**（`fault/` + `015_fault_v1` + pipeline；非 GA 脚本） |
| P8 Security Hardening（全链路） | **PARTIAL** |
| P9 Migration & Release | **MISSING**（P0.5 provenance_complete=0 → 禁止直接迁移） |

## 仓库阶段名（易混，勿当任务书）

| 仓库旧称 | 实际含义 | 任务书对应 |
|---|---|---|
| P6 Knowledge | Knowledge 判别式节点 | 任务书 P4 下游 |
| P7 Claim-stack GA | `mnemosyne_claim_ga_check.py` | **不是**任务书 P7 |

## 硬约束（仍生效）

- 禁止静默 / LLM Verified；`confirm` ≠ 授权
- 禁止生产 DB 回填；Claim forget → tombstone
- P9 前必须先解决 provenance 完整率 = 0 的迁移策略

## 本轮增量（任务书 P2 + P7）

- Claim `merge` / `split` / `relate` / `parse` API
- Relation：`same_as` + `contradicts` + `qualifies` + `supports`
- Claim 矩阵 **S1–S20**（含并发提出、重复请求）
- `fault/`：Invariant → Earliest → Diff Trace → Min Repro → Root Cause → Patch → Targeted/Regression/Replay/Rollback → Governance
