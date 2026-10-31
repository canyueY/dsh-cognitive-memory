# Mnemosyne 2.0 — P0 仓库审计报告

**审计对象：** `dsh-mnemosyne` 仓库中的 `service/` Node/Core，以及根目录 DSH 适配层  
**审计提交：** `589c694`（`docs: add 3.0 algorithm stack analysis`）  
**软件版本：** `3.0.0`  
**审计日期：** 2026-10-31（Asia/Shanghai）  
**审计性质：** P0 Repository Audit；只读检查、测试运行、合成基准与只读数据盘点  
**结论状态：** 现有系统可作为 2.0 的运行时与记忆基础；**不能把现有能力视为 2.0 Claim 架构已经实现**

---

## 1. 审计方法

本次审计使用四类证据：

1. **静态代码审计**：对象模型、SQLite schema、API 路由、核心 service、governance、retrieval、cognition 模块。
2. **测试执行**：`pytest -q`，122 个测试全部通过。
3. **最小 readiness 套件**：`scripts/mnemosyne_readiness_suite.py`，G1/G3/G4/G5/G6/G7 等 smoke gate 通过。
4. **只读数据盘点与合成基准**：对当前 Memory Bank 做只读聚合统计；在临时库上用 2,000 条合成记忆测 in-process 基线。

> 本报告中的 **Implemented / Partial / Missing / Stub** 是工程状态，不是 2.0 设计目标。  
> 只读盘点不读取记忆正文，只统计表、状态、数量与类型。

---

## 2. 总体结论

现有 3.0 Node 是一个可运行的：

- Observation / Memory / Evidence-link 记忆系统；
- Memory Bank / 版本 / 检索 / 关系 / 反馈系统；
- Schema / Change Plan / Schema Network 的**实验性认知层**；
- Identity / Agent Grant / Authority / Policy 的**请求级治理层**；
- 带 Outbox / Task / Event 的异步运行时。

但它**不是** 2.0 设计方案所定义的 Claim 中心系统：

- 没有 Claim AST、Claim Parser、Claim 持久化；
- 没有 `same_as`、`verified`、`unknown` 的独立判定类型；
- 没有 first-class Evidence 对象、独立性算法、Justification/Truth Maintenance；
- 没有 Judgment Trace、VerificationRecord、Experience/Strategy 对象；
- Schema 层是启发式记忆聚类与图式操作，不是经过独立验证的 Knowledge 体系。

### 一句话判断

> **3.0 已把“记忆”和“请求级治理”做成了基础设施；2.0 的“Claim 认知判断”仍基本从零开始。**

---

## 3. 仓库与测试基线

| 项 | 结果 |
|---|---|
| Python 源文件 | 94 个 |
| Python 源码行数 | 13,090 行 |
| 测试文件 | 33 个 `.py`（目录内共 68 个文件，含缓存） |
| 测试行数 | 3,109 行 |
| 测试结果 | **122 passed in 9.19s** |
| readiness suite | 各 smoke gate ok，`errors: []` |
| API | FastAPI `/api/v1`，约 70 条路由 |
| 存储 | SQLite + FTS5 + WAL |
| 默认 Bank | `%LOCALAPPDATA%\Mnemosyne Memory Bank` |

### 测试覆盖的重心

现有测试主要集中在：

- Memory CRUD、版本冲突、FTS 检索；
- Observation、Evidence link、provenance 字段；
- Bank 隔离、Agent grants、Authority 状态机；
- Change Plan、Schema Discovery/Assimilate/Accommodate、Schema Network；
- Retrieval planner/pipeline；
- Migration staging、dedupe、rollback；
- Emotion shadow、spatiotemporal；
- Component Manager、MCP、Node CLI。

### 测试缺口

没有发现针对以下 2.0 核心对象的测试：

- Claim AST / parser / relation；
- `same_as` / `visible` / `verified` / `unknown` 判定；
- Justification / Truth Maintenance；
- JudgmentTrace / DecisionRecord；
- Claim 合并、拆分、redirect；
- 权限替代 Justification 与推理泄漏。

因此，**122 个测试通过不能作为 2.0 Claim 架构的完成证据**。

---

## 4. 现有 SQLite 对象与数据模型

主要表：

```text
observations
memories
memory_versions
memory_evidence
memory_relations
memory_feedback
events
outbox
inbox
tasks
idempotency_keys
change_candidates
change_plans
cognitive_schemas
schema_versions
cognitive_change_plans
capability_permissions
capability_audit
identity_principals
memory_banks
authority_state
agent_grants
agent_audit
```

