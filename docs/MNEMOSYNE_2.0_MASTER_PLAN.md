# Mnemosyne 2.0 — Master Implementation & Architecture Roadmap

**项目定位：** Personal Cognitive Infrastructure  
**项目名称：** Mnemosyne  
**目标版本：** 2.0  
**规划性质：** 总体架构与实施路线（正式冻结稿）  
**文档状态：** Frozen Target（2026-10-30；同日落地更新：保留资产 + 独立 Node + 开放接入）  
**总体战略：** Build First → Validate → Complete → Adopt Later  
**落地性质：** 在现有仓库上演进，**不是**推倒重来或另起项目。

> 配套文档：  
> - [架构边界](MNEMOSYNE_2.0_ARCHITECTURE.md)  
> - [能力矩阵与差距](MNEMOSYNE_2.0_CAPABILITY_MATRIX.md)  
> - [实施计划（Epic/PR）](MNEMOSYNE_2.0_IMPLEMENTATION_PLAN.md)  
> - [代码审计基线](MNEMOSYNE_2.0_CODE_AUDIT.md)  
> - [Node 运维/演练](MNEMOSYNE_NODE_OPERATIONS.md) · [组件规范草案](MNEMOSYNE_COMPONENT_SPEC.md) · [交换模型草案](MNEMOSYNE_INTERCHANGE_SPEC.md)  
> - 窄义「图式/Gate」层说明（旧稿，从属本总方案）：[MNEMOSYNE_2.0.md](MNEMOSYNE_2.0.md)

---

## 0. 冻结声明

自本文件起，**Mnemosyne 2.0 的正式目标、架构边界、阶段划分、用户收纳门槛**以此文档及两份配套文档为准。

| 规则 | 说明 |
| --- | --- |
| 目标冻结 | 2.0 要建成什么、不建什么，以本文第 1 / 3 / 11 / 13 节为准 |
| 基线诚实 | 现状以仓库可验证证据为准；**不得**把规划或外部未入库产物写成已实现 |
| 实施纪律 | 先完成 Phase 0（架构冻结 + Capability Matrix），再按依赖开 Epic；**禁止同时开启七个开发方向** |
| 兼容纪律 | 稳定契约不得无计划破坏；扩展走版本评估 |
| 收纳纪律 | 未通过 **2.0 Readiness Gate** 前，不正式收纳用户及其历史记忆 |

内部开发测试、合成数据、受控测试节点 ≠ 正式用户收纳。

---

## 1. 项目总体目标

### 1.1 定位

Mnemosyne 2.0 建设一套**独立、自治、可扩展、可互操作**的个人认知基础设施。

它不是普通 Agent Memory Plugin，也不是某一 Agent Framework 的附属记忆服务。

**双重目标（同时成立，禁止混为一谈）：**

1. **应用集成：** 以 **DSH /「大肥鱼」为首个核心宿主**，社区开源插件扩展宿主能力，支撑拟人化、可持续积累、可迁移、可组合的个人记忆与知识使用。  
2. **开放基础设施：** 任何人可独立配置、安装、组合、扩展 **Mnemosyne Node**；其他 Agent / 工具经稳定接口直连，**不经过 DSH**。

每个用户拥有自己的 **Mnemosyne Node**，控制记忆、知识、身份、访问权限与认知数据。外部 Agent / Framework / Plugin / App / Service 仅可在授权下接入，**不得**直接访问个人记忆库。

Mnemosyne 应当成为：

1. 个人长期记忆的权威存储  
2. 个人知识与经历的组织基础设施  
3. Agent 的长期上下文与认知基础设施  
4. 不同 Agent / 应用之间的个人数据互操作层  
5. 授权知识交换的基础  
6. 可迁移、可备份、可恢复、用户自主控制的数据系统  

### 1.1.1 2.0 完成的三项必要条件（A+B+C）

| ID | 条件 | 说明 |
| --- | --- | --- |
| **A** | Cognitive Infrastructure | 独立记忆、知识、关系、证据、检索、治理与认知管理 |
| **B** | Open Component Infrastructure | 统一组件契约、注册、发现、配置、安装、依赖与兼容（**D8**；≠ DSH 插件生态） |
| **C** | Universal Agent Interoperability | 授权 Agent/工具可不经 DSH 接入 |

仅有 A → 独立记忆软件；A+C 无 B → 有 API 但难安装组合；**必须 A+B+C**。  
跨 Node 联邦可裁切出首个 GA；**不可**因此省略单 Node 独立运行、组件管理最小集、外部 Agent 直连。

