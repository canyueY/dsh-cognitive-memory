# Mnemosyne 2.0 — Implementation Status

**更新：** 2026-10-31  
**仓库：** `canyueY/dsh-mnemosyne`  

> **任务书对照：** 本文件的阶段编号与 `10.31更新方案.txt` 不完全一致。任务书的 P7（故障定位/修复验证）、P8（安全强化全链路）、P9（迁移/发布）尚未完成；P2 仍缺 Merge/Split 与完整关系。详见 [PLAN_COMPLETION_AUDIT.md](PLAN_COMPLETION_AUDIT.md)。

**main：** `9eb9b93`（P2–P7 + DSH 0.2.1 修复）

| 阶段 | 状态 |
|---|---|
| P0–P1.5 | **COMPLETED** |
| P2 Claim Vertical Slice (repo phase) | **PARTIAL**（Merge/Split/完整 Relation 待补） |
| P3 Evidence Objects | **COMPLETED** |
| P4 Truth Maintenance | **COMPLETED** |
| P5 Strategy / Experience / A/B / MetaController | **COMPLETED** |
| P6 Knowledge + gated RL/Value | **COMPLETED** |
| P7 Claim-stack GA check (repo phase) | **COMPLETED**（仅 GA 脚本；人工现网签字外置） |
| 任务书 P7 Fault Localization & Repair | **MISSING** |
| 任务书 P8 Security Hardening（全链路） | **PARTIAL** |
| 任务书 P9 Migration & Release | **MISSING** |

## 硬约束（仍生效）

- 禁止静默 / LLM Verified
- 禁止生产 DB 回填 / Memory·Bank 重建
- `confirm` ≠ 授权；Claim forget → tombstone 不硬删
- Strategy `ACTIVE` / RL / A/B / Value adapt 需 Capability Gate（默认 LOCKED）
- Knowledge `active` ≠ Claim Verified ≠ Strategy deploy
- 联邦 / 知识市场 → **2.1+**（禁止标完成）

## P6 Knowledge / RL / Value — COMPLETED

- `014_knowledge_v1`：`knowledge_nodes` + `value_soft_prefs`
- 判别式类型：claim/rule/structural/pattern/strategy_knowledge + validator
- Schema demotion → structural/pattern Knowledge
- RL-B：Gate 后 propensity 统计拟合（不 ACTIVE）
- RL-C：`deploy_policy(strategy_id)` → Strategy ACTIVE（独立 Gate）
- V-B 多维压力报告；V-C 软偏好写入（硬约束拒绝）

## P7 GA — COMPLETED（自动化面）

- `scripts/mnemosyne_claim_ga_check.py`：模块导入 + migrations 009–014 + 默认 Gate LOCKED
- 报告：`tmp/mnemosyne_claim_ga_report.json`
- 人工现网签字 / E6.5 试点不在本自动化范围

## API 增量

`/knowledge*` · `/value/adapt` · `/ab/*` · `/strategies*` · `/experiences` · `/meta/schedule` · `/tms/*` · `/claims*`