### 关键判断

| 2.0 对象 | 现有实现 | 状态 |
|---|---|---|
| Memory | `memories` + `memory_versions` + `bank_id` | **Implemented** |
| Evidence | `memory_evidence` 是“Memory ↔ Observation”的关联表，不是独立 Evidence 实体 | **Partial** |
| Claim | 无 `claims` 表、无 AST、无 parser、无 relation | **Missing** |
| Knowledge | `cognitive_schemas` / `schema_versions`，但无判别式 Knowledge 类型 | **Partial** |
| Experience | 有 episodic memory / events，但没有 first-class Experience | **Partial** |
| Strategy | 无 Strategy / StrategyLog 表或对象 | **Missing** |

### 4.1 Evidence 的实际形态

`memory_evidence` 字段：

```text
memory_id
observation_id
relation
note
confidence
evidence_kind
validation_state
producer
metadata_json
```

它本质上表达：

```text
Memory --supports/contradicts--> Observation
```

而不是：

```text
Evidence {
  evidence_id, source, provenance_chain, independence, ...
}
```

所以当前系统可以做“证据链接”和“验证状态字段”，但不能直接计算：

- 同一根来源的派生链；
- 证据独立性；
- 替代 Justification；
- 证据级权限；
- Claim 级可见性。

---

## 5. 当前 Memory Bank 数据盘点

只读聚合结果（审计时点）：

| 指标 | 数值 |
|---|---:|
| `memory.db` 文件大小 | 574,582,784 bytes（约 548 MB） |
| observations | 41,870 |
| memories | 58,186 |
| memory_versions | 58,159 |
| memory_evidence | 57,169 |
| memory_relations | 446 |
| memory_feedback | 0 |
| cognitive_schemas | 8 |
| schema_versions | 36 |
| cognitive_change_plans | 0 |
| change_plans | 0 |
| agent_grants | 0 |
| events | 100,475 |
| outbox | 100,475（pending 2,538，delivered 97,937） |
| tasks | 98,932（pending 3,194，done 95,738） |
| 带 `metadata.domain=music` 的 observations | 1,102 |
| 音乐相关 memories | 约 990–1,017 |

### 5.1 记忆类型与状态

| 类型 | 状态 | 数量 |
|---|---|---:|
| episodic | candidate | 41,758 |
| working | active | 16,401 |
| semantic | candidate | 27 |

所有 memories 的 `bank_id` 都是 `personal`。

### 5.2 Evidence 验证状态

| validation_state | evidence_kind | 数量 |
|---|---|---:|
| unverified | observation | 57,163 |
| supports | observation | 6 |

`memory_evidence.relation` 全部为 `supports`，没有生产数据中的 `contradicts` 链接。

### 5.3 Schema 状态

| schema_type | state | 数量 |
|---|---|---:|
| CONCEPT | ACTIVE | 5 |
| DOMAIN | ACTIVE | 1 |
| EVENT_TYPE | ACTIVE | 1 |
| SIGNAL | ACTIVE | 1 |

这 8 个 schema 主要是本体/领域概念，未看到 `KNOWLEDGE` 或 `PATTERN` 类型的已发现用户规律。

### 5.4 数据含义

- 系统已经积累了大量记忆，但绝大多数处于 `candidate` / `unverified`；
- 没有 `memory_feedback`、没有 `change_plans`、没有 `agent_grants`；
- Schema 层主要被用作领域本体，而不是从经验中形成并验证的 Knowledge；
- 2,538 个 pending outbox、3,194 个 pending task 说明异步队列仍有积压，P0 应把队列排空/监控列为运行基线。

---

## 6. 能力逐项审计

### 6.1 Memory / Observation

**状态：Implemented。**

已有：

- `capture_observation()`：归一化、幂等、事件、快速 working memory；
- `propose_memory()`：状态、版本、证据、FTS；
- `update_memory()`：乐观版本冲突检测；
- `forget_memory()`：软/硬删除，硬删受 capability gate；
- `memory_versions`：版本快照；
- Bank 隔离。

缺口（相对 2.0）：

- Memory 没有 first-class security context（owner/classification/purpose）；
- `metadata` 是自由 JSON，缺少统一契约；
- 没有 Working Memory 容量/淘汰/干扰的显式算法；
- 没有 Claim 层，Memory 不能表达“可独立验证的命题”。

