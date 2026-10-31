# Mnemosyne 2.0 — Implementation Status

**更新：** 2026-10-31  
**仓库：** `canyueY/dsh-mnemosyne`  
**main：** `b891230`（PR #1 MERGED）+ post-merge Knowledge/GA 收口

| 阶段 | 状态 |
|---|---|
| P0–P1.5 | **COMPLETED** |
| P2 Claim Vertical Slice | **COMPLETED** |
| P3 Evidence Objects | **COMPLETED** |
| P4 Truth Maintenance | **COMPLETED** |
| P5 Strategy / Experience / A/B / MetaController | **COMPLETED** |
| P6 Knowledge + gated RL/Value | **COMPLETED** |
| P7 Claim-stack GA check | **COMPLETED**（脚本；人工现网签字仍外置） |

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
