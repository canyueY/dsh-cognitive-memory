# Mnemosyne 2.0 — Capability Matrix & Gap Analysis

> **权威仓 = [`canyueY/mnemosyne`](https://github.com/canyueY/mnemosyne)。**  
> **旧 npm / [`dsh-mnemosyne`](https://github.com/canyueY/dsh-mnemosyne) 不作为 2.0 标尺。**  
> 详见 [REPO_BASELINE](REPO_BASELINE.md)。用旧公开 `service/` 目录做的「V1.5 / 无 Identity/Bank/CLI」类审计视为**过时基线**，不得覆盖本账本。

**盘点日期：** 2026-10-31（修订：权威仓声明 + 黄项厚度；此前含 PR #12–#14 / GA hardening）  
**对照目标：** [MASTER_PLAN](MNEMOSYNE_2.0_MASTER_PLAN.md)  
**架构边界：** [ARCHITECTURE](MNEMOSYNE_2.0_ARCHITECTURE.md)（§0–§6 双重目标与生态边界）  
**API 规格：** [MNEMOSYNE_API_SPEC.md](MNEMOSYNE_API_SPEC.md)  
**证据范围：** **`canyueY/mnemosyne`（本仓）**；宿主桥接见 `MurasamePet`；`services/cognitive-memory` 仅为过渡副本

状态枚举：

| 状态 | 含义 |
| --- | --- |
| **Implemented** | 有可运行代码 + 基本测试/可调用路径 |
| **Partial** | 有代码但缺关键语义/契约/验收 |
| **Planned** | 仅文档/路线图，无实现 |
| **Missing** | 目标要求有，仓库无痕迹 |
| **Deprecated** | 应淘汰或仅过渡保留 |
| **External-Unverified** | 方案声称存在，本仓无法验证 |

**2.0 完成定义（A+B+C，缺一不可）：**

| 条件 | 含义 | 本仓粗判 |
| --- | --- | --- |
| **A** Cognitive Infrastructure | 独立认知资产与引擎 | Partial→Implemented-lite（Node+Core；厚度仍可加） |
| **B** Open Component Infrastructure | 可安装/配置/组合 | Partial（本地 D8；**市场 Missing=预期裁切**） |
| **C** Universal Agent Interoperability | 不经 DSH 的稳定接入 | Partial→增强（REST/MCP/SDK/standalone E2E/DSH 薄化契约） |

---

## 1. 总览差距（八领域）

| 领域 | 目标完备度（相对 2.0） | 状态 | 一句话 |
| --- | --- | --- | --- |
| D1 Runtime & Storage | ~80% | Partial→Implemented-lite | Node CLI/config/backup 包/E6.2/V8；StorageProvider 已有；PG/加密仍缺 |
| D2 Cognitive Foundation | ~75% | Partial→Implemented-lite | Obs/Evidence/Banks/Authority/Identity 最小面齐 |
| D3 Cognitive Intelligence | ~55% | Partial | Schema 网络+黄金样本+feedback promote；Entity 仍薄；RL LOCKED |
| D4 Universal Interoperability | ~70% | Partial→增强 | REST+MCP+Py/TS SDK+SSE+standalone/DSH 薄化 E2E；API Spec 已补 |
| D5 Memory Migration & Adoption | ~80% | Partial→增强 | Interchange/Staging/Cutover/Admin/E6.5；全量仍另开 |
| D6 Open Agent Ecosystem | ~25% 同 Node / 0% 联邦 | Partial + **CUT 2.1+** | 同 Node 多 Agent 已有；跨 Node 联邦裁切 |
| D7 Governance & Operations | ~65% | Partial→增强 | grants+CRUD+硬删闸+policy 执法测试；隐私产品化仍可厚 |
| **D8 Distribution & Composition** | ~55% | Partial | 本地 Manifest/Installer/Lifecycle；**市场/远程 Missing=预期** |

**结论：** 2.0 最小骨架已闭合；剩余是厚度、人工试点签字与明确裁切项。  
**禁止**把 DSH 社区插件进度记成 Mnemosyne Component 进度。  
**不得**将全量用户收纳或跨 Node 联邦标为已完成。

### 1.1 两套生态对照（防混用）

| 项 | DSH 社区插件 | Mnemosyne Components / Adapters |
| --- | --- | --- |
| 扩展对象 | 宿主 Agent（大肥鱼/DSH） | Node 认知基础设施 |
| 目录 | `_dsh_plugins/*` | 未来由 Node Component Manager 管理（尚无） |
| `dsh-cognitive-memory` | **DSH Adapter**（Partial） | **不是** Mnemosyne 本体；不计入 B 完成 |
| 搜索/浏览器等 | 工具能力 | 经 Adapter → Observation 后才进认知资产 |
| 进度记账 | 「宿主集成」 | D8 / D4 Provider；**禁止合并记账** |

三种「合并」语义见 [ARCHITECTURE §5.2](MNEMOSYNE_2.0_ARCHITECTURE.md)。

---

## 2. 基线声明差距（方案 vs 仓库）

| 方案声称 | 本仓验证 | 处置 |
| --- | --- | --- |
| P3 Universal Ecosystem Foundation Accepted | Missing | 标 External-Unverified；入库前不作为依赖 |
| Foundation 1.0 Stabilized / contract `foundation-0.1.0` | Missing | 同上 |
| PR #18 merge `05c73bf` | 本仓仅见 PR #1（migration） | 勿引用 |
| `docs/ENGINEERING_CONSTRAINTS.md` | Implemented（已入库） | 持续引用；不得削弱 |
| DSH 插件 = Mnemosyne 组件（隐含假设） | **错误混淆** | 见 §1.1；Adapter 单独记账 |
| `feat/mnemosyne-2.0-p3-ecosystem` | Missing | 勿当作稳定基线分支 |
| Production Security Assessment Completed | Missing | 保持 Hardening Deferred + 能力级安全验收 |
| 窄义 Mnemosyne 2.0（Schema+Gate） | Partial | 降级为 L2 子层，从属 Master Plan |
| `_dsh_plugins/dsh-cognitive-memory` | Partial（**DSH Adapter** / 副记忆试用） | 保留；转正见 `TRIAL.md`；**勿记为 D8 完成** |

---

## 3. 能力矩阵（按领域）

### D1 Runtime & Storage

| 能力 | 状态 | 证据 | 缺口 |
| --- | --- | --- | --- |
| 进程启动 / HTTP API | Implemented | `main.py`、`api/app.py`、`bootstrap.py` | 非独立 Node 安装体验 |
| SQLite + migrations | Implemented | `storage/migrations.py` 001–005 | 无多 Provider |
| Outbox / Tasks worker | Implemented | `jobs/dispatcher.py`、`events/bus.py` | Event Contract 未版本化对外 |
| Backup / Restore CLI | Implemented | `cli`/`node_cli` backup/restore + 备份包 | 运行中 restore 拒绝 |
| Health | Implemented | `cli health`、`/health`、`doctor` | — |
| Storage Provider Interface | Implemented-lite | `storage/provider.py` + 边界契约测试 | 仍仅 SQLite；PG 后续 |
| Transaction Manager（显式） | Partial | SQLite 事务散落 service | 无统一 Tx 边界文档 |
| Encryption / Key Interfaces | Missing | — | — |
| Node 配置校验 / 升级框架 | Implemented-lite | `node_config.py` + validate | 升级编排仍薄 |
| 独立安装包 / 干净环境安装验收 | Implemented-lite | `mnemosyne_clean_install_e62.py` + 报告 | 非安装器产品包装 |

### D2 Cognitive Foundation

| 能力 | 状态 | 证据 | 缺口 |
| --- | --- | --- | --- |
| Observation 写入 | Implemented | `ingestion/` + `capture_observation` | 入站归一化 Identity；长期无证据 ACTIVE 强制 candidate |
| Memory CRUD / 状态 | Implemented | `memories` + access 执法 | Bank 经 grant/banks 约束 |
| memory_evidence 表 | Implemented | `evidence/` + provenance 字段 | 验证态/置信可写；非联邦级 |
| Retrieval Planner | Implemented | `retrieval/planner.py`、`pipeline.py` | 向量/实体 Provider 化 |
| Relations | Partial | `memory_relations` + 时空字段 | 冲突/图谱查询弱 |
| Memory Bank 多空间 | Implemented | `bank_id` + 六空间目录 | Shared/Public 默认隔离 |
| Identity Engine | Partial | `identity/` + `identity_principals` | 单 Node 主体已有；跨节点仍缺 |
| Episode 一等公民 | Partial | consolidate 规则 | 与 Observation 边界需产品化 |
| Graphiti 等图后端 | Planned | SPEC 标注 ⏳ | 勿装作已有 |

### D3 Cognitive Intelligence

| 能力 | 状态 | 证据 | 缺口 |
| --- | --- | --- | --- |
| Consolidate / Promote | Partial | `promote.py` 显式规则 | Schema 网络仍待 E2.4 |
| ChangeDetect / ChangePlan | Partial | `change_*`、migration 004 | L2 apply 谨慎；验收用例薄 |
| Emotion shadow | Partial | `emotion_*`、003 | 默认不写主记忆（正确） |
| Schema discover/assimilate | Implemented | `schema_*` + `schema_network` | 拆分/合并/影响可追踪 |
| Metacognition / RL / Value | Partial | stubs + Gate LOCKED | 保持 LOCKED |
| Conflict Detection（完整） | Partial | `cognition/conflict.py` retain_both | 系统化图谱查询仍弱 |
| 事实 vs 推断区分（可测） | Implemented | `tests/cognitive/fixtures/golden_samples.json` | E2.1 可测 |
| Feedback Learning | Partial | feedback API | 不无条件覆盖需强化测试 |

### D4 Universal Interoperability

| 能力 | 状态 | 证据 | 缺口 |
| --- | --- | --- | --- |
| REST API | Implemented | `api/app.py`、OpenAPI、[API_SPEC](MNEMOSYNE_API_SPEC.md) | 前缀 `/api/v1` |
| MCP tools | Implemented-lite | `mcp/server.py`（observe/import_preview+confirm） | ≠ 唯一协议 |
| Host Bridge / Plugin | Partial | 宿主 HTTP Bridge + `adapters/dsh_http.py` 薄化 | 宿主侧仍可继续减脂 |
| Component Registry / Discovery | Implemented-lite | 本地 Component Manager | **市场未做=裁切** |
| Schema Registry（对外） | Missing | 仅内部迁移 | — |
| PCIP | Planned | 草案 / **2.1+** | 非生产协议 |
| 多语言 SDK | Implemented-lite | Python `sdk` + `sdk-ts` `@mnemosyne/client` | TS 为子集 |
| adapters/ 包 | Implemented-lite | `adapters/dsh_http.py` + 薄化 E2E | Importer Provider 仍可扩 |
| 契约/集成测试目录 | Implemented | `tests/contract` + `tests/security` | 故障注入仍可扩 |

### D5 Memory Migration & Adoption

| 能力 | 状态 | 证据 | 缺口 |
| --- | --- | --- | --- |
| Migration Engine 核心 | Implemented | `migration/engine.py` + staging/interchange | Staging/Approval/Checksum 已落地 |
| JSONL / A-MEM source | Implemented | `migration/sources.py` | — |
| Checkpoint resume | Implemented | `migration/checkpoint.py` | — |
| Idempotent write keys | Implemented | sink + service idempotency | — |
| MigrationReport | Implemented | engine report | — |
| Universal Interchange Model | Implemented | `migration/interchange.py` v0 | 未知字段进 extensions |
| Markdown / SQLite / Mem0 Provider | Implemented | `importers` + `mem0_adapter` | 经 Interchange；宿主 Mem0 仍并行 |
| Dedupe / Conflict / Planner / Staging | Implemented-lite | Staging+Approval+Checksum+source/content dedupe+soft/hard rollback | Conflict 图谱仍可增强 |
| Compatibility Gateway | Implemented | `compat_gateway` 只读/单向 | 双向默关 |
| Authority Manager / Cutover | Implemented-lite | cutover preview/execute + CLI + Admin Adoption | 全量收纳仍另开 |
| 用户预览/选择范围 UI | Partial | Staging + adopt export + Admin Adoption 面板 | CognitiveMemory 全量面板仍可选扩 |
| 完整导出（互操作格式） | Partial | `export_interchange` JSONL + Admin `/api/adoption/export` | 范围选择仍可增强 |

### D6 Open Agent Ecosystem

| 能力 | 状态 | 证据 | 缺口 |
| --- | --- | --- | --- |
| Agent/Node Identity（跨节点） | Missing | — | — |
| Discovery / Connection | Missing | — | — |
| Knowledge Exchange L0–L3 | Missing | — | L3 默认禁止需产品化 |
| Federation / P2P / Relay | Missing | — | P2P 明确延后 |
| Brain 接入方案 | Planned/Partial | `docs/BRAIN_INTEGRATION.md`、`Murasame/brain/`（若未提交则仅工作区） | 属 Consumer，非 Federation |

### D7 Governance & Operations

| 能力 | 状态 | 证据 | 缺口 |
| --- | --- | --- | --- |
| Capability Gate | Implemented | `capability_gate.py`、Admin 面板 | 默认 LOCKED（正确） |
| Capability Audit | Partial | `capability_audit` 表 | 覆盖面需扩到迁移/导出 |
| Backup/Restore | Implemented | CLI + E1.2 drill + V8 现网签字脚本 | 人工签字栏待填 |
| Privacy / Consent / Revocation | Implemented-lite | grants + `governance/policy.py` | 产品化 UI/默认策略仍可厚 |
| train/forward 真实执行 | Implemented-lite | store/forward/train/retention 执法 + security 测试 | 历史数据未回溯重标 |
| Operational Runbook | Implemented-lite | NODE_OPS / ADOPTION / E6.5 / e6.5-pilot-status | — |
| ENGINEERING_CONSTRAINTS 入库 | Implemented | `docs/ENGINEERING_CONSTRAINTS.md` | 保持 |

### D8 Distribution & Composition

| 能力 | 状态 | 证据 | 缺口 |
| --- | --- | --- | --- |
| Node Installer（独立于 DSH） | Implemented-lite | `mnemosyne config init` + E6.2 干净目录 | 非商业安装包 |
| Configuration Manager（Node 级） | Implemented-lite | `node_config.py` | 与宿主 config 并存 |
| Component Manifest | Implemented | `components/manifest.py` | 与 DSH `dsh.plugin.json` **分离** |
| Component Manager / Installer | Implemented-lite | `components/manager.py` + CLI/API | 升级/远程源仍待 |
| Dependency Resolver | Implemented-lite | `components/resolver.py` | 仅 interfaces.requires |
| Composition Profiles | Implemented-lite | `components/profiles.py` | 模板≠已装组件 |
| Compatibility Gate（组件↔Node） | Partial | compatibility 字段 + resolve | 版本范围执法仍弱 |
| 组件市场 / 远程 Registry | Missing | — | **明确裁切；勿记 Missing 为遗漏实现** |
| 「合并」三语义实现 | Missing / Partial | 迁移引擎≈记忆合并起步 | 组件合并、Node 合并未做 |

### 宿主并行记忆（过渡）

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| A-MEM | Deprecated-候选 / 仍并行 | 迁移后可 Retired；Gate 前不停用 |
| Mem0 / Neko | Partial 过渡 | 非 Mnemosyne 权威 |
| mnemosyne_compat 只读 | Implemented | 禁止双向同步（正确） |
| DSH 社区插件（非 Adapter） | 宿主侧 Partial | **不计入** D8 完成度 |

---

## 3.1 落地更新新增能力行（账本）

| 能力 | 领域 | 状态 | 说明 |
| --- | --- | --- | --- |
| Node Autonomy | D1 | Implemented | `mnemosyne doctor/start/health` 无 DSH — Phase1 |
| Node Configuration | D1 | Implemented | `node_config.py` + `mnemosyne config` — E1.3 |
| Node Lifecycle | D1 | Implemented | `mnemosyne start/stop/status` — E1.4 |
| Node Admin API / CLI | D1 | Implemented | `mnemosyne`：config/backup/restore/doctor — E1.5 |
| Memory Bank | D2 | Implemented | 六空间 + 默认 Personal 检索隔离 |
| Authority Model | D2/D5 | Implemented | 五态状态机；dual 须 allow_dual |
| Universal API | D4 | Implemented-lite | REST + API_SPEC + OpenAPI + contract 测试 |
| MCP Adapter | D4 | Implemented-lite | mcp/server；写确认 |
| External Agent Identity | D4/D7 | Implemented | principals + agent_grants |
| TS SDK | D4 | Implemented-lite | `sdk-ts`；Python 为主参考 |
| Storage Provider | D1 | Implemented-lite | Protocol + Sqlite + 边界测试 |
| Component Manifest | D8 | Implemented | `manifest.py` + SPEC |
| Component Installer | D8 | Implemented-lite | 本地源 `ComponentManager.install` |
| Dependency Resolver | D8 | Implemented-lite | interfaces.requires |
| Composition Profiles | D8 | Implemented-lite | standalone/dsh/custom |
| Component Lifecycle | D8 | Implemented-lite | install→enable→health→disable→remove |
| Import Preview | D5 | Implemented-lite | Staging preview + MCP import_preview |
| Adoption Readiness | D5/D7 | Implemented-lite | ADOPTION + E6.5 + pilot-status（人工签字中） |
| Backup Restore Drill | D1 | Implemented | E1.2 + V8；人工签字栏待填 |
| Policy Enforcement | D7 | Implemented-lite | allow_store/forward/train + retention |
| E6.2 Clean Install | D1 | Implemented | `mnemosyne_clean_install_e62.py` + 报告 |
| DSH Adapter Thin E2E | D4 | Implemented-lite | `adapters/dsh_http` + contract 测试 |

执行账本见 [IMPLEMENTATION_PLAN](MNEMOSYNE_2.0_IMPLEMENTATION_PLAN.md)；审计见 [CODE_AUDIT](MNEMOSYNE_2.0_CODE_AUDIT.md)。

---

## 4. 文档 vs 代码漂移（需治理）

| 文档 | 问题 | 动作 |
| --- | --- | --- |
| `MNEMOSYNE_2.0.md` + `v2/PHASE_MAP` | 描述的是「图式/Gate」窄 2.0，易与 Master 2.0 混淆 | 页首标注从属于 MASTER_PLAN |
| `COGNITIVE_MEMORY_SPEC` | 声称 migrate/面板完成；Graphiti/自动采集仍 ⏳ | 与 Matrix 对齐改状态 |
| `MNEMOSYNE_COMPLETION` | 「完成起步」易被读成 2.0 完成 | 加警告：非 Master Readiness |
| `docs/README.md` | 未索引 Master 三件套 / v2 | 更新索引 |
| 方案中的 Foundation 叙事 | 本仓不存在 | 仅 MASTER_PLAN §2 更正段保留 |

---

## 5. 可执行 Epic / PR 清单

> **原则：** 一次只推进少数 Epic；每个 PR 小步、可回滚、带验收。  
> **现在不要**同时开 Runtime + Intelligence + Interop + Ecosystem 四条实现线。

### Phase 0 — Architecture Freeze（当前）

| ID | Epic | 交付物 | 建议 PR | 验收 |
| --- | --- | --- | --- | --- |
| **E0.1** | 冻结 Master 文档集 | 本三文件 | `docs: freeze Mnemosyne 2.0 master plan` | 审阅通过；README 索引 |
| **E0.2** | 约束文档入库 | `docs/ENGINEERING_CONSTRAINTS.md`（三条原则+引用） | 独立小 PR | 与 MASTER_PLAN 一致 |
| **E0.3** | 窄义 2.0 降级说明 | 改 `MNEMOSYNE_2.0.md` / `MNEMOSYNE_COMPLETION.md` 页首 | 随 E0.1 | 无「2.0 已完成」歧义 |
| **E0.4** | 外部基线登记（可选） | 若确有 Foundation 仓：`docs/EXTERNAL_BASELINES.md` | 有证据再开 | 列 URL/commit；无则标明 N/A |
| **E0.5** | 五者边界 + D8 设计冻结 | ARCHITECTURE §0–§6 已写入；Matrix §1.1 / D8 | 本文档修订（**先设计，不开实现洪峰**） | 审阅确认：DSH 插件 ≠ Mnemosyne Component |
| **E0.6** | Readiness 裁切决议 | 是否将 D6 联邦标为 2.1+；**B/C 最小集是否进 GA** | 短决策记录进 MASTER_PLAN 附录 | 签字前不拆 D8 大批实现 Epic |

**退出：** Phase 0 完成 → 允许启动 Phase 1 设计与首个实现 Epic。  
**明确：** E0.5/E0.6 之后再决定 D8 实现切片；**现在不**因 Distribution 概念立刻新开一串开发分支。

---

### Phase 1 — Runtime & Cognitive Foundation

| ID | Epic | 依赖 | 建议分支 | 拆 PR（示例） | 验收 |
| --- | --- | --- | --- | --- | --- |
| **E1.1** | Storage Provider Contract | E0 | `feat/mnemosyne-2.0-runtime` | P1: interface+SQLite adapter；P2: 禁止外部直连文档/测试 | 契约测试绿 |
| **E1.2** | Backup/Restore 强化 | E1.1 | 同左 | 干净目录备份恢复 + Runbook | Readiness A 子集 |
| **E1.3** | Observation 统一入站 | E0 | `feat/mnemosyne-2.0-cognitive-foundation` | 填 `ingestion/`；导入必经 Observation | 无「直接写 ACTIVE」路径 |
| **E1.4** | Evidence 语义加固 | E1.3 | 同左 | evidence API + provenance 字段验收用例 | B 门证据项 |
| **E1.5** | Memory Bank 设计+最小实现 | E1.1 设计先 | 同左 | P1: 模型/迁移；P2: 隔离测试 | Personal≠Shared 互不污染 |
| **E1.6** | Identity 最小模型（单节点） | E0 | 可挂 foundation 或 cognitive | user/node/agent 表或文档化 ID 方案 | 为 Gate/Bank 提供主体 |
| **E1.7** | 检索 Provider 缝 | E1.1 | 同左 | FTS 保留；向量接口空实现+契约 | 可替换点存在 |
| **E1.8** | Node 独立运行最小面 | E0.5 | `feat/mnemosyne-2.0-runtime` | 无 DSH 亦可：配置根、启停、health、data_dir | 满足「独立于 DSH」硬约束的可演示路径 |
| **E1.9** | D8 设计草案（非实现洪峰） | E0.5–0.6 | docs only 或单 PR | Manifest 字段草案 + 与 `dsh.plugin.json` 对照表 | 设计评审通过；**暂不**实现完整 Component Manager |

**退出：** 独立 data_dir 上完成「装库→观察→证据→记忆→检索→备份恢复」脚本化闭环；并证明 **可不经 DSH 启动 Node**。

---

### Phase 2 — Cognitive Intelligence

| ID | Epic | 依赖 | 建议 PR 焦点 | 验收 |
| --- | --- | --- | --- | --- |
| **E2.1** | 黄金样本集 | E1.3–1.4 | `tests/cognitive/fixtures`：事实/推断/外部/冲突/未知 | Phase 2 退出条件可测 |
| **E2.2** | Conflict 保留策略 | E2.1 | 冲突不丢；可检索两侧 | 用例全过 |
| **E2.3** | Promotion 条件显式化 | E1 | 文档+代码守卫+测试 | 无静默 ACTIVE |
| **E2.4** | Schema 网络（拆分/合并） | ✅ `schema_network` | API + 测试 | 影响可追踪 |
| **E2.5** | Gate 保持 | — | RL/Value 仍 LOCKED | 无生产 RL |

---

### Phase 3 — Universal Interoperability

| ID | Epic | 依赖 | 建议 PR 焦点 | 验收 |
| --- | --- | --- | --- | --- |
| **E3.1** | OpenAPI/契约测试 | E1 | `tests/contract` + CI | 破坏变更失败 |
| **E3.2** | Component Contract v0 | E0.4 或新建 | 注册≠授权；范围/过期 | 未授权拒绝 |
| **E3.3** | Python SDK 薄封装 | E3.1 | `packages/` 或官方 client | 第二 Consumer 不止桌宠 |
| **E3.4** | Event Contract 对外 | E1 | 版本化事件 | 可订阅/审计 |
| **E3.5** | PCIP 草案（仅设计） | — | `docs/pcip/` 草案 | 不声称行业标准 |

**退出：** ≥2 技术栈（如 Python SDK + REST/TS Admin）受权读写通过。

---

### Phase 4 — Migration & Adoption（在 PR #1 之上）

| ID | Epic | 依赖 | 建议分支 | PR 焦点 | 验收 |
| --- | --- | --- | --- | --- | --- |
| **E4.1** | Interchange Model v0 | E0/E1 | `feat/mnemosyne-2.0-memory-migration` | schema+未知字段保留 | 与 Cognitive 映射表 |
| **E4.2** | Staging + Approval + Checksum | 现有 engine | 同左 | 未批准不 Commit | 回滚区分态 |
| **E4.3** | Markdown + SQLite importers | E4.1 | 同左 | 复用 engine | 三形态导入 |
| **E4.4** | Mem0 Adapter | E4.1 | 同左 | 经 Interchange，不直写表 | 幂等续传 |
| **E4.5** | Authority 状态机 | E1.6 | 同左 | 五态 + 配置/API | 无双权威 |
| **E4.6** | Compatibility Gateway（只读/单向） | E3.1 | 同左 | 旧 API 语义等级 | 双向默关 |
| **E4.7** | 导出 Interchange + 预览 | ✅ CLI/API export + Admin Adoption | banks 可选 |

**退出：** ≥3 数据形态 + ≥1 兼容 API；**仍不等于**可正式收纳全体用户。

---

### Phase 5 — Agent Ecosystem

| ID | Epic | 依赖 | 说明 |
| --- | --- | --- | --- |
| **E5.1** | Agent Identity（同 Node） | ✅ grants/audit | 跨节点仍 2.1+ |
| **E5.2** | Exchange L0–L2 + Provenance | E5.1 | L3 默认拒绝 |
| **E5.3** | Revocation（同 Node） | ✅ revoke + expires | 联邦撤销仍 2.1+ |
| **E5.4** | Federation | E5.3 | 明确范围 |
| **E5.5** | P2P/Relay | 专项安全 | **默认不纳入首个 2.0 GA**，除非单列并过验收 |

---

### Phase 6 — Integration & Readiness

| ID | Epic | 内容 |
| --- | --- | --- |
| **E6.1** | E2E 套件 | ✅ `mnemosyne_readiness_suite.py` 最小面 | 故障注入仍可扩 |
| **E6.2** | 干净环境安装 | 新机器/新目录一条龙 |
| **E6.3** | 文档与 Runbook | 运维手册 + Adoption 手册 |
| **E6.4** | Readiness Gate 签字 | ✅ `MNEMOSYNE_2.0_READINESS.md` | 全量收纳仍另开 |
| **E6.5** | 正式 Adoption 试点 | ✅ Runbook `MNEMOSYNE_E6.5_PILOT.md` + Admin UI；**小规模**（非全量） |

---

## 6. 建议的「下一周」执行序（仅此）

**Phase 1–4 最小面已收口（PR #3–#8）。** 不要开七条实现线，也**不要**因 D8 概念立刻开组件市场实现。建议严格按序：

1. ~~Phase 1–3 Cognitive / Interop~~  
2. ~~E2.4 Schema 网络 + Phase 4 Migration/Adoption 最小面~~  
3. **下一实现主线（可选）：** Phase 5 Agent Ecosystem 裁切评估，或 D8 最小组件面  
4. Interchange v0 + Staging 已落地；Component 安装器仍设计稿；D6 联邦零实现  
5. ~~Adoption Admin UI / V8 / E6.5 Runbook~~（本切片）；全量收纳与联邦仍不纳入  

---

## 7. Readiness 速查（相对现状）

| 门 | 现状粗判 | 阻断项（示例） |
| --- | --- | --- |
| A Node Infra | 绿（Phase1） | doctor/config/start/backup；V8 脚本已提供（现网签字视环境） |
| B Cognitive Foundation | 绿（Phase2 Core） | Identity/Obs/Evidence/Bank/Authority + 黄金样本 |
| C Cognitive Intelligence | 绿偏黄 | Schema 网络 + 黄金样本；RL 仍 LOCKED |
| D Interoperability | 黄→绿偏黄 | Python+TS SDK；CRUD 执法；SSE；standalone E2E；PCIP 仍可扩 |
| E Migration & Adoption | 绿偏黄 | Interchange/Staging(dedupe+rollback)/Cutover + Admin Adoption；全量仍另开 |
| F Agent Ecosystem | 黄 | 同 Node 多 Agent 已有；**跨 Node 联邦裁切 2.1+** |
| G Quality & Ops | 绿偏黄 | readiness + V8 + E6.2 clean install + E6.5 Runbook |
| H Adoption Readiness | 黄→绿偏黄 | Admin Adoption + E6.5 小规模试点手册；**≠ 全量收纳** |
| **条件 B（D8）** | 黄 | 本地组件面已有；市场/远程仍 Missing；**≠ DSH 插件** |

**裁切规则：** 若某能力不进 2.0 GA，必须在 MASTER_PLAN 附录写明排除理由、替代方案、归属版本——**禁止默认为已完成**。  
建议首个 GA：将 **F（跨 Node 联邦）** 标为 2.1+；**不得**裁切「单 Node 独立运行 / D8 最小组件面 / 非 DSH 接入（条件 C）」。

---

## 8. 矩阵维护

- 每完成一个 Epic：更新本表状态与证据路径  
- 禁止只改文档状态不改代码，或只并代码不改矩阵  
- Track A 发现契约破坏：先修回归，再继续功能 Epic  


> 2026-10-30 enforcement：CRUD Agent/Node 双轨执法；`MEMORY_HARD_DELETE` 默认 LOCKED；备份包含 config；E6.2 干净安装证据见 `docs/reports/e6.2-clean-install.json`。
