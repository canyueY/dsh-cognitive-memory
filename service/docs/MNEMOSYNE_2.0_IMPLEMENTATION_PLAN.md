# Mnemosyne 2.0 — Implementation Plan

**文档状态：** Active Execution Plan（2026-10-30）  
**性质：** 落地执行计划（Epic / PR / 依赖 / 验收）；**不**重复 Master Plan 定位长文  
**上位：** [MASTER_PLAN](MNEMOSYNE_2.0_MASTER_PLAN.md) · [ARCHITECTURE](MNEMOSYNE_2.0_ARCHITECTURE.md) · [CAPABILITY_MATRIX](MNEMOSYNE_2.0_CAPABILITY_MATRIX.md)  
**基线核实：** [CODE_AUDIT](MNEMOSYNE_2.0_CODE_AUDIT.md)

> 本方案是 **项目落地更新**，不是推倒重来。  
> 下列新增能力 **均未默认已实现**。

---

## 0. 落地目标（四件事）

1. **保留现有资产：** `services/cognitive-memory`、DSH 副记忆 Adapter、A-MEM 并行、Migration Engine（以 `origin/main` 为准）、Schema/Gate。  
2. **补齐基础设施：** Node 独立运行/管理；组件安装、配置、组合、升级（D8）。  
3. **开放生态接入：** DSH、社区插件、其他 Agent 经稳定契约接入；DSH **不是**唯一入口。  
4. **控制交付风险：** 按真实缺口拆 Epic/PR；规划 ≠ 已实现；D6 联邦明确裁切。

### 0.1 成功定义 = A + B + C

| 目标 | 2.0 必须回答 |
| --- | --- |
| Cognitive Infrastructure | 用户是否拥有独立、可靠、可管理的个人记忆与认知数据？ |
| Component Infrastructure | 用户能否安装、配置、组合、升级和替换组件？ |
| Agent Interoperability | DSH 以外的 Agent 能否直接接入、授权使用和撤销访问？ |

### 0.2 明确不做

- 重做 DSH Agent Runtime / 模型市场 / 桌宠 UI  
- 重做社区已有搜索/浏览器/自动化工具  
- 中心化用户记忆云  
- 首个 GA 完整 P2P / 跨节点联邦  
- 一次性纳入全部 AI 算法  
- 为包名整洁提前拆大量 npm 包  
- 一次性按目标目录树搬家  

**原则：** Mnemosyne 管理认知资产生命周期；宿主负责编排；组件提供可替换能力。

---

## 1. 基线与差异（摘要）

详见 [CODE_AUDIT](MNEMOSYNE_2.0_CODE_AUDIT.md)。

| 类型 | 内容 |
| --- | --- |
| 实施基线 | monorepo `services/cognitive-memory` + Bridge；须先与 `origin/main`（含 PR #1）对齐 |
| 生态参考 | 公开 `dsh-mnemosyne` 0.2.0（client / tool-spec / optional DSH peer / `service/`） |
| Adapter 工作区 | `_dsh_plugins/dsh-cognitive-memory`（嵌套仓，分支可能超前/分叉） |
| 禁止 | 把公开页面目录强行写成本地已实现路径 |

**包演进方向（不立即拆包）：** Core / Node 入口 / Client / DSH Adapter / Component SDK / CLI — 先稳定边界与入口，再考虑发布单元。

---

## 2. 阶段总览（依赖驱动，非工期承诺）

| 阶段 | 核心目标 | 出口 |
| --- | --- | --- |
| **P0** | 文档采纳 + 代码审计 | 真实基线冻结；D6 裁切签字 |
| **P1** | Node 生存 + 备份恢复 | 无 DSH 可运行；恢复演练通过 |
| **P2** | Cognitive Core 解耦 | Contract；Adapter 变薄 |
| **P3** | API / MCP / SDK | 外部 Agent 直连验收 |
| **P4** | Component Infrastructure (D8) | 本地组件安装生命周期 |
| **P5** | Migration / Adoption | 预览→批准→导入→权威 |
| **P6** | Cognitive Intelligence（范围内） | 黄金样本与冲突等 |
| **P7** | 集成与安全 | 2.0 GA Readiness |