### 6.2 Evidence

**状态：Partial。**

已有：

- `evidence/store.py`；
- `evidence_kind`、`validation_state`、`confidence`、`producer`、`metadata`；
- provenance 字段由 observation 派生。

缺口：

- 无独立 `evidence_id`；
- 无 `source_fingerprint` / `derivation_chain` / `independence_key`；
- 无 Evidence 级授权；
- 无独立性算法；
- 生产数据中 57,163 条为 `unverified`，6 条为 `supports`，没有 `contradicts`；
- 不能支撑 2.0 的“证据集 → Justification → Claim”链路。

### 6.3 Claim / AST / Parser / Relation

**状态：Missing。**

代码搜索没有发现：

- `Claim` 模型；
- `ClaimAST`；
- `parse_claim`；
- `relate_claims`；
- `same_as`；
- Claim 状态机。

现有 `MusicRecallService` 等模块返回的 `claims` 只是临时 JSON 字段，不是可持久化 Claim。

> **P2 的第一个真实新模块，必须从 Claim 开始，而不是从 Schema 开始。**

### 6.4 Confidence / Verification

**状态：Partial（仅有字段和启发式分数）。**

已有：

- `confidence` 字段；
- `memory_evidence.validation_state`；
- `change_plan.verification_status`（`pending` 等）；
- 检索排序中的 evidence/status 分数。

缺口：

- 无 Claim 级 `VerificationRecord`；
- 无验证范围、验证者、策略版本、有效期；
- 无 `verified / not_verified / insufficient / disputed / expired` 枚举；
- `validation_state` 不是统一验证结果；
- 现有 confidence 是浮点数与启发式加减，不是证据集评估。

### 6.5 Visibility / Security

**状态：Partial。**

已有：

- `AccessContext`（node / agent）；
- `agent_grants`：permissions、banks、expiry、revoke；
- `authority_state`；
- `memory_banks`；
- `metadata.policy`：`allow_store` / `allow_forward` / `allow_train` / `retain_until`；
- 检索按 `bank_id` 过滤；
- 硬删受 capability gate。

缺口：

- 权限是**请求级**，不是对象级；
- Memory 只有 `bank_id`，没有 `owner_id` / classification / purpose / grants；
- Schema、Relation、Evidence 没有统一 `security_context`；
- 没有 `visible(principal, object, purpose, fields)`；
- 没有替代 Justification 的可见性计算；
- 没有字段级披露、推理泄漏检查、redirect 权限保持；
- 没有 `trace` 或拒绝原因的安全输出策略。

### 6.6 Schema / Knowledge

**状态：Partial / Experimental。**

已有：

- `cognitive_schemas`：name、description、type、state、confidence、payload；
- `schema_versions`：版本快照；
- `schema_discovery.py`：token Jaccard 聚类，生成候选；
- `schema_ops.py`：assimilate / accommodate；
- `schema_evolution.py`：assimilation / accommodation / conflict；
- `schema_network.py`：split / merge / impact。

关键问题：

1. **Schema 不是 Claim 派生**：证据是 `memory_id` 数组，不是 Claim/Evidence 集。
2. **Schema 没有 security context / bank 范围**：无法按 Bank 或用户授权隔离。
3. **Schema 置信度是启发式**：`+0.02` / `-0.05` / 固定 delta，不是验证结果。
4. **Schema Discovery 是词面 Jaccard**：`_TOKENS` + 贪心聚类，候选置信度是固定公式。
5. **Schema mutation 存在治理旁路**：
   - `schemas_assimilate` 只要求 Node token，直接修改 schema；
   - `schemas_accommodate` 直接修改并可选生成 plan；
   - `split_schema` / `merge_schemas` 接收 `confirm=true` 后直接执行，不经过 Authority/审批；
   - `apply_cognitive_change_plan` 有风险检查，但直接 split/merge 不依赖它。
6. **Metacognition 是 stub**：
   - `reflect()` 是启发式检查；
   - `analyze_impact()` 读取 `sch["relations"]`，但 Schema Network 主要写 `network_links`，可能看到空影响集。
7. **无 AND/OR Justification、无 SCC、无增量传播**：`impact_of_schema` 只返回邻居、证据、计划计数。

### 6.7 Retrieval

**状态：Partial。**

已有：

