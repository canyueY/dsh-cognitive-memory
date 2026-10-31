# Mnemosyne 2.0 — P0 风险登记册

**审计提交：** `589c694`  
**评分：** Critical / High / Medium / Low  
**用途：** P0 审计附件；不是最终架构决策记录。

| ID | 风险 | 等级 | 证据 | 影响 | 建议动作 |
|---|---|---|---|---|---|
| R01 | Claim 全链路缺失 | Critical | 无 `claims` 表、无 AST/parser/relation/state；测试中无 Claim | P2 无法开始；2.0 核心能力不存在 | P1 冻结 AST/Result/State；P2 单独立项 |
| R02 | Evidence 只是 Memory↔Observation 链接 | Critical | `memory_evidence` 字段；57,169 条链接 | 无法计算独立性/派生链/Justification/证据级权限 | 新增 Evidence 对象；保留旧链接过渡 |
| R03 | Schema mutation 绕过统一治理 | Critical | ~~direct assimilate/accommodate~~ → P1.5 CLOSED：`SCHEMA_MUTATION` + LearningProposal；confirm alone 拒绝 | 高风险结构变更可未经审批落盘 | **CLOSED**（2026-10-31） |
| R04 | 对象级 SecurityContext 缺失 | High | `memories` 只有 `bank_id`；schemas/relations/evidence 无统一 owner/purpose/classification | 跨 Agent/Bank/用途泄漏；无法实现 `visible` | 增加对象级 security；Claim 前先定义 scope |
| R05 | VerificationRecord 缺失 | High | 只有 `validation_state`、`confidence`、`verification_status` 字段 | 无法证明 verified；无法绑定范围/有效期/策略版本 | P1 冻结 VerificationResult；P2 实现 |
| R06 | Schema 发现/演化是启发式 | High | `schema_discovery` token Jaccard；`schema_evolution` 固定 delta | 误聚类、误合并、置信度虚高 | 只作为 candidate；P4 前不自动 ACTIVE |
| R07 | Truth Maintenance 缺失 | High | ~~仅计数 stub~~ → P4 引擎 + Schema TMS impact 已接 | 下游依赖无法可靠失效/恢复 | **CLOSED**（2026-10-31；无自动覆盖） |
| R08 | 无 JudgmentTrace/DecisionRecord | High | 搜索无 trace_id/DecisionRecord | 无法解释 Claim 状态、无法回放/审计 | P1 定义 Trace；P2 强制记录 |
| R09 | 历史数据 57k evidence 基本 unverified | High | 57,163 unverified / 6 supports | 迁移会把历史噪声带入 Claim；不能自动 Verified | P0.5 100 条分层 spike；provenance_unknown |
| R10 | Schema 无 Bank/权限范围 | High | `cognitive_schemas` 无 `bank_id`/security | 跨 Bank 知识泄漏 | 与 R04 一起修 |
| R11 | Claim/Schema 无合并/重定向协议 | High | 无 Claim 表；Schema split/merge 只做 `network_links` | 旧 ID 失效、引用断裂、权限绕过 | P1 冻结 merge/split/redirect |
| R12 | Semantic 检索未接入主路径 | Medium | ~~仅可选~~ → P3 `semantic_assist` 旁路 + live eval + 门控 A/B | 语义召回能力被高估 | **CLOSED**（assistive only；不替代证据） |
| R13 | `SearchQuery` 无 domain 过滤 | Medium | `SearchQuery` 字段无 `domain` | 音乐/领域闸门无法在 Node 执行 | 增加 domain filter 或统一 metadata policy |
| R14 | 队列积压与存储增长 | Medium | 2,538 pending outbox；3,194 pending tasks；548 MB | 延迟、磁盘增长、worker 阻塞 | P0 补排空/retention/监控 |
| R15 | 测试覆盖与 2.0 不匹配 | High | 122 tests，但无 Claim/Visibility/Verification/TMS | 回归通过会制造“已完成”错觉 | P1 建 Claim 测试矩阵；P2 门禁 |
| R16 | 文档与实现存在张力 | Medium | ~~矩阵超前~~ → IMPLEMENTATION_STATUS / docs/2.0 README 与 P0–P7 对齐 | 对外误导、错误规划 | **CLOSED**（2026-10-31） |
| R17 | 无对象级删除传播 | High | ~~仅 forget~~ → `cascade_memory_invalidated`：Claim superseded tombstone + Evidence revoked + TMS | 删除 Memory 后 Claim/Knowledge 引用悬挂 | **CLOSED**（Claim 行保留审计；非硬删） |
| R18 | Parser 无实现，LLM 解析误差未知 | High | 无 parser；未来需 LLM/规则 | 低质量 Claim 污染 | P1 定 Parser 契约；P2 先小样本 |
| R19 | 时间语义仅有 `occurred_at`/`expires_at` | Medium | `observations`/`memories` 字段 | 过去/现在/未来混淆 | P1 冻结 temporal scope |
| R20 | 并发/事务边界分散 | Medium | SQLite service 事务散落 | Schema 更新与 Claim 写入竞态 | P1 定义事务边界/乐观锁 |

---

## 优先处理顺序

1. **R01/R02**：Claim + Evidence；没有它们，2.0 无法开始。
2. **R03/R04/R10**：治理与对象级权限；否则新 Claim 会继承旧漏洞。
3. **R05/R08/R18**：Verification/Parser/Trace；P2 的质量门。
4. **R07/R11/R17**：Truth Maintenance、合并/删除传播；P4 前必须定。
5. **R09/R15**：历史迁移与测试矩阵；P0.5/P1 必须完成。
6. **R12/R13/R14/R16/R19/R20**：体验、性能、文档与并发，随阶段补齐。

---

## 风险接受规则

- 不允许把 R01/R02/R03/R04 标为“P2 后续处理”；它们是 P2 的前置条件。
- 不允许在 R05/R08 未实现时宣称 Claim 已验证。
- 不允许在 R09 未做 spike 时批量迁移历史数据。
- 不允许在 R15 未建立测试矩阵时进入 P2 开发。
