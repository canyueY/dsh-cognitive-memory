# Mnemosyne 2.0 — P0 审计文档索引

**审计提交（远程）：** `c82d47e`（P0）  
**日期：** 2026-10-31  
**状态：** P0–P2 **完成**；P3 Evidence 对象进行中（PR #1）。

| 文档 | 内容 |
|---|---|
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | 阶段状态与验收记录 |
| [CLAIM_TABLE_DRAFT.md](CLAIM_TABLE_DRAFT.md) | P2 Claim 表/索引草案 |
| [EVIDENCE_OBJECT_DRAFT.md](EVIDENCE_OBJECT_DRAFT.md) | P3 Evidence 对象草案 |
| [contracts/](contracts/) | P1 语义契约 + schema-governance |
| [P0_REPOSITORY_AUDIT.md](P0_REPOSITORY_AUDIT.md) | 仓库、对象、测试、数据、性能与主要发现 |
| [EXISTING_TO_2_0_MAPPING.md](EXISTING_TO_2_0_MAPPING.md) | 现有模块到 2.0 对象/判定域的复用映射 |
| [GAP_ANALYSIS.md](GAP_ANALYSIS.md) | 六类对象、四个判定域、Truth Maintenance 的差距 |
| [PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md) | 合成基准、生产库容量、队列与候选非功能目标 |
| [RISK_REGISTER.md](RISK_REGISTER.md) | 20 项风险、等级与处理顺序 |
| [MIGRATION_SPIKE_PLAN.md](MIGRATION_SPIKE_PLAN.md) | P0.5 100 条历史 Memory 迁移 spike 方案 |
| [P0_5_MIGRATION_SPIKE_REPORT.md](P0_5_MIGRATION_SPIKE_REPORT.md) | P0.5 只读迁移评估报告 |
| [fixtures/migration_samples/](fixtures/migration_samples/) | 样本 jsonl / 错误 / provenance gaps |

## 审计结论摘要

- 现有 3.0 Node 是可运行的 Observation / Memory / Evidence-link / Bank / Governance / Runtime 基础。
- **Claim 全链路缺失**：没有 AST、Parser、Relation、Verification、State Machine。
- **Evidence 不是独立对象**：`memory_evidence` 只是 Memory↔Observation 链接。
- **Schema 层是启发式实验层**：不能直接作为 2.0 Knowledge/Claim。
- ~~Schema mutation 治理旁路~~ → P1.5 已收口为 LearningProposal + `SCHEMA_MUTATION`。
- P1 已补 Claim/Visibility/Verification/TruthValue 契约测试；旧 122 回归仍只证明 3.0 能力。
- P2 Claim 纵向切片已合入分支；P3 起独立 Evidence 对象（`memory_evidence` 仅过渡）。

## 建议下一步

1. P3：Verified 前强制 independence gate；语义检索旁路评估；
2. 禁止 LLM Verified、禁止生产回填；
3. 不同时铺开 Knowledge/Strategy/MetaController / TMS（P4）。