- FTS5 + LIKE 降级；
- `retrieval/planner.py` 规则触发；
- `retrieval/pipeline.py` plan → search → filter → rank → deepen；
- spatiotemporal rerank；
- optional emotion rerank；
- `retrieval/semantic.py`：字符 n-gram 哈希向量 + 可注入 `EmbeddingProvider`。

缺口：

- `semantic.py` **没有接入 `service.search` / `pipeline`**，测试只验证“可选信号”；
- `SearchQuery` 没有 `domain` 字段，领域过滤/闸门无法在 Node 端执行；
- 没有 Claim/Verification 状态过滤；
- 没有 Claim 级冲突/反证召回；
- `status_score` 将状态映射为固定分，不是权限/验证语义；
- 没有 `unknown` / `not_found` / `not_authorized` 的区分。

### 6.8 Change Plan / Learning Proposal

**状态：Partial。**

已有：

- `change_plans` / `cognitive_change_plans`；
- `store_change_plan` / `get` / `list` / `update`；
- `change_plan.py` 有 proposal/apply 逻辑；
- `apply_cognitive_change_plan` 对高风险要求 `confirm`；
- `schema_network` 拆分/合并会生成 plan。

缺口：

- 没有统一的 `LearningProposal` 类型，Change Plan 只是现有载体；
- 没有 universal validation / evidence / impact / rollback 字段；
- 直接 schema mutation 可以绕过 plan；
- 没有 Claim 级别提案；
- 没有审批角色/风险等级到 Authority 的映射；
- 没有并发提案冲突处理。

### 6.9 Governance / Identity

**状态：Partial（请求级强，对象级弱）。**

已有：

- Node Bearer 与 Agent Token；
- `agent_grants`：permissions / banks / expiry / revoke / audit；
- `authority_state` 五态；
- `capability_gate`；
- `policy.py`：store/forward/train/retention；
- `access.py`：API 层权限执法。

缺口：

- 只有 Request 级 AccessContext，没有 Object 级 SecurityContext；
- `memories` 只有 `bank_id`；`cognitive_schemas` 没有 bank；
- 无 `purpose_constraints`；
- 无 `authorized_grants` 与对象的关联；
- 无 Claim/Knowledge 的审批模型；
- 无 Trace/审计链，只有 events/outbox 和零散 audit 表。

### 6.10 Observability

**状态：Missing（针对 2.0 判断契约）。**

已有：

- `events` 表、`outbox`、`tasks`、`inbox`；
- API 返回 `write_stages` 等；
- readiness/health。

缺口：

- 无 `trace_id` / `span_id`；
- 无 `JudgmentTrace` / `DecisionRecord`；
- 无 `trace_completeness`；
- 无 replay；
- 无 Claim 判断的 machine-verifiable reason；
- 无法从 Claim 状态变化回溯到规则/证据/算法版本。

---

## 7. 性能基线

### 7.1 合成基准

方法：临时 SQLite + `MemoryService`，2,000 条合成 semantic memory，每条 1 个 source_id；Windows 本机、in-process、无网络。

| 指标 | 结果 |
|---|---:|
| DB 大小 | 4,972,544 bytes |
| 初始化/迁移 | 38.0 ms |
| 写入 2,000 条 | 2,257.55 ms |
| 单条写入 | 1.129 ms |
| 检索（9 次） | 1.07–1.94 ms |
| 检索中位数 | 1.20 ms |
| 检索 P95 | 1.83 ms |
| 单次检索 | 1.15 ms |
| 上下文组装（3 次） | 1.44–1.53 ms |
| health | 0.93 ms |

> 合成库没有 58k 生产数据的索引膨胀、WAL、事件/任务表和并发竞争，**不能当作生产 P95**。

### 7.2 生产库基线

| 项 | 值 |
|---|---:|
| DB 大小 | 548 MB |
| 记忆 | 58,186 |
| 版本行 | 58,159 |
| 证据链接 | 57,169 |
| 事件 | 100,475 |
| 任务 | 98,932 |
| pending outbox | 2,538 |
| pending tasks | 3,194 |

### 7.3 性能结论

- 当前检索在合成小库上很快，但不能证明 58k 生产库的 P95；
- 存储/事件/任务量已经显著大于记忆本体，需建立 **存储增长、事件保留、队列排空** 基线；
- P0 应补：生产库检索 P95、Outbox/Task 排空时间、Trace 写入开销、重放耗时。

---

## 8. 主要审计发现

### Critical

