# Mnemosyne 2.0 — Architecture

**文档状态：** Frozen Target Boundaries（2026-10-30；同日补充：五者边界 / Distribution / A+B+C）  
**上位文档：** [MASTER_PLAN](MNEMOSYNE_2.0_MASTER_PLAN.md)  
**差距对照：** [CAPABILITY_MATRIX](MNEMOSYNE_2.0_CAPABILITY_MATRIX.md)

本文冻结 **模块边界、数据流、依赖与接口分层**。实现可分期，边界不可被各模块私自改写。

---

## 0. 双重目标（同时成立，禁止混为一谈）

Mnemosyne **不是**单纯的 DSH 记忆插件。正式目标是两层同时成立：

| 层 | 目标 | 不是 |
| --- | --- | --- |
| **应用集成** | 以 **DSH /「大肥鱼」为首个核心宿主**，用社区开源插件扩展宿主能力，在拟人化场景里持续积累、可迁移、可组合地使用个人记忆与知识 | 把 Mnemosyne 做成只能活在 DSH 插件树里的附属模块 |
| **开放基础设施** | 任何人可 **独立配置、安装、组合、扩展** Mnemosyne Node；其他 Agent / 工具经稳定接口直连，**不经过 DSH** | 把「能被桌宠调用」等同于「开放基础设施已完成」 |

以「大肥鱼」为例的三层对应：

| 层 | 角色 | 负责 |
| --- | --- | --- |
| **应用宿主层** | 大肥鱼 / DSH | 核心大脑、Agent 编排、交互界面、**DSH 社区插件生态** |
| **认知基础设施层** | Mnemosyne Node | 个人记忆/知识/关系/证据/检索/学习与治理（权威认知资产） |
| **开放接入层** | Universal Interoperability | REST / SDK / MCP / Events / CLI / PCIP — 其他 Agent 可不经 DSH 使用 Node |

硬约束：

- DSH **可以是**首个重要宿主与主要使用者。  
- DSH 社区插件可为宿主提供模型、工具、检索、自动化等能力。  
- **Mnemosyne 不得依赖 DSH 插件系统才能运行。**  
- 其他 Agent **可以绕过 DSH** 直连 Mnemosyne。  
- 用户可只装 Node，也可把同一 Node 接到 DSH 或其他 Agent。

---

## 1. 逻辑总图

```
┌─────────────────────────────────────────────────────────────────┐
│ 应用宿主（例：大肥鱼 / DSH）· 其他 Agent / 工具 / App                 │
│  DSH 社区插件 ≠ Mnemosyne Components（见 §3）                      │
└───────────────────────────────▲─────────────────────────────────┘
                                │ Adapter / Consumer（授权）
┌───────────────────────────────┴─────────────────────────────────┐
│ L3 Open Agent Ecosystem + 开放接入                                 │
│  Agent Identity · Discovery · Exchange · Federation · (P2P*)    │
│  REST / SDK / MCP / Events / CLI / PCIP                           │
└───────────────────────────────▲─────────────────────────────────┘
                                │ 授权契约（不经 DSH 亦可）
┌───────────────────────────────┴─────────────────────────────────┐
│ L2 Personal Cognitive Infrastructure                            │
│  Identity · Observation · Evidence · Memory · Retrieval         │
│  Relationship · Cognitive · Learning · Governance · Interop     │
│  Memory Bank（Personal / Projects / Knowledge / Shared / …）      │
└───────────────────────────────▲─────────────────────────────────┘
                                │ Service Contract（禁止直连 DB）
┌───────────────────────────────┴─────────────────────────────────┐
│ L1 Runtime & Storage + Distribution & Composition（§5）           │
│  Runtime · Config · Storage Provider · Tx · Outbox/Jobs         │
│  Installer · Component Manager · Profiles · Compatibility Gate  │
│  Index · Backup/Restore · Schema Migration · Health             │
└─────────────────────────────────────────────────────────────────┘

* P2P/Relay：仅专项安全验收后开放
```