---

## 3. Phase 0 — 立即执行

| ID | 工作 | 交付 | 状态 |
| --- | --- | --- | --- |
| E0.1–0.3 | Master / Arch / Matrix 采纳 | PR #2 已合入 main | **完成** |
| E0.4 | 模块与依赖清单 | [CODE_AUDIT](MNEMOSYNE_2.0_CODE_AUDIT.md) | **完成** |
| E0.5 | 接口与 DB 边界清单 | CODE_AUDIT §2–4；后续补 OpenAPI 对照表 | 部分 |
| E0.6 | 2.0 vs 2.1+ 裁切签字 | 见 §11 附录；D6 联邦 → 2.1+ | **执行启动时记录** |
| E0.7 | 同步 monorepo 与 migration | main 已含 PR #1 migration；落地 PR #2 | **完成（远程）** |

**退出：** 裁切签字 + 代码与 `origin/main` 对齐 + 无虚构模块。

---

## 4. Phase 1 — Node 生存（✅ 已收口 · 2026-10-30）

> Phase 1 实现线已完成；下一实现线见 §5 Phase 2。不要同时开 D3/D4/D8 实现洪峰。

| 顺序 | PR | Epic | 内容 | 验收 |
| --- | --- | --- | --- | --- |
| **1** | **PR-E1.2** ✅ | Backup & Recovery Drill | 合成库 drill + V8 `mnemosyne_production_backup_signoff.py` | 独立恢复 + 损坏可检；现网签字归档 |
| **2** | **PR-E1.1** ✅ | Node Runtime Boundary | `mnemosyne` CLI：`doctor/status/health/start/stop`（`cognitive_memory.node_cli`） | 不启动桌宠/DSH 也能 doctor+health |
| **3** | **PR-E1.3** ✅ | Configuration Boundary | `node_config.py`：CLI>env>file>defaults；`config init/show/validate` | 独立配置文件可加载；remote_access 守卫 |
| **4** | **PR-E1.4** ✅ | Lifecycle | start/stop/status/doctor 经 Node CLI | doctor+health 无 DSH |
| **5** | **PR-E1.5** ✅ | Admin API / CLI 基础 | Node CLI：`config` / `backup` / `restore` | 无 GUI 也可运维 |

**为何备份演练第一：** 直接检验数据边界；若无法可靠恢复，再加 Observation/Import 只是扩大风险。  
**注意：** 现有 `cli backup` **只证明能生成文件**；E1.2 必须 **真正 restore 并验证**。

### 4.1 E1.2 检查清单（强制）

1. 明确备份范围（db / 必要 runtime 元数据）  
2. DB 一致性（SQLite backup API 已用则保留）  
3. 配置与必要文件  
4. **独立目录**恢复  
5. 记录数与关键关联校验  
6. 恢复后检索/health  
7. 损坏与中断处理（至少一项）  
8. 重复恢复  
9. 可复现演练报告（写入 `docs/` 或 `tmp/` 并归档）  

---

## 5. 后续 Phase（依赖就绪后再拆 PR）

### P2 Cognitive Core 解耦

Identity → Observation Contract → Evidence → Memory Service Contract → Memory Bank 基础 → Authority Model  

验收：核心可脱离 DSH 调用；Adapter 不承担核心业务；多 Agent 主体可区分。

### P3 Universal Interoperability

Canonical Model → REST v1 收口 → AuthZ → MCP → Events → TS/Python SDK（薄）  

验收：**不依赖 DSH 的测试 Agent** 完成认证、观察、检索、反馈、撤销。

### P4 Component Infrastructure（D8）

Manifest → Registry → Resolver → Installer → Config → Lifecycle → Profiles  

验收：安装→权限审查→配置→启用→健康→禁用→升级→失败回滚。  
**先本地/Git 来源；不做社区市场。**

### P5 Migration & Adoption

Interchange → Preview → Mapping/Conflict → Execute → Adoption Readiness → Authority Transfer  

Migration ≠ Adoption（分开验收）。

### P6 Cognitive Intelligence

