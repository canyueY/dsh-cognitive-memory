# Mnemosyne 2.0 — 差距分析（P0）

**审计提交：** `589c694`  
**对照目标：** Mnemosyne 2.0 总体设计方案（六类对象、四个判定域、Truth Maintenance、P2 Claim 纵向切片）

## 1. 总差距

| 领域 | 现有状态 | 2.0 目标 | 差距等级 |
|---|---|---|---|
| Memory / Observation | Implemented | Memory | 低 |
| Evidence | 证据链接，非对象 | Evidence + provenance + independence | 高 |
| Claim | 不存在 | AST/parser/relation/verification/state | 极高 |
| Knowledge | 启发式 Schema | 判别式 Knowledge + validator | 高 |
| Experience | episodic memory 近似 | first-class Experience | 中 |
| Strategy | 不存在 | Strategy/StrategyLog/离线评估 | 极高 |
| same_as | 不存在 | 命题同一性 | 极高 |
| visible | 请求级权限 | 对象/字段/Justification 可见性 | 高 |
| verified | 状态字段/启发式 | VerificationRecord + scope | 极高 |
| unknown | 无类型 | TruthValue + reason codes | 高 |
| Truth Maintenance | 邻居计数 | AND/OR + SCC + 增量传播 | 极高 |
| Trace | events/outbox | JudgmentTrace/DecisionRecord | 高 |
| Migration | Memory staging | Claim/Provenance 迁移 | 高 |

---

## 2. 对象层差距

### 2.1 Memory

已有，但：

- `metadata` 是自由 JSON，没有统一 `SecurityContext`；
- 没有 Working Memory 容量/淘汰策略；
- 没有与 Claim 的关系。

**P2 决策：** 保留；增加 `bank_id` 之外的 owner/purpose/classification 由安全契约另行补齐。

### 2.2 Evidence

现状是 `memory_evidence` 关联表：

```text
memory_id + observation_id + relation
```

缺：

- `evidence_id`；
- `source_fingerprint`；
- `derivation_chain` / `root_source_id`；
- `independence_key`；
- 证据级 `security_context`；
- 反证（生产数据全部 `supports`）；
- 独立性算法与验证状态语义。

**P2 决策：** 新增独立 Evidence 对象；`memory_evidence` 仅作为过渡；不要直接把 `observation_id` 当 Evidence ID。

### 2.3 Claim

完全缺失。

缺：

- `ClaimAST v1`；
- parser；
- `RelationResult`；
- `VisibilityResult`；
- `VerificationResult`；
- 生命周期状态机；
- 合并/拆分/redirect；
- Claim API 与测试。

**P2 决策：** 这是唯一需要从零开始的主对象。

### 2.4 Knowledge

`cognitive_schemas` 有 `type/state/confidence/payload`，但：

- 不是 Claim 派生；
- 没有判别式类型；
- 没有独立 Validator；
- 没有 ClaimKnowledge/RuleKnowledge/StructuralKnowledge/PatternKnowledge/StrategyKnowledge；
- 没有 scope/security；
- 置信度是硬编码 delta。

**P4 决策：** 在 Claim 稳定后，再将 Schema 降为 `StructuralKnowledge` 或 `PatternKnowledge` 的下游。  
**P6 进展（2026-10-31）：** `knowledge_nodes` 判别式类型 + validator + Schema demotion API 已落地；Knowledge.active ≠ Claim Verified。

### 2.5 Experience / Strategy

只有 episodic memory/events；无：

- `Experience` 对象；
- `Strategy` / `StrategyLog`；
- propensity/overlap；
- 离线评估。

**P5+ 决策：** 不在 P2 实现；先保留 events 作为原始素材。  
**P5 进展（2026-10-31）：** Experience/Strategy/StrategyLog + propensity + 门控 offline eval + 有界 MetaController + 门控 online A/B 已落地；online RL 权重更新 / 自动 ACTIVE 仍禁止。

---

## 3. 四个判定域差距

### 3.1 same_as

缺失。现有只有：

- `memory_relations.relation`（字符串）；
- `schema_network` 的 `network_links`；
- 文本相似度/检索。

没有 Claim AST，因此不能定义：

- 实体/谓词/参数/scope 等价；
- 否定/时间/条件；
- 自反/对称/传递；
- `candidate_relation` / `decision` / `final_relation`。

**P1 必须冻结。**

### 3.2 visible

已有：

- Node token / Agent token；
- grants（permissions/banks/expiry/revoke）；
- `bank_id` 检索过滤；
- `policy`（store/forward/train/retention）；
- capability gate。

缺：