**部署形态（2.0 默认）：** Modular Monolith（单 Node 进程 / 单逻辑服务），内部按引擎分包；不提前拆微服务。

**产品默认体验：** Node 是主体，组件按需安装（见 §6）；积木式「只装部分模块」为高级扩展，不得成为破坏 Node 一致性的默认路径。

### 1.1 五层逻辑视图（与三层等价展开）

落地沟通可用五层（**仍是逻辑层，不是五个微服务**）：

| 层 | 名称 | 职责 | 不应负责 |
| --- | --- | --- | --- |
| L5 | Host Ecosystem | DSH/大肥鱼、外部 Agent、桌面/Web/CLI 编排与交互 | 直接管理核心 DB |
| L4 | Interoperability | REST/MCP/SDK/Events/认证 | 重做记忆业务 |
| L3 | Composition (D8) | Manifest/安装/依赖/Profiles/生命周期 | 代替认知引擎 |
| L2 | Cognitive Core | Identity→Governance 等认知引擎 | 桌宠 UI / 模型调度 |
| L1 | Runtime & Storage | 进程、配置、存储、事务、备份恢复 | 认知业务规则 |

三条硬约束：**Node 不依赖宿主** · **宿主不拥有 Node** · **组件不绕过 Service Contract**。

执行计划见 [IMPLEMENTATION_PLAN](MNEMOSYNE_2.0_IMPLEMENTATION_PLAN.md)；代码基线见 [CODE_AUDIT](MNEMOSYNE_2.0_CODE_AUDIT.md)。

---

## 2. 五者边界（冻结）

下列五者职责不同，**禁止在实现与文档中混称「插件」而不加限定词。**

| # | 主体 | 是什么 | 不是什么 | 本仓典型落点 |
| --- | --- | --- | --- | --- |
| 1 | **Mnemosyne Node** | 独立个人认知基础设施：自有配置、存储、生命周期、管理接口与认知引擎 | DSH 的一个插件进程附属品 | 目标：`services/cognitive-memory` 产品化；现状仍常被宿主拉起 |
| 2 | **DSH / 大肥鱼（宿主）** | Agent 编排、交互、拟人化场景；**首个重要集成宿主** | Mnemosyne 的核心运行时依赖 | `Murasame/`、桌宠 Pet、DSH Host |
| 3 | **DSH 社区插件** | 扩展**宿主 Agent** 的能力（模型、搜索、浏览器、工具、自动化…） | Mnemosyne 的 Component / 存储实现 | `_dsh_plugins/*`（除 Adapter 外） |
| 4 | **Mnemosyne Components** | 扩展 **Node** 的认知基础设施能力（Embedding、Reranker、Extractor、Storage Provider、检索算法、Extension…） | DSH 插件包的换皮 | 目标：Node 侧 Manifest + Manager；现状多为内嵌代码 |
| 5 | **外部 Agent / 工具** | 经开放接入层授权使用同一 Node 的 Consumer | 必须经过 DSH 才能访问记忆 | 未来任意 REST/SDK/MCP 客户端；现有 Admin / Bridge 是早期 Consumer |

### 2.1 协作示例（搜索 → 记忆）

1. **DSH 网页搜索插件** 产生网页结果（工具能力）。  
2. **DSH / 大肥鱼** 决定是否采纳、如何编排（Agent）。  
3. 经 **DSH Adapter** 调用 Mnemosyne，把结果提交为带 provenance 的 **Observation**。  
4. **Mnemosyne** 决定保存、关联、检索，以及是否有足够证据晋升为长期 Memory。  

→ 工具产生能力，Agent 决策编排，Mnemosyne 管理长期认知资产。三者不可互相取代。

### 2.2 硬性禁止

- 禁止让 Node 的 Storage / Schema 迁移逻辑写进某个 DSH 插件的私有实现且无法独立运行。  
- 禁止「安装 DSH 插件」被文档表述成「安装了 Mnemosyne Component」。  
- 禁止其他 Agent 接入时要求必须加载 DSH 插件树。  
- 允许：同一份算法以 **DSH 插件** 与 **Mnemosyne Provider** 两种包装出现，但须有各自 Manifest，且 Node 只认后者契约。

