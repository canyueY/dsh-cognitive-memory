# 重构理论的功能实现与验证

日期：2026-11-01。适用：当前未提交的 Mnemosyne 2.0 合并工作区。

依据：用户提供的《理论基础重构：从最小要素到可验证闭环》v0.1。本文区分已执行的工程验收与尚待真实任务验证的研究假设。

## 组件范围

实现位置是 `dsh-mnemosyne/service`。Mnemosyne 是执行核心；Memory Bank 是其管理的数据目录，包含 SQLite、证据与版本等状态，不是另一个需要重复实现的服务。本轮扩展现有 Bank schema，不另建个人记忆数据库，不修改归档的旧核心。

原工作区已有的权限、迁移、领域包、故障验证等改动全部保留。本轮未读取、迁移或回填生产个人库，未重启当前 Node，未提交、发布或更新旧 release-dist。

## 逐项对照与实现

### 读取、编码和组织

- 继续保留原始 Observation、来源和时间，摘要派生条目新增 `epistemic=summary`、原观察引用与 `lossy` 标志。
- Parser v2 保留具名主体、偏好否定、系词否定、位置否定及相对时间；对不能可靠处理的程度、暂时状态和复合偏好输出 Unresolved，保留原文，不输出永久偏好。
- 明确提供的有效期进入 Claim 的规范化身份，避免不同时间段的命题被错误去重。新增 parser_version；历史未知 Parser 不伪装成可精确重放。
- 相似和分组继续用于索引与候选生成，不因检索命中、同化或好评自动认证事实。

### 证据、推断与依赖

- Verification 拒绝直接用 inference、summary、model_output、self_eval、generated 及相应 epistemic 标签认证事实。
- Evidence 支持 `metadata.parent_evidence_ids`，递归解析声明的来源；跨 Bank、缺失、环路、超出节点预算及撤回的来源失败关闭。
- 独立性检查比较传递来源根，不因换 producer 或导入格式就把同一个根当作新来源。
- 撤回证据时，将依赖的转述标为待核验，重审关联 Claim；尚有其他有效独立支持的结论保留并重新验证。
- 检索分数显式标记为排序分数；上下文片段及 brief 显式标记 hypothesis／unverified_record，不把持久化成功解释为内容真实。

来源根是可审查的声明，不是来源真实性的密码学证明。使用不同假身份伪造来源等问题，仍需上游来源审核；系统不能仅凭 JSON 字段推断真实世界独立性。

### 反馈、权重与归因

- 旧 Feedback 接口保持兼容，新增 `feedback_kind` 并持久化；未分类反馈默认 unclassified。
- useful 不再自动晋升事实候选；任务成败和自评不再增减事实置信度。不同来源的 utility_signal 仍可记录，但不作为概率。
- 事实纠错、故障或约束违反进入重审任务，归因默认为 unresolved，不从负反馈直接宣布根因。
- 慢速晋升要求关联的 Claim 有当前数据库支持的 Verification，拒绝 force_activate、from_user 和重复好评替代证据；推断必须经过明确重新分类，不能自动洗成事实。
- 同化、顺应和演化不再按新增引用数量给事实置信度加减固定常数。演化写入要求现有 SCHEMA_MUTATION 治理权限，不会仅凭 confirm 解锁。

### 有界任务闭环

新增 `CognitiveLoops` 与严格输入契约，接入 REST 和 Python／TypeScript SDK。

任务包括 goal、bank_id、context、acceptance、allowed_actions、actions、max_steps 和 use_cache。每个行动声明依赖 Claim，可关联一个可执行图式；priority 只用于任务排序。

处理过程：检查动作授权范围 → 检查情境 → 检查图式条件和反证 → 检查 Claim 当前有效性与证据 → 比较可行行动 → 返回 selected 或 unknown → 保存处理轨迹。

执行图式采用有限 JSON 条件：action_id、when、invalid_when、required_claim_ids、counter_claim_ids、valid_from、valid_until。when 使用明确 JSON 值匹配；未知情境不默认匹配。任意自然语言规则不会被直接执行。

预算耗尽时返回 unknown，不把尚未检查的候选或反证当作不存在。选择行动不等于执行成功，task_success 保持未知，直至有后续结果记录。

任务结果独立记录 kind、source、outcome、possible_stages、evidence_ids；possible_stages 是原因假设，不是已验证诊断。没有结果时不编造奖励。

### CACHE 与 HEURISTICS

完整依赖快照绑定任务、Bank、情境、图式、Claim、支持／反对证据、传递来源及时间有效性。命中前重新读取依赖与时效；撤回、过期、版本或上下文变化使旧缓存失效。

精确缓存复用是本轮可验证的捷径；不宣称已经实现任意语义近似缓存。每个任务可关闭缓存走完整检查路径。缓存最多保留 256 项；读取依赖仍有成本，不宣称零成本加速。

现有 MetaQueue 已有持久化预算、优先级老化和冷却。本轮新任务闭环在候选未检查完且预算耗尽时明确放弃确定选择，避免用资源不足伪装成反证已排除。最优探索比例仍需真实任务标定。

### 学习闭环、独立验收和回滚