- 对象级 `SecurityContext`；
- `purpose_constraints`；
- Justification 计算；
- OR 替代依据；
- 字段级 `partial`；
- 推理泄漏；
- redirect 权限保持；
- fail-closed 统一返回。

**P1/P4 必须补齐。**

### 3.3 verified

已有：

- `memory_evidence.validation_state`（unverified/supports/contradicts/revoked）；
- `confidence`；
- `change_plan.verification_status`。

缺：

- `VerificationRecord`；
- verification scope / valid_until / policy_version；
- `verified/not_verified/insufficient/disputed/expired/revalidate_required`；
- 与 Claim 状态机的映射；
- 反证触发降级；
- 模型不能直接设置 verified 的强制约束。

**P2 必须实现。**

### 3.4 unknown

缺：

- `TruthValue`；
- 三值逻辑；
- `missing_information` / `insufficient_evidence` / `conflicting_evidence` / `unsupported_semantics`；
- 对外脱敏；
- `not_found` / `not_authorized` 的区分。

现有 `NO_MATCH` 只是检索状态，`metacognition` 的 `uncertainty` 只是字符串。

**P1 必须冻结，P2 实现。**

---

## 4. 运行与治理差距

### 4.1 Truth Maintenance

现有：

- `schema_network.impact_of_schema`：证据数 + 邻居 + plan 数；
- `metacognition.analyze_impact`：读取 `relations` 生成重评列表。

缺：

- 独立 Justification；
- AND/OR 语义；
- 替代依据；
- 依赖边类型；
- SCC/循环；
- 增量传播；
- 预算/终止条件。

### 4.2 Schema mutation 治理

现有直接路径：

- `assimilate_schema`：直接 `update_cognitive_schema`，置信度 +0.02/条；
- `accommodate_schema`：直接更新，并可选建 plan；
- `split_schema` / `merge_schemas`：`confirm=true` 直接执行，不经过 Authority；
- `schemas_assimilate` / `schemas_accommodate` API 只要求 Node token。

这与 2.0 的“所有长期认知变化经 LearningProposal / Governance”不一致。**P1/P2 必须收口。**

### 4.3 Trace

现有 events/outbox/tasks 是**运行事件**，不是判断 trace。

缺：

- `trace_id`；
- `JudgmentTrace`；
- `DecisionRecord`；
- `rule_version` / `algorithm_version`；
- `machine_verifiable_reason`；
- `trace_completeness`；
- replay。

### 4.4 对象级安全

`memories` 有 `bank_id`，但：

- `cognitive_schemas` 无 bank/owner/classification；
- `memory_evidence` 无 security context；
- `memory_relations` 无 security context；
- Claim 尚不存在。

这会导致「同一个 Bank 的 Schema 被另一个 Agent 看到」或「跨 Bank 证据派生 Claim」的潜在漏洞。

---

## 5. 数据与迁移差距

现有数据：

- 58,186 memories；
- 57,169 evidence 链接；
- 57,163 unverified；
- 8 个 ontology schema；
- 0 个 change plan；
- 0 个 feedback；
- 0 个 agent grant。

迁移挑战：

- 历史 Memory 没有 Claim AST；
- 没有 source fingerprint/derivation；
- 没有 Claim 级权限；
- 没有 `provenance_unknown` 字段；
- 不能自动把旧 Memory 标为 Verified。

**P0.5 必须先做 100 条分层迁移 spike。**

---

## 6. P2 最小范围建议

P2 只做以下闭环：

```text
Memory / Observation
  → Evidence
  → Claim Candidate
  → Claim Persistence
  → Claim Relation
  → Claim Verification
  → Claim Lifecycle
  → Retrieval
  → Trace
```

不在 P2 做：

- Knowledge 全类型；
- Truth Maintenance 全图；
- Strategy/MetaController；
- Pattern 归纳；
- 多模态；
- 自动修复。

P2 验收必须覆盖：

- 重复、同义、否定、条件、时间；
- 支持/反驳；
- 冲突/Unknown；
- 权限拒绝；
- 替代 Justification；
- Verified 降级；
- parser 升级；
- 合并/redirect；
- 追溯与回放。

---

## 7. 结论

| 问题 | 答案 |
|---|---|
| 能否复用现有 Memory？ | 能，保留 |
| 能否复用现有 Schema 作为 Claim？ | 不能 |
| 能否复用 Change Plan？ | 能，但需收口为 LearningProposal |
| 能否复用 Agent grants？ | 能，但需扩展到对象级 |
| 是否需要重写整个仓库？ | 不需要 |
| P2 最大风险 | Claim/Evidence 契约未冻结，Schema 先行动 |
| 正确顺序 | P0 审计 → P0.5 迁移 spike → P1 契约 → P2 Claim 纵向切片 |