顺序：Temporal → Context → Relationship → Conflict → Adaptive Retrieval →（P2）Emotion / Learning  

禁止先情绪后证据时间。

### P7 集成验收

| 对象 | 重点 |
| --- | --- |
| DSH/大肥鱼 | 兼容；核心业务不重复 |
| 外部 Agent A | REST/SDK |
| 外部 Agent B | MCP |
| 独立 CLI | 无 DSH |
| 多 Agent | 身份/权限/审计隔离 |

---

## 6. D6 裁切（待签字）

| 能力 | 版本 |
| --- | --- |
| 多 Agent 接入 **同一** Node（身份/权限/审计） | **2.0 必须** |
| 多 Node 完整自治联邦 / PCIP 生产 / P2P / Relay | **2.1+** |
| 跨用户知识市场 | 更后 |

裁切后 **禁止**在 2.0 完成报告将联邦标为已完成。

---

## 7. 测试体系（六类）

Unit · Contract · Integration · E2E（A 无 DSH / B DSH / C 外 Agent / D 多 Agent / E 组件 / F 迁移）· Recovery · Security  

详情门槛见 §8。

---

## 8. 2.0 GA Readiness Gate

| Gate | 条件 | 必要性 |
| --- | --- | --- |
| G1 Node Independence | 不依赖 DSH 独立运行 | 必须 |
| G2 Storage Safety | 备份恢复与数据验证 | 必须 |
| G3 Cognitive Core | 记忆生命周期可验证 | 必须 |
| G4 Interoperability | ≥1 外部 Agent 直连 | 必须 |
| G5 Component Management | 安全安装/配置/停用 | 必须 |
| G6 Governance | 身份、授权、撤销、审计 | 必须 |
| G7 Migration | 预览、批准、导入、验证 | 必须 |
| G8 Compatibility | DSH Adapter + 旧数据路径 | 必须 |
| G9 Documentation | 安装/管理/备份/接入 | 必须 |
| G10 Ecosystem Federation | 跨 Node 联邦 | **可裁切 → 2.1+** |

---

## 9. 当前开工面（Adoption Cutover + Runbook · 2026-10-30）

1. ~~Phase 1–6 最小面 / 多 Agent / D8~~ PR #3–#10  
2. ~~Authority Cutover~~ preview/execute（confirm）；CLI `authority` / `adopt export`；REST cutover + adoption/export  
3. ~~Adoption Runbook~~ `docs/MNEMOSYNE_ADOPTION.md`；备份 drill `--archive` 证据  
4. ~~现网备份 V8 / Admin Adoption UI / E6.5~~；~~CRUD 执法 / Storage Provider / MCP confirm / E6.2 / SSE / TS SDK~~；全量收纳与联邦仍不纳入  
5. D8 市场 / D6 跨 Node 联邦仍禁止默认为已完成

---

## 10. 相关文档索引

| 文档 | 角色 |
| --- | --- |
| MASTER_PLAN | 目标与阶段冻结 |
| ARCHITECTURE | 五层/五者/D8/A+B+C |
| CAPABILITY_MATRIX | 真实缺口与 Epic 账本 |
| CODE_AUDIT | 本轮代码基线 |
| ENGINEERING_CONSTRAINTS | 安全三原则 + 组件/Agent 执法 |
| NODE_OPERATIONS | 安装/备份/恢复操作与演练 |
| COMPONENT_SPEC | Manifest/生命周期（设计） |
| INTERCHANGE_SPEC | 外部交换模型（设计） |

---

## 11. 附录：E0.6 范围裁切记录（执行启动 · 2026-10-30）

| 能力 | 归属 |
| --- | --- |
| 单 Node 独立运行 / 配置 / 备份恢复 | **2.0 必须** |
| 单 Node 多 Agent 接入（身份/权限/审计） | **2.0 必须** |
| A+B+C 最小集（认知核心 + 组件管理最小面 + 非 DSH 接入） | **2.0 必须** |
| 多 Node 联邦 / PCIP 生产 / P2P / Relay | **2.1+**（禁止在 2.0 完成报告标已完成） |

本记录随 Phase 1 执行启动写入；若产品负责人修改裁切，须更新本表并留日期。
