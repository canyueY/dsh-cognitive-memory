# Mnemosyne 2.0 — 审计与实现文档索引

**状态：** P0–P7 Claim 主线 **COMPLETED**（已合入 `main`；联邦/市场裁切 2.1+）  
**日期：** 2026-10-31

| 文档 | 内容 |
|---|---|
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | 阶段状态与验收记录 |
| [KNOWLEDGE_DRAFT.md](KNOWLEDGE_DRAFT.md) | Knowledge 判别式类型 |
| [STRATEGY_DRAFT.md](STRATEGY_DRAFT.md) | Experience / Strategy / A/B |
| [TMS_DRAFT.md](TMS_DRAFT.md) | Truth Maintenance |
| [EVIDENCE_OBJECT_DRAFT.md](EVIDENCE_OBJECT_DRAFT.md) | Evidence 对象 |
| [CLAIM_TABLE_DRAFT.md](CLAIM_TABLE_DRAFT.md) | Claim 表草案 |
| [contracts/](contracts/) | 语义契约（含 knowledge/strategy/tms） |
| [P0_REPOSITORY_AUDIT.md](P0_REPOSITORY_AUDIT.md) | P0 仓库审计（历史快照） |
| [POST_AUDIT_DELTA.md](POST_AUDIT_DELTA.md) | P0 历史快照 → 当前 `main`（P2–P7 + DSH 0.2.1）状态增量 |
| [HOST_E2E_VERIFICATION.md](HOST_E2E_VERIFICATION.md) | 真实 `dsh-tools@0.2.1-rc.5` ToolRuntime 宿主端到端验证 |
| [PLAN_COMPLETION_AUDIT.md](PLAN_COMPLETION_AUDIT.md) | 对照 `10.31更新方案.txt` 的阶段完成情况与缺口 |
| [GAP_ANALYSIS.md](GAP_ANALYSIS.md) | 差距分析（历史+进展注记） |
| [RISK_REGISTER.md](RISK_REGISTER.md) | 风险登记 |

## 结论

- Claim / Evidence / TMS / Strategy / Knowledge 主对象已落地。
- Capability Gate 默认 LOCKED；无静默 Verified / 无静默 ACTIVE。
- GA 自动化：`scripts/mnemosyne_claim_ga_check.py`
- **不做：** 跨 Node 联邦、知识市场、online RL 权重自更新。
