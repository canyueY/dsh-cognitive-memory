# Mnemosyne 2.0 — 现有模块到目标对象的映射

**审计提交：** `589c694`  
**用途：** P0 审计附件；回答“现有代码能复用到什么程度”。  
**注意：** 这是目标映射，不代表现有实现已经满足 2.0 契约。

## 状态说明

| 状态 | 含义 |
|---|---|
| Implemented | 有可运行代码 + 测试/调用路径 |
| Partial | 有实现，但缺 2.0 语义或关键契约 |
| Stub | 有接口/骨架，缺实际能力 |
| Missing | 2.0 要求存在，仓库中没有实现 |
| Keep | 保留并作为基础 |
| Adapt | 改造后复用 |
| Wrap | 用适配层包装，不直接改核心 |
| New | 必须新增 |

---

## 1. 六类对象映射

| 2.0 对象 | 现有实现 | 状态 | 决策 | 主要缺口 |
|---|---|---|---|---|
| Memory | `memories`、`memory_versions`、`bank_id`、`metadata` | Implemented | Keep | 无统一 SecurityContext；metadata 自由 JSON |
| Evidence | `memory_evidence`（Memory↔Observation 链接） | Partial | Adapt | 非独立实体；无 source fingerprint/derivation/independence |
| Claim | 无 | Missing | New | AST、parser、relation、state machine、persistence、API |
| Knowledge | `cognitive_schemas`、`schema_versions` | Partial | Adapt | 无判别式类型；Schema 未由 Claim 派生；无 validator |
| Experience | episodic memory / events | Partial | Adapt | 无 first-class Experience；无 task/action/outcome 统一结构 |
| Strategy | 无 | Missing | New | Strategy、StrategyLog、propensity、off-policy |

---

## 2. 核心模块映射

| 现有模块/表 | 当前实际职责 | 2.0 目标职责 | 状态 | 处理 |
|---|---|---|---|---|
| `observations` / `capture_observation` | 原始观察、幂等、working memory 快通道 | Memory/Evidence 的输入与来源 | Implemented | Keep |
| `memories` / `propose_memory` | 长期记忆、状态、版本、FTS | Memory | Implemented | Keep |
| `memory_versions` | 记忆版本快照 | Memory version history | Implemented | Keep |
| `memory_evidence` / `evidence/store.py` | Memory↔Observation 证据链接 | Evidence 对象 + provenance | Partial | Adapt |
| `memory_relations` | 记忆关系（supports/supersedes/…） | 关系图 + Justification 边 | Partial | Adapt |
| `memory_feedback` | useful/incorrect 反馈 | Feedback signal / attribution | Partial | Adapt |
| `events` / `outbox` / `tasks` | 事件、outbox、异步任务 | Trace/Event 基础和任务队列 | Implemented | Keep |
| `idempotency_keys` | 幂等 | 幂等基础 | Implemented | Keep |
| `memory_banks` / `bank_id` | Bank 隔离 | SecurityContext 的 bank 维度 | Partial | Adapt |
| `agent_grants` / `authority_state` | Agent 授权、Authority 五态 | Governance / Authority | Implemented | Keep/Adapt |
| `access.py` / `policy.py` | 请求级访问、store/forward/train/retention | `visible` 的一部分 | Partial | Adapt |
| `capability_gate.py` | 高风险能力闸 | Governance | Implemented | Keep |
| `cognitive_schemas` | 图式/本体/假设 | Knowledge / StructuralKnowledge | Partial | Adapt |
| `schema_versions` | Schema 版本 | Knowledge version | Implemented | Keep/Adapt |
| `schema_discovery.py` | Token Jaccard 聚类 → Schema 候选 | Pattern/Knowledge discovery | Partial | Adapt |
| `schema_ops.py` | Assimilation / Accommodation | Knowledge operations | Partial | Adapt |
| `schema_evolution.py` | 同化/顺应/冲突 | Knowledge evolution | Partial | Adapt |
| `schema_network.py` | Split/Merge/Impact | Knowledge dependency / impact | Partial | Adapt |
| `metacognition.py` | 启发式 reflect / impact stub | MetaController | Stub | Wrap |
| `retrieval/planner.py` | 规则触发/模式 | Retrieval planner | Implemented | Keep |
| `retrieval/pipeline.py` | plan → search → filter → rank | Retrieval pipeline + Claim 筛选 | Partial | Adapt |
| `retrieval/scoring.py` | R/T/S/E 加权 | Retrieval scoring | Partial | Adapt |
| `retrieval/semantic.py` | 哈希 n-gram 语义信号 | 候选召回信号 | Partial | Adapt/未接入 |
| `change_plans` / `cognitive_change_plans` | 变更计划/审批 | LearningProposal 载体 | Partial | Adapt |
| `change_plan.py` | Proposal/apply/rollback | LearningProposal 逻辑 | Partial | Adapt |
| `migration/*` | Memory 迁移、staging、checkpoint | 历史迁移基础 | Implemented/Partial | Keep + New Claim spike |
| `components/*` | 本地组件管理 | 组件/知识包管理 | Implemented-lite | Keep |
| `api/app.py` | REST 路由 | 2.0 API surface | Partial | Extend |
| `mcp/server.py` | MCP 工具 | Agent 接入 | Partial | Extend |
| `migrations.py` | SQLite schema | 2.0 schema migration | Implemented | Extend |

---

## 3. 2.0 判定域映射

| 判定域 | 现有对应 | 状态 | 缺口 |
|---|---|---|---|
| `same_as` | 无 | Missing | 无 Claim AST、无 relation engine |
| `visible` | `AccessContext` + `agent_grants` + `bank_id` + `policy` | Partial | 请求级，不是对象级；无 Justification/字段级/推理泄漏 |
| `verified` | `memory_evidence.validation_state`、`confidence`、`change_plan.verification_status` | Partial | 无 VerificationRecord/范围/有效期/策略版本 |
| `unknown` | `retrieval` 的 `NO_MATCH/PARTIAL`、metacognition 的 uncertainty 字符串 | Missing | 无 TruthValue、原因码、对外脱敏 |

---

## 4. 直接复用 / 需要改造 / 新增

### 直接复用

- Observation / Memory / MemoryVersion / FTS；
- Memory Bank 与 `bank_id`；
- Agent grants / Authority / capability gate；
- events / outbox / tasks / idempotency；
- migration staging / checkpoint / interchange；
- API / MCP / CLI / readiness suite；
- 现有 122 个测试作为回归基础。

### 改造后复用

- `memory_evidence` → Evidence 对象；
- `cognitive_schemas` → Knowledge（Claim 下游）；
- `schema_*` → Knowledge candidate/evolution/dependency；
- `feedback_learning` → attribution/learning signal；
- `metacognition` → MetaController；
- `retrieval` → Claim/Verification-aware retrieval；
- Change Plan → LearningProposal。

### 必须新增

- Claim AST / parser / relation / verifier / state machine；
- Evidence provenance/independence；
- Justification / Truth Maintenance；
- Visibility / Disclosure；
- JudgmentTrace / DecisionRecord；
- Experience / Strategy / StrategyLog；
- Claim migration 与回滚。

---

## 5. 关键结论

1. **现有 Memory/Bank/Governance/Runtime 应保留，不应重写。**
2. **Schema 层不能直接升级为 Claim 层；它必须移到 Claim/Knowledge 下游。**
3. **Evidence 必须先对象化，否则 Claim 的验证没有可执行依据。**
4. **Change Plan 可以复用，但必须收口为统一 LearningProposal。**
5. **P2 只应新增 Claim 纵向切片，不应同时重写 Schema/Strategy/MetaController。**