1. **Claim 全链路缺失**：无 AST、Parser、Relation、状态机、持久化、API、测试。
2. **Evidence 不是 first-class 对象**：无法实现独立性、派生链、Justification、证据级权限。
3. **Schema mutation 存在治理旁路**：direct assimilate/accommodate；split/merge 可在 `confirm=true` 下直接执行，无 Authority/审批。
4. **对象级安全上下文缺失**：Schema/Evidence 没有 bank/owner/purpose；无法做 `visible` 契约。

### High

5. **无 VerificationRecord**：`validation_state` 和 `confidence` 不能替代验证。
6. **无 JudgmentTrace/DecisionRecord**：无法回答“为什么这个 Claim 被标为 verified”。
7. **Schema 发现/演化是启发式**：Jaccard + 固定置信度，缺少独立验证与反例。
8. **Metacognition 是 stub**：`analyze_impact` 与 `schema_network` 字段不一致。
9. **历史数据几乎未验证**：57,163 条 evidence 为 `unverified`，无 Claim 映射。
10. **迁移没有 Claim 语义**：现有 migration 处理 Memory 导入，不处理 Claim AST/Provenance。

### Medium

11. **Semantic 检索未接入主检索**：`semantic.py` 是可选信号，不是生产路径。
12. **无 domain 过滤**：`SearchQuery` 无 `domain`，音乐组件的领域闸门无法在 Node 执行。
13. **队列积压**：2,538 pending outbox / 3,194 pending tasks。
14. **文档与代码有张力**：README/旧 2.0 矩阵描述的能力大于实际 Claim 能力。

---

## 9. 可复用 / 需改造 / 需新增

### 可直接复用

- `observations` / `memories` / `memory_versions` / FTS；
- `memory_banks` / `bank_id`；
- `agent_grants` / `authority_state` / `policy` / `access`；
- `events` / `outbox` / `tasks` / `inbox`；
- migration staging / interchange / checkpoint；
- API 基础设施、MCP、CLI、readiness suite；
- `memory_evidence` 作为**过渡性证据链接**。

### 需要改造

- `memory_evidence` → 独立 Evidence 对象 + provenance/independence；
- `cognitive_schemas` → Knowledge/Claim 之后的结构化知识；
- `schema_discovery` → Pattern candidate（不能直接写正式 Knowledge）；
- `schema_evolution` → 基于 Claim/验证的演化；
- `schema_network` → Justification/Impact 图，而不是 `network_links` 计数；
- `feedback_learning` → 反馈归因/结果记录，不是置信度加减；
- `metacognition` → MetaController 的调度基础；
- `semantic.py` → 真正接入 retrieval pipeline；
- Change Plan → LearningProposal 的通用载体。

### 必须新增

- Claim AST v1 / parser / relation / state machine；
- Claim 持久化与版本/merge/split/redirect；
- Evidence provenance/independence；
- VerificationRecord；
- Justification/Truth Maintenance；
- Visibility 判定；
- JudgmentTrace/DecisionRecord；
- Experience / Strategy / StrategyLog（P5+）。

---

## 10. P2 前必须关闭的审计门

在开始 P2 Claim 纵向切片前，必须完成：

1. 冻结 Claim AST v1 与 `RelationResult`；
2. 冻结 Evidence provenance/independence 字段；
3. 冻结 `visible` 的 Justification 计算与 fail-closed 规则；
4. 冻结 `verified` 的 VerificationRecord 与状态映射；
5. 冻结 `unknown` 的 TruthValue 与原因码；
6. 给出 Claim 表/索引/迁移草案；
7. 用 100 条历史 Memory 做 P0.5 迁移 spike；
8. 修正 schema mutation 的治理旁路；
9. 建立一条 Claim 测试矩阵（S1–S14+）。

---

## 11. 审计结论

现有仓库的价值不在“已经实现了 2.0”，而在于它提供了：

- 可运行的 Node / Bank / 事件 / 任务基础；
- 大量真实记忆数据；
- 请求级权限与迁移工具；
- 可复用的 API / MCP / CLI / 测试设施。

2.0 的正确路径不是重写这些基础，而是：

```text
保留 Memory / Bank / Governance / Runtime
        ↓
把 Evidence 从“链接”升级为“对象”
        ↓
新增 Claim / Parser / Relation / Verification
        ↓
让 Schema 变成 Claim/Knowledge 的下游
        ↓
最后再做 Truth Maintenance / Strategy / MetaController
```

**P0 审计结论：可以进入 P0.5 迁移 spike 和 P1 契约冻结；不应直接进入全面 P2 开发。**