---

## 3. 两套组件生态（禁止混成一套）

| 生态 | 负责 | 例子 | 生命周期由谁管理 |
| --- | --- | --- | --- |
| **DSH 社区插件** | 扩展宿主 Agent | 模型、搜索、浏览器、工具、自动化 | DSH / Cordis（或宿主）插件系统 |
| **Mnemosyne Components** | 扩展认知基础设施 | Embedding、Reranker、Extractor、Storage Provider、检索算法、Cognitive Extension | **Node** Component Manager |
| **Mnemosyne Adapters** | 连接外部系统到 Node | DSH Adapter、其他 Agent Adapter、数据导入 Adapter | Node（Adapter 也是一种 Component） |

交集只允许发生在 **Adapter / 明确双包装** 层；**不得**共用一套「插件目录 = 认知组件目录」的默认假设。

社区能力复用路径：

> 外部能力 →（可选）DSH 插件服务宿主 → **Adapter** 译成 Observation / Provider 调用 → Node 契约  
> 或：外部能力 → **直接** Mnemosyne Provider/Extension（不经 DSH）

---

## 4. A + B + C：2.0 必须同时成立的三项条件

| ID | 条件 | 决定什么 | 缺了会变成什么 |
| --- | --- | --- | --- |
| **A** | Cognitive Infrastructure | 独立记忆、知识、关系、证据、检索、治理与认知管理 | 只是个记事本/向量库 |
| **B** | Open Component Infrastructure | 统一组件契约、注册、发现、配置、安装、依赖解析、生命周期与兼容性 | 有 API 的记忆服务，但用户难以安装与组合 |
| **C** | Universal Agent Interoperability | 任意授权 Agent/工具/应用经稳定接口接入，**不依赖 DSH** | DSH 专用记忆后端，不是开放基础设施 |

**只有 A+B+C 同时成立，才符合 Mnemosyne 2.0 正式目标。**  
跨 Node 联邦（原 D6 生产网络）可在首个 GA **显式裁切**到后续版本；**不得**因此省略：单 Node 独立运行、组件管理（B 的最小集）、外部 Agent 直连（C 的最小集）。

---

## 5. Distribution & Composition（分发与组合）

逻辑能力域（**不是**新的认知引擎，也**不**要求拆成微服务）。职责：把基础设施变成可安装、可配置、可扩展的产品。

| 能力 | 职责 |
| --- | --- |
| Node Installer | 安装、初始化、升级 Node |
| Configuration Manager | Node / 存储 / Provider / 权限 / 数据来源配置 |
| Component Manifest | 组件身份、版本、依赖、接口、能力声明 |
| Component Manager | 安装、启用、停用、升级、卸载组件 |
| Dependency Resolver | 版本、依赖、兼容性 |
| Composition Profiles | 场景模板（起点，不锁定用户选择） |
| Migration / Import | 导入外部数据，保留来源与映射（与 D5 引擎衔接） |
| Compatibility Gate | 组件 ↔ Node 版本 / 协议 / 权限是否兼容 |

### 5.1 组合 Profile（模板 ≠ 锁定）

| Profile | 含义 |
| --- | --- |
| **Standalone** | 只运行 Mnemosyne Node |
| **DSH Profile** | Node + DSH Adapter + 适用 Provider |
| **Personal Agent Profile** | Node + 其他 Agent Adapter |
| **Custom** | 用户自选组件组合 |

配置模板只是安装起点，**不得**锁定后续组件选择。

### 5.2 「合并」的三种语义（禁止混用）

| 语义 | 含义 | 要求 |
| --- | --- | --- |
| **组件合并** | 组合不同 Component 提供的能力 | 经 Manifest / Resolver / Compatibility Gate；不是把代码或 DB 文件随意拼盘 |
| **记忆合并** | 导入不同来源的记忆 | 保留来源、原始 ID、冲突与映射；走 Migration / Interchange |
| **Node 合并** | 整合不同个人数据空间 | 必须预览、冲突处理、**用户批准**；禁止自动覆盖 |