五者边界（Node / DSH / DSH 社区插件 / Mnemosyne Components / 外部 Agent）见 [ARCHITECTURE §2](MNEMOSYNE_2.0_ARCHITECTURE.md)。

### 1.2 核心战略

**Build First → Validate → Complete → Adopt Later**

1. 完整建设 2.0 范围内架构与能力  
2. 跨模块集成与端到端测试  
3. 迁移、兼容、备份、恢复与治理就绪  
4. 通过 **2.0 Readiness Gate**  
5. **然后**才正式收纳用户与历史记忆  

### 1.3 设计原则（冻结）

1. Personal Node Ownership  
2. Local First  
3. User Data Sovereignty  
4. No Central Memory Database  
5. Protocol First  
6. Contract First  
7. Language Agnostic  
8. Framework Agnostic  
9. Universal Interoperability  
10. Replaceable Components  
11. Capability Based Security  
12. Provenance Preservation  
13. Reversible Operations  
14. Backward Compatibility  
15. Modular Monolith First（先模块化单体，不提前拆微服务）

---

## 2. 本仓库验证后的工程基线

> **重要更正：** 原稿中「P3 Universal Ecosystem Foundation / Foundation 1.0 Stabilized / PR #18 / `foundation-0.1.0` / `feat/mnemosyne-2.0-p3-ecosystem` / `docs/ENGINEERING_CONSTRAINTS.md`」在 **本仓库（canyueY/MurasamePet）无法验证**。  
> 下表以 **2026-10-30 仓库盘点** 为准。若那些产物存在于其他仓库，须单独登记为「外部依赖」，不得默认已合并到本仓。

### 2.1 已验证基线（本仓）

