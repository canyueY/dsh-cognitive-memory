# Mnemosyne 2.0 — P0 审计文档索引

**审计提交：** `589c694`  
**日期：** 2026-10-31  
**状态：** P0 Repository Audit 已完成；P1 契约尚未冻结，P2 尚未开始。

| 文档 | 内容 |
|---|---|
| [P0_REPOSITORY_AUDIT.md](P0_REPOSITORY_AUDIT.md) | 仓库、对象、测试、数据、性能与主要发现 |
| [EXISTING_TO_2_0_MAPPING.md](EXISTING_TO_2_0_MAPPING.md) | 现有模块到 2.0 对象/判定域的复用映射 |
| [GAP_ANALYSIS.md](GAP_ANALYSIS.md) | 六类对象、四个判定域、Truth Maintenance 的差距 |
| [PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md) | 合成基准、生产库容量、队列与候选非功能目标 |
| [RISK_REGISTER.md](RISK_REGISTER.md) | 20 项风险、等级与处理顺序 |
| [MIGRATION_SPIKE_PLAN.md](MIGRATION_SPIKE_PLAN.md) | P0.5 100 条历史 Memory 迁移 spike 方案 |

## 审计结论摘要

- 现有 3.0 Node 是可运行的 Observation / Memory / Evidence-link / Bank / Governance / Runtime 基础。
- **Claim 全链路缺失**：没有 AST、Parser、Relation、Verification、State Machine。
- **Evidence 不是独立对象**：`memory_evidence` 只是 Memory↔Observation 链接。
- **Schema 层是启发式实验层**：不能直接作为 2.0 Knowledge/Claim。
- **Schema mutation 存在治理旁路**：direct assimilate/accommodate；split/merge 可在 `confirm=true` 下直接执行。
- 122 个测试通过，但没有 Claim/Visibility/Verification/TMS 测试。
- 122 个测试只证明旧能力回归，不证明 2.0 已完成。

## 建议下一步

1. 执行 [MIGRATION_SPIKE_PLAN.md](MIGRATION_SPIKE_PLAN.md) 的 100 条样本；
2. 冻结 P1 契约：Claim AST、RelationResult、VisibilityResult、VerificationResult、TruthValue；
3. 修正 Schema mutation 的治理旁路；
4. 只做 P2 Claim 纵向切片，不同时铺开 Knowledge/Strategy/MetaController。
