# 三笔记审查后的实现补全

日期：2026-10-31。基于当前工作区 `969b10a`，未提交、未发布。依据《项目定义》《和其他记忆库的解决方案》《10.31更新方案》，优先修复已复现的不变量失败，复用既有 Bank/Runtime。

## 已实现并验证

- **入口统一**：桌宠完整/精简配置指向 `dsh-mnemosyne/service`；桥默认优先寻找合并 Node，自定义路径和环境变量继续有效。旧核心未提交的音乐 Domain Pack、关系和检索改动已整合，原文件保留。
- **Claim 权限**：统一检查主对象、关联对象的 Bank，以及 Evidence 所有者/用途；事务提交时再检查 grant 有效性。合并/拆分/重定向不能扩大 Bank 权限，无权限和不存在使用 opaque 响应。未具备对象授权边界的全局 TMS/Knowledge/Strategy 管理暂限 Node 管理员。
- **Verification**：事务内检查真实 Evidence、来源、有效状态、scope、权限、反证和独立性。伪 ID、未审查/撤销证据和 Unresolved 不能 Verified；请求布尔值只能否决。生命周期跳转不能绕过引擎；Record、Claim、TMS、Trace、Decision 统一提交，错误回滚。支持 Evidence assessment、撤销重评、版本冲突检查和幂等验证。
- **规范化 v2**：保留参数顺序、空参数、标点、小数；常用单位确定性换算，MW/mW 不混淆。可按新规则比较旧 AST 并复用旧 ID，不改写历史哈希；旧算法不可重放时明确返回 unavailable。
- **披露控制**：Evidence 隐藏时移除 verification_status 和 Verified lifecycle，历史/Decision/Evidence 查询也执行约束；Store 先查授权元数据再读正文，重定向有环路/深度保护。
- **迁移审批和回滚**：批准哈希绑定提交内容，Staging 原子替换。不同来源不因同文被自动丢弃，来源版本冲突要求审查。保留来源 Bank、隐私/训练/转发/保留期/删除限制；幂等键隔离 Bank。回滚只处理本批创建的记忆，不动原已存在的记忆；失败不伪装 committed。
- **Memory Bank 安全复制**：通过 SQLite backup 生成包含 WAL 的一致快照；不复制活动 runtime 标记。拒绝路径重叠和运行中的目标，覆盖前备份。数据库有待应用迁移时先自动备份并校验，再逐项事务迁移。
- **Trace 和 Schema**：JudgmentTrace 持久化，重建 Store 可恢复；关键写入失败中止。显式 preview（含 HTTP split/merge）零写入。Proposal 绑定 expected_versions，串行校验提交并保存幂等 receipt；内部 preauthorized 布尔值不能绕过 capability。
- **策略和调度**：新增真实行为概率上的 IPS/SNIPS/DR、baseline、overlap、ESS；缺数据返回 insufficient。旧奖励/Jaccard 混合分标明为 suitability，不作为选择概率；评估报告不混入动作概率日志。MetaController 复用 tasks，持久化去重、优先级/老化、冷却、预算、重试、租约恢复与版本检查，并接入 worker。
- **故障和时间**：在隔离 SQLite 快照中真实复现、运行四类回归并重新执行已知修复，再比较结果；修复有审计和回滚事件。新增按时刻重建 Decision 状态、确定性 Parser/AST 重放，明确区分快照修复重放与完整模型历史重放。

## 新增接入能力

- `manifest/` 及安装包内 Manifest/JSON Schema，附本地源码 checksum；签名列表为空，未伪造发布签名。
- `discover / diagnose / plan / install / connect / verify / upgrade / rollback`：只读计划、源码/配置哈希绑定、明确授权标志、运行中检查、升级备份和恢复、临时库功能验证。模式是配置已具备依赖的 Python 环境，不自动下载并信任未知包。
- [onboarding Skill](../../src/cognitive_memory/resources/onboarding/SKILL.md)，随 wheel 打包并经 skill-creator validator 验证。
- `memory providers / discover / inspect` 和 `memory migrate plan / run / verify / history / rollback`；执行需 batch checksum 和 confirm，验证记录数、来源 ID 与正文，不把截断/未映射当作迁移完成。
- JSON/JSONL/CSV/Markdown/SQLite 与 Mem0、Zep/Graphiti facts、Letta blocks/archive、LangChain documents 的**导出文件映射**。保留 raw payload、时间、原 ID 和来源指纹，导入保持 candidate。
- `/api/v1/compat/mem0/add|search` 与 GET/DELETE `/compat/mem0/{memory_id}`，明确为 record subset。hard delete 返回 501；soft delete 明示 physical_erasure=false。可绑定 legacy_reader 做 read-through，外部结果不自动成为个人事实。

## 数据库与兼容

新增迁移 `016_audit_hardening`：judgment_traces、Claim version / normalization_version、schema_proposal_commits。已在旧 Foundation schema 的临时库验证：保留原记忆，生成可读升级备份。本次没有打开/迁移个人生产库，没有回填历史 Claim。

旧测试中“虚构 ID 应 Verified”“任意字节冒充 SQLite”的夹具已换为真实临时 Evidence/SQLite，原成功断言保留，并新增反例。桌宠注入测试改为 mock 当前实际的外部召回边界，保留注入断言；没有跳过测试或降低断言。

## 实际验证

使用项目已有 `.venv/Scripts/python.exe`，未安装新运行时依赖：

- service `python -m pytest tests -q`：**306 passed in 36.25s**。
- `npm test`：**7 passed, 0 failed**；`npm run check` 通过。
- 桌宠桥接/兼容/编排三个测试文件：**13 passed**。
- CLI 临时目录：只读 diagnose → plan → checksum 批准/run → verify → rollback 通过，源文件字节不变。
- `python -m build --wheel --no-isolation` 通过；检查 wheel 含 Manifest、Schema、Skill，且 source checksum 与当前源码相同。临时构建，未更新旧 release-dist 或发布包。
- Skill validator：**Skill is valid!**；`git diff --check` 通过。

## 仍不计作完成

1. **生产激活**：配置已切换，当前运行中的 Node 未重启；新入口在下次启动生效。自动备份不替代真实现网发布/回滚签字。
2. **生产历史 Claim 迁移**：已有抽样来源完整率为 0，生产迁移 gate 保留，不补造历史 provenance。
3. **跨节点 Federation/PCIP/P2P 与在线 vendor 双向同步**：本轮未实现；文件导入和单 Node grants 不等同完整联邦或完整官方 vendor API。
4. **完整认知研究链路**：任意历史模型重放、生产 propensity 采集、完整 shadow/canary 效果验证和所有下游 Knowledge/Strategy 自动恢复仍需后续阶段。已有记录重建、已知修复重放、离线估计器不能替代这些证据。

本轮可宣称“主要审查阻断项已修复，新增接入闭环通过本地验收”，不能宣称三份笔记的全部长期目标或生产发布已完成。