---

## 6. 安装体验四层与产品默认形态

1. **独立安装** — 可不先装 DSH，直接安装 Node。  
2. **独立配置** — 存储、模型/Embedding、检索策略、Memory Bank、权限、数据来源可配。  
3. **组件组合** — 安装/启用/停用/替换/组合 Provider、Adapter、Extension。  
4. **多宿主接入** — 同一 Node 可同时服务 DSH、其他 Agent、桌面工具、Web App、自建程序（按权限分能力）。

**默认产品形态（冻结）：**

1. **Node 为主体，组件按需安装** — 保证完整 Node 一致性与治理面。  
2. **积木式部分能力组合** — 作为高级扩展；不得绕过 Service Contract，不得形成第二套权威存储。

---

## 7. 与本仓现状的映射

| 2.0 逻辑模块 | 本仓当前位置 | 边界说明 |
| --- | --- | --- |
| Node Runtime | `cognitive_memory.main` / `bootstrap` + 宿主拉起 | 尚无独立「Node 产品」安装器；与桌宠进程耦合；**违背硬性独立约束的现状** |
| Distribution & Composition | Missing | 无 Installer / Manifest / Component Manager；DSH 插件目录 ≠ Node 组件目录 |
| Storage Provider | `storage/db.py` + SQLite | 仅默认 Provider；无 Provider Interface 正式契约 |
| DSH Adapter | `_dsh_plugins/dsh-cognitive-memory`、`cognitive_memory_bridge.py` | 宿主适配存在；易被误称为「Mnemosyne 插件本体」 |
| Observation | `observations` 表 + `capture_observation` | 有；导入/外部输入应先入 Observation |
| Evidence | `memory_evidence` 表 | **表级**存在；非独立 Evidence Engine |
| Memory | `memories` + versions + status | 有生命周期字段；Bank 隔离缺失 |
| Retrieval | `retrieval/*` + FTS5 | 全文/混合规则有；向量/实体检索 Provider 化不足 |
| Relationship | `memory_relations` | 有边类型；图谱/冲突处理不完整 |
| Cognitive Intelligence | `cognition/*` | 规则巩固/ChangePlan/情绪/Schema MVP；非完整可验证智能 |
| Governance | `governance/capability_gate.py` | Gate+审计表；隐私/同意/撤销模型不完整 |
| Interoperability | REST + MCP | 无 Component Registry / PCIP / 多语言 SDK |
| Migration | `migration/*`（PR #1） | A-MEM/JSONL 引擎起步；Interchange/Mem0/权威切换未完成 |
| Host Adapter | `Murasame/*_bridge` + `_dsh_plugins/dsh-cognitive-memory` | 桌宠/DSH 接入；≠ Universal Consumer SDK |
| Legacy LT | A-MEM / Mem0 / Neko | 并行；Adoption 完成前不得默认权威 |

---

## 8. 引擎边界（L2）

### 8.1 Identity Engine（目标）

- User / Node / Agent / Entity / External mapping  
- **现状：** Missing（无独立模块）  
- **约束：** 权限与 Bank、跨节点交换均依赖此引擎；不得用「字符串用户名」冒充身份模型  

### 8.2 Observation Engine

- 入站：对话、用户输入、Agent 输出、外部事件、文档、导入记忆、外部知识  
- **硬规则：** 外部输入 → Observation；**不**自动变可信长期 Memory  

### 8.3 Evidence Engine

- Provenance、支持/反对证据、置信、时效、验证态  
- **硬规则：** 证据与记忆内容分离；模型输出 ≠ 用户事实  

### 8.4 Memory Engine

- 类型 / 状态 / 版本 / 晋升 / 废弃 / 归档 / 保留  
- 区分 Observation、Evidence、Episode、长期 Memory  

### 8.5 Retrieval Engine

- 全文 / 向量 / 时间 / 实体 / 关系 / 上下文 / 混合  
- Embedding / Reranker / Vector Store 经 **Provider** 替换  