1. 先登记不可通过更新提案修改的 ValidationSuite，包含 heldout 与 regression 两类案例、预期行动和验收阈值，同时冻结依赖快照与摘要。
2. 提交 LearningProposal，绑定目标图式版本和 suite；拒绝显式训练案例／来源与验证样本的重叠，检查新规则引用的 Bank 与存在性。
3. 使用同一决策引擎，在隔离的内存规则覆盖中重放旧／新版本，不修改线上图式，不调用任意脚本或模型，不接收调用者的 passed 标志。
4. 分别统计 heldout 净收益与回归损失；预算不足、目标变化、来源变化、测试内容变化都不能发布。
5. apply 再次重放验证，并要求 confirm 和 SCHEMA_MUTATION；版本、状态、验收报告与采用记录在同一事务提交。
6. rollback 恢复之前的规则／状态，保留递增版本与历史；有后续无关修改时拒绝覆盖。

修复 Capability 的只读检查意外提交外层事务的问题，并执行到期检查。新增故障注入测试：图式写入后发生异常时，图式与采用状态一起回滚。

本轮验收测的是有限规则执行器的行为正确性，不是大样本认知能力提升。训练来源由调用者声明；没有声明完整训练历史，系统不能证明现实中的数据独立性。固定测试反复调参后的泛化能力也需另行检验。

### 人格、情绪、偏好和价值

新增 ProfileHypothesis，分别记录 personality／preference／emotion／value，保存主体、情境、来源、自述／推断、依据、guided 标记和到期条件。

这些条目保持 candidate／hypothesis，声明只可用于表达和注意，不自动改变事实、授予权限或把价值主张转成执行规则。没有预设大五人格解释比例、道德阶段总分或由相似度直接推导心理概率。

这里完成的是可追溯、可撤回的状态记录与影响边界。通用人格预测模型、情绪动力学和价值冲突求解器仍是研究问题，不由本轮几个规则冒充完成。

## 新接口

全部位于 `/api/v1/cognition`，本轮为 Node 管理控制面，要求 Node token。普通 Agent grant 不能借此绕过对象权限或自行发布图式。

- `POST /tasks/run`：处理有界任务。
- `POST /tasks/{run_id}/feedback`：记录执行结果和分类反馈。
- `POST /validation-suites`：登记固定验收。
- `POST /learning-updates`：提交规则更新。
- `GET /learning-updates/{id}`：读取更新及报告。
- `POST /learning-updates/{id}/evaluate`：执行重放比较。
- `POST /learning-updates/{id}/apply?confirm=true`：经能力门控采用。
- `POST /learning-updates/{id}/rollback?confirm=true`：经能力门控回滚。
- `POST /profile-hypotheses`：记录有情境的画像假设。

Python SDK 方法为 run_cognitive_task、record_cognitive_result、register_validation_suite、propose_learning_update、evaluate_learning_update、apply_learning_update、rollback_learning_update、record_profile_hypothesis。TypeScript 有相应 camelCase 方法。

旧 search／retrieve 继续返回记忆候选；它们不自动执行新任务闭环。需要行动决策的调用者使用新接口。旧描述性图式管理操作与“通过独立任务验证的新规则采用”分开，不把人工改动等同于自动学习成功。

## Bank 升级与兼容

迁移 `017_theory_loops` 增加 Claim parser_version、反馈类型，以及任务运行、任务反馈、固定验收、学习更新和缓存表。复用同一个 SQLite Bank。

已有 Bank 在正常启动升级流程中先生成备份，再应用迁移。旧反馈标为 unclassified，旧 Parser 标为 legacy；不补造旧来源，不自动提升旧结论。生产升级尚未执行。

刻意改变的旧语义：好评不晋升，元数据 from_user／force_activate 不作证明，自评／任务成功不增加事实置信度，同化不按计数增信。相应旧测试已改为验证新约束；保留真实证据认证后能够晋升的正向测试，没有跳过失败用例。

另外修复全文检索的 FTS MATCH 表名引用，并让上下文打包不再因首条内容过长而突破声明的内容 token 估算预算。token_estimate 是既有估算，不等于模型精确 tokenizer；头部和提示标签也不在该内容估算中。

## 可重复验证

在 service 目录执行：

```powershell
& '..\..\.venv\Scripts\python.exe' -m pytest tests -q
& '..\..\.venv\Scripts\python.exe' scripts/verify_theory_loops.py
```

第二条脚本只创建临时 Bank，合成 Observation 与审查者记录，执行验证、能力门控、规则采用、情境边界、缓存失效和回滚；不会接触个人数据。其 synthetic gain 只是夹具结果，不应作为真实用户效果报告。

关键反例覆盖：主体／否定／时间保留、暂时偏好不泛化、同源跨导入不独立、循环来源、自产证据拒绝、反馈不增信、不同 Bank／情境／动作约束、预算终止、缓存与完整路径一致、过期与撤回、下游重审与独立支持保留、验收污染、伪造 passed、并发版本冲突、事务中断、回滚冲突、画像保持假设、REST 授权、SDK 调用、旧 Bank 升级备份。

## 本轮实际运行结果

- 服务完整测试：**352 passed in 52.98s**；修改前为 306 项，本轮新增 46 项理论约束验收。
- 桌宠桥接、兼容、编排：**13 passed**。出现已有根目录 pytest 缓存不可写提示，不影响测试执行。
- Node 插件：`npm test` **7 passed**，`npm run check` 通过。
- TypeScript SDK：TypeScript 5.9.3 `tsc --noEmit -p sdk-ts/tsconfig.json` 通过。
- 临时 Bank 闭环脚本：通过；门控、情境边界、缓存失效与回滚均实际执行。
- 临时 wheel 构建：通过；包含新模块，打包 Manifest 的源码校验值与当前源码一致。
- `git diff --check`：通过。

这些测试没有跳过失败用例或放宽新约束。工程验收通过不能替代真实语料的消融、反馈归因研究和长期效果测量。