| 项目 | 验证状态 | 证据 |
| --- | --- | --- |
| 桌宠宿主 + 多记忆层并行 | 运行中 | `Murasame/`、`docs/MEMORY_MAP.md` |
| 外置认知记忆服务（模块化单体） | Partial→强 | `services/cognitive-memory/`（SQLite、REST、Outbox/Tasks、检索、认知规则） |
| DSH 插件宿主适配 | Partial | `_dsh_plugins/dsh-cognitive-memory/`（副记忆试用位，见 `TRIAL.md`） |
| 宿主桥接 | Implemented | `Murasame/cognitive_memory_bridge.py`、`memory_orchestrator.py`、`gatekeeper_memory.py` |
| A-MEM 并行 / 兼容 | Implemented | `a_mem_bridge.py`；`replace_a_mem` 默认 false |
| 外部只读窥视 | Implemented | `mnemosyne_compat.py`（日记/mementoQ，禁止双向同步） |
| Mnemosyne 1.x 升级轨（检索/一致/ChangePlan/情绪/灰度） | Partial | `docs/MNEMOSYNE_UPGRADE.md` + `docs/p0`–`p5` + CM API |
| 窄义 2.0（Schema + Capability Gate） | Partial / MVP | `docs/v2/*`、`cognition/schema_*`、`governance/capability_gate.py` |
| A-MEM→CM 迁移引擎 | Implemented-lite（已合入 main） | PR [#1](https://github.com/canyueY/MurasamePet/pull/1) merge `d96c1ad`；`cognitive_memory/migration/` |
| Admin 认知记忆面板 | Implemented | `CognitiveMemoryPanel.vue` |
| Foundation / PCIP / Component Contract 包 | **Missing** | 全仓无匹配文档与代码 |
| Engineering Constraints 文档 | **Missing** | 无 `docs/ENGINEERING_CONSTRAINTS.md` |
| Production Hardening / P3.2（生态 Foundation） | **Not in repo** | — |

### 2.2 必须保留的安全原则（即使 Constraints 文件尚未入库）

先以本 Master Plan 冻结三条原则；后续补文件时不得削弱：

1. **部署不默认放宽** — 部署与接入不得隐式扩大权限  
2. **字段不等于执法** — `allow_train` / `allow_forward` / `allow_store` 声明 ≠ 已执行  
3. **通信不等于可信** — 连通 / 注册 / 协议通过 ≠ 对端可信  

### 2.3 当前阶段边界（立即生效）

**继续：**

- 认知记忆服务与宿主桥接的稳定维护  
- 契约 / 回归测试补强  
- Bug 修复与兼容维护  
- Phase 0 文档与 Capability Matrix（本轮）  
- 受控测试节点与合成数据试验  

**当前不启动：**

- 正式用户大规模收纳 / 停用 A-MEM  
- Production Hardening 专项（无触发条件）  
- P2P / Relay 生产化  
- 中心化个人记忆库  
- 微服务拆分  
- 默认双向同步  
- 七条开发分支同时全面开工  

---

## 3. 总体架构（冻结目标）

### 3.1 三层逻辑架构

| 层 | 名称 | 职责摘要 |
| --- | --- | --- |
| **L1** | Runtime & Storage Foundation | Node 运行、存储、事务、事件、备份/恢复、迁移升级、健康诊断 |
| **L2** | Personal Cognitive Infrastructure | Identity / Observation / Evidence / Memory / Retrieval / Relationship / Cognitive / Learning / Federation / Governance / Interoperability（逻辑引擎，非强制微服务） |
| **L3** | Open Agent Ecosystem | Agent 身份与发现、能力发现、知识交换、Federation；可选 P2P/Relay（须专项安全验收） |

### 3.2 八个建设领域

| ID | 领域 | 2.0 职责 |
| --- | --- | --- |
| D1 | Runtime & Storage | Node 运行、存储、事务、备份恢复；**独立于 DSH 的生命周期** |
| D2 | Cognitive Foundation | Observation、Evidence、Memory、Retrieval、Relationship、Memory Bank |
| D3 | Cognitive Intelligence | 分类、抽取、冲突、巩固、晋升、时序推理、反馈学习 |
| D4 | Universal Interoperability | API/Events/SDK/MCP/PCIP；**非 DSH Consumer** |
| D5 | Memory Migration & Adoption | 迁移、导入导出、兼容、权威切换 |
| D6 | Open Agent Ecosystem | Agent 互联、知识交换、Federation（可裁切） |
| D7 | Governance & Operations | 授权、审计、隐私、生命周期、运维 |
| **D8** | **Distribution & Composition** | Installer、Config、Manifest、Component Manager、Profiles、Compatibility Gate（**≠ DSH 插件系统**） |

详细模块边界见 [ARCHITECTURE](MNEMOSYNE_2.0_ARCHITECTURE.md)。逐项现状见 [CAPABILITY_MATRIX](MNEMOSYNE_2.0_CAPABILITY_MATRIX.md)。

**Node 独立性：** 独立配置、存储根、进程生命周期与管理接口为 **2.0 硬性架构约束**。  
**DSH 关系：** 首个重要集成宿主，**不是**核心运行时依赖。

---

## 4. 七阶段实施路线（冻结）

| Phase | 名称 | 退出条件（摘要） |
| --- | --- | --- |
| **0** | Architecture Freeze | 职责/状态/依赖/验收齐备；本三份文档审阅通过 |
| **1** | Runtime & Cognitive Foundation | 独立 Node：初始化→观察→证据→记忆→检索→备份恢复闭环 |
| **2** | Cognitive Intelligence | 测试样本可证明：事实/推断/外部知识/冲突/未知可区分 |
| **3** | Universal Interoperability | ≥2 种技术栈组件经稳定契约完成受权读写与事件 |
| **4** | Memory Migration & Adoption | ≥3 种数据形态同引擎导入/校验/恢复/导出；≥1 旧 API 经 Compatibility Gateway |
| **5** | Open Agent Ecosystem | 两独立 Node 在授权与范围内交换知识，含来源/过期/撤销/拒绝 |
| **6** | Integration & 2.0 Readiness | 通过 Readiness Gate；无未标记关键缺口 |

**主依赖链：**  
Runtime/Storage → Cognitive Foundation → Cognitive Intelligence → Interoperability → Migration & Adoption → Agent Ecosystem → Integration。

允许设计并行；**禁止**为并行而复制/绕过核心 Service。

---

## 5. 工程工作流（Track）

| Track | 职责 | 现在 |
| --- | --- | --- |
| **A** Foundation Maintenance | CI、契约回归、Bug、兼容、安全边界回归 | 持续（以本仓 CM+宿主为准，待真正 Foundation 入库后再对齐） |
| **B** Core Infrastructure & Cognition | Runtime、Storage、认知基础与智能、Memory Bank | Phase 0 后启动设计；实现跟 Phase 1–2 |
| **C** Interoperability & Migration | API/SDK、Interchange、Migration、Compatibility | 迁移引擎已起步；完整 D4/D5 按 Phase 3–4 |
| **D** Agent Ecosystem & Governance | PCIP、Federation、治理、跨节点授权 | 仅设计预研；实现跟 Phase 5 + Gate |

---

## 6. Git / PR 策略（冻结）

### 6.1 稳定基线

- 当前默认集成线：`main`（含已合并的迁移引擎 PR #1）  
- **不存在**本仓分支 `feat/mnemosyne-2.0-p3-ecosystem`；若外部有，须显式镜像/登记后再引用  

### 6.2 建议工作分支（按需创建，禁止一次全开）

| 分支（规划名） | 对应 | 何时开 |
| --- | --- | --- |
| `design/mnemosyne-2.0-master-plan` | 文档与矩阵（可选） | Phase 0 |
| `feat/mnemosyne-2.0-runtime` | D1 | Phase 1 |
| `feat/mnemosyne-2.0-cognitive-foundation` | D2 | Phase 1 |
| `feat/mnemosyne-2.0-cognitive-intelligence` | D3 | Phase 2 |
| `feat/mnemosyne-2.0-interoperability` | D4 | Phase 3 |
| `feat/mnemosyne-2.0-memory-migration` | D5（相对已有 2.1 引擎的增强） | Phase 4 |
| `feat/mnemosyne-2.0-agent-ecosystem` | D6 | Phase 5 |

已有：`feat/mnemosyne-2.1-memory-migration`（已合并）— 记为 D5 起步，**不等于** Phase 4 完成。

### 6.3 PR 必备字段

Scope · Architecture Impact · Schema Impact · API Impact · Security Impact · Migration Impact · Tests · Compatibility · Rollback Plan  

禁止单 PR 同时大规模改 Runtime + Memory + Governance + Interoperability。

---

## 7. 2.0 Readiness Gate（用户收纳门槛）

正式收纳用户前，须通过（细节清单见 CAPABILITY_MATRIX §Readiness）：

| 门 | 内容 |
| --- | --- |
| A | Node 安装/配置/启停/健康/升级/备份/恢复/故障 |
| B | Observation / Evidence / Memory / Retrieval / Relationship / Memory Bank |
| C | 事实 vs 推断、冲突保留、晋升条件、反馈不无条件覆盖 |
| D | 契约稳定、Schema 版本、受权接入、未授权拒绝 |
| E | 多格式迁移、去重冲突、幂等续传回滚、权威切换 |
| F | Agent/Node 身份、发现、授权交换、溯源、撤销（若纳入 2.0） |
| G | 单测/集成/E2E/契约/安全/干净环境/备份恢复/文档与 Runbook |
| H | 用户所有权、可预览迁移、可选范围、不改旧库、可导出、可切权威、无隐式中心库 |

**未通过 Gate → 禁止正式用户 Adoption。**

---

## 8. 明确不做（范围防火墙）

- 不启动未入库的「P3.2 / 独立 Production Hardening」除非触发条件成立并单独立项  
- 不建中心化用户记忆库  
- 不提前拆微服务  
- 不一把实现全部 Provider  
- 不默认双向同步  
- 不自动扫描用户全盘  
- 不默认跑不可信第三方代码  
- 不把 MCP 当唯一 API  
- 不把外部 Agent 内容直接升为 Active Memory  
- 迁移未验证前不停用旧系统  
- Readiness Gate 前不正式收纳用户  

---

## 9. 当前执行顺序（立即）

1. **完成现状盘点** → 本轮已完成，结果写入 CAPABILITY_MATRIX  
2. **冻结总体架构** → 本文 + ARCHITECTURE（审阅即冻结）  
3. **拆分 Epic / PR** → 见 CAPABILITY_MATRIX §Epic  
4. **建立并行工作流** → 仅 Track A 持续；B/C 设计可开；D 仅文档预研  
5. **按依赖实现** → 先 D1/D2 闭环，再 D3，再 D4/D5 增强，再 D6  
6. **整体集成验收** → Phase 6  
7. **正式发布 2.0 → 用户收纳**  

---

## 10. 最终定义

Mnemosyne 2.0 交付的不是单个 API、插件或 SQLite 文件，而是完整的个人认知基础设施：独立运行、长期记忆、理解与组织、检索与演化、外部接入、迁移兼容、节点协作、数据主权、备份恢复升级。

**最终战略：**

> 先完成基础设施，再迁移历史记忆。  
> 先完成认知能力，再开放外部接入。  
> 先完成互操作和治理，再建设开放生态。  
> 先验证整体系统，再正式收纳用户。  
>
> **Mnemosyne 2.0 Complete → User Adoption.**