### 8.6 Relationship Engine

- 实体、关系、时序、跨记忆引用、关系溯源与冲突  

### 8.7 Cognitive / Learning Engine

- 分类、抽取、实体消歧、冲突、巩固、情节构造、晋升、整合、时序推理、衰减、反馈学习  
- 必须保留：原始 Observation、Evidence、Source、变换史、Provider 元数据、验证态、晋升决策  

### 8.8 Memory Bank（2.0 正式范围）

逻辑空间，**不是**每 Agent 一库：

| Bank | 用途 |
| --- | --- |
| Personal | 个人记忆（默认权威 LT） |
| Projects | 项目上下文 |
| Knowledge | 结构化知识 |
| Shared | 显式共享 |
| Public | 公开可分发 |
| System | 系统/运维 |

每 Bank：Access / Types / Retrieval Scope / Retention / Cross-ref / Sharing / Export / Training Policy。  

**硬规则：** Shared/Public **不得**自动污染 Personal。

### 8.9 Federation / Interoperability / Governance

见 MASTER_PLAN；跨节点能力在 Identity + Governance + Revocation 就绪前不得生产化。单 Node 的开放接入（条件 C）不依赖 Federation 完成。

---

## 9. 数据模型分层（禁止混成一张大 Schema）

| # | 模型层 | 作用 | 本仓现状 |
| --- | --- | --- | --- |
| 1 | Component Contract | 组件接入 | Missing |
| 2 | Universal Data Model | 通用表达 | Partial（领域 Pydantic ≈ 内部模型） |
| 3 | Memory Interchange Model | 外部交换格式 | Missing（仅有 A-MEM/JSONL 特化映射） |
| 4 | Mnemosyne Cognitive Model | 内部认知语义 | Partial（Observation/Memory/Schema…） |
| 5 | Storage Schema | 持久化 | Implemented（migrations 001–005） |
| 6 | Event Contract | 事件语义 | Partial（events/outbox 表 + 进程内 bus） |

### 演进规则

- Schema 版本化；外部 ID 保留；未知扩展字段可保留；原始 payload 可追溯  
- 破坏性变更必须有迁移与回滚计划  
- **外部组件禁止直连 SQLite**；一律走 Service Contract  
- 内部模块禁止依赖他模块私有实现细节  

### Interchange ≠ Cognitive Ingestion

```
External Source
  → Interchange Model（只描述外部数据）
  → Cognitive Ingestion
       Observation → Evidence+Provenance → Validation
       → Conflict → Episode/Memory Promotion
```

**迁移成功 ≠ 认知验证通过。**

---

## 10. 权威状态机（Adoption）

| 状态 | 含义 |
| --- | --- |
| External Authoritative | 旧库权威；Mnemosyne 只读接入 |
| Importing | 旧库权威；Mnemosyne 暂存验证 |
| Mnemosyne Primary | 新写入以 Mnemosyne 为准 |
| Dual Sync | 显式启用的双向同步（默认禁止） |
| Retired | Mnemosyne 权威；旧库仅备份/停用 |

**不允许**两套系统同时默认自认为唯一权威。  
当前推荐运行态：**External Authoritative 或 Importing（并行副记忆）**，见插件 `TRIAL.md`。

---

## 11. 迁移子系统边界（D5）

### A. Migration Engine

Provider Registry → Extractor → Interchange → Mapper → Dedupe → Conflict → Plan → User Approval → Staging → Verify → Commit  

必须：幂等、批次、续传、回滚、校验和、外部 ID 映射、溯源、部分失败处理。  

回滚须区分：未提交 / 已提交未引用 / 被引用 / 用户已改确认。

### B. Adoption & Compatibility Engine

Compatibility Gateway、语义映射、Read-through、单向同步、（可选）双向、Authority Manager、Cutover、Conflict Manager。

### Provider 优先级

1. JSON/JSONL · Markdown · SQLite · Mem0  
2. Zep/Graphiti · Letta · LangChain/Custom  

**现状：** JSONL + A-MEM 源已有；其余 Missing。

---

## 12. 互操作接入模式（D4）

| 模式 | 含义 | 本仓例 |
| --- | --- | --- |
| Provider | 向 Node 提供能力 | （目标）Embedding/Vector；现状多为内嵌 |
| Consumer | 调用 Node | 桌宠 Bridge、Admin UI、MCP 工具 |
| Adapter | 协议/格式转换 | A-MEM migrate source；Mem0 仍在宿主侧 |
| Extension | 扩展内部认知 | Schema discover 等 |

注册 ≠ 授权。必须：身份、能力、资源范围、用户同意、有效期、审计、撤销。

通信面：REST（基础）、WS/SSE、MCP（工具面≠唯一 API）、Webhook、可选 gRPC、CLI/STDIO、PCIP（节点间提案协议，非既成行业标准）。

---

## 13. 依赖图（实现顺序约束）

```
D1 Runtime/Storage + D8 Distribution 设计（Installer/Config/Manifest 最小集）
    └── D2 Cognitive Foundation（含 Memory Bank 设计）
            └── D3 Cognitive Intelligence
                    └── D4 Universal Interoperability（含非 DSH Consumer）
                            ├── D5 Migration & Adoption
                            ├── D8 Composition 最小可用（Component Manager / Profiles）
                            └── D6 Agent Ecosystem（跨 Node；可裁切出首个 GA）
                                    └── Phase 6 Integration / Readiness Gate（须含 A+B+C）
```

可提前并行（仅设计/预研，**不**因此立刻开大批实现 Epic）：

- Distribution Manifest / Profile 草案  
- Interchange Model 草案  
- Provider 调研（与 DSH 插件目录分离登记）  
- PCIP 协议草案  
- Compatibility Profile 草案  
- Backup/Restore 强化（属 D1，应早做）  
- Memory Bank + 权限模型（须在核心记忆「完成」前进入设计）  

---

## 14. 宿主与 Node（本仓落地关系）

```
[大肥鱼 / DSH]          [其他 Agent / 工具]
   │ DSH 社区插件              │
   │ (工具/模型/自动化)          │
   ▼                           │
[DSH Adapter] ────────────┐    │
                          ▼    ▼
              [Mnemosyne Node] ←── 开放接入（REST/SDK/MCP/…）
                          │
                          ▼
              [Storage Provider / 其他 Mnemosyne Components]
```

- **DSH / 大肥鱼**：首个重要集成宿主 = Consumer + Observation Producer；**不是**权威存储，**不是** Node 运行时硬依赖。  
- **`_dsh_plugins/dsh-cognitive-memory`**：定位为 **DSH Adapter / Host 适配**，可联调或托管 Node 进程；**禁止**另建第二套个人 LT；**禁止**被表述为「Mnemosyne 本体」。  
- 其他 `_dsh_plugins/*`：默认属 **DSH 社区插件生态**；仅当显式提供 Mnemosyne Manifest 并经 Node Component Manager 安装时，才同时算 Mnemosyne Component。  
- Brain / Agent 任务态（`docs/BRAIN_INTEGRATION.md`）经授权调用 Node；输出先入 Observation。  

**Node 独立性（2.0 硬性架构约束）：** 必须具备可独立于 DSH 的配置、存储根、进程生命周期与管理接口；缺任一者不得宣称 A+B+C 达成。

---

## 15. 安全横切

全程遵循 MASTER_PLAN 三条原则 +：

1. 外部数据默认不可信  
2. 外部 Agent 输出 → Observation  
3. 组件注册不自动获数据权  
4. 远程访问需明确授权与网络边界  
5. 权限带资源范围；可过期可撤销  
6. 敏感操作审计  
7. 迁移须用户明确批准  
8. 导出不绕过授权  
9. train/forward 须有真实执行机制（字段≠执法）  
10. 双向同步默认关闭  
11. 删除传播区分原因  
12. P2P/Relay 专项验收  

Production Hardening 可 Deferred，但**某能力自身带来的新信任边界不得用 Deferred 跳过验收**。
