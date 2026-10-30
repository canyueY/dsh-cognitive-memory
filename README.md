# Mnemosyne

### Modular Evolving Memory Infrastructure for AI Agents

让 Agent 不只是记住过去，而是能够理解变化、积累经验，并修正自己。

Mnemosyne 是一个面向 AI Agent 的模块化记忆基础设施。

它不排斥其他记忆系统，而是成为个人认知的权威层（Cognitive Authority Layer），通过适配器与其他记忆库协作。

它为 AI Agent 和其他智能应用提供一套独立、持久、可治理、可演化的认知能力，让它们能够积累经验、形成记忆、理解关系、检索过去、修正认知，并在时间中持续学习。

> **权威实现：** 本仓库 [`canyueY/mnemosyne`](https://github.com/canyueY/mnemosyne)。  
> **不是 2.0 标尺：** npm / GitHub 旧壳 [`dsh-mnemosyne`](https://github.com/canyueY/dsh-mnemosyne)。  
> 基线、GA 与完整文档见 [`docs/REPO_BASELINE.md`](docs/REPO_BASELINE.md)。

它希望解决的不是简单的对话历史保存问题，而是如何让 Agent 在长期运行中持续积累经验：将经历转化为证据，将证据组织成记忆，在新信息出现时更新已有认知，并通过行为结果和反馈不断改善未来的判断。

Mnemosyne 以独立运行、模块化设计、可追溯数据和可组合服务为核心原则。它可以作为独立记忆系统运行，也可以通过适配器接入 DeepSeek Harness（DSH）等 Agent 宿主。

---

## 目录

- [1. 核心思想](#1-核心思想)
- [2. 项目定位](#2-项目定位)
- [3. 核心特点](#3-核心特点)
- [4. 整体架构](#4-整体架构)
- [5. 核心实现方案](#5-核心实现方案)
- [6. 模块化设计](#6-模块化设计)
- [7. 安装与运行](#7-安装与运行)
- [8. DSH 集成](#8-dsh-集成)
- [9. 开发与测试](#9-开发与测试)
- [10. 设计边界](#10-设计边界)
- [11. 未来方向](#11-未来方向)
- [12. 项目理念](#12-项目理念)

---

## 1. 核心思想

传统 Agent Memory 通常关注两个问题：

- 保存了什么？
- 需要时能否检索出来？

Mnemosyne 希望进一步解决三个问题：

- 新经验如何改变已有记忆？
- 已有判断如何在反证出现时得到修正？
- 一次经验如何改善 Agent 下一次的判断与行动？

因此，Mnemosyne 将记忆视为一个持续演化的过程：

Experience → Evidence → Memory → Retrieval → Action → Feedback → Evolution

```text
                新经历  新信息
                       │
                       ▼
                 Observation
                       │
                       ▼
                   Evidence
                       │
                       ▼
             Candidate  Evaluation
                       │
                       ▼
                 Memory Bank
                       │
                       ▼
             Retrieval  Context
                       │
                       ▼
                 Agent Action
                       │
                       ▼
                Feedback  Outcome
                       │
                       ▼
              Schema  Memory Evolution
                       │
                       └───────► 新一轮经验
```

记忆不是静态仓库，而是一个能够随着证据变化而持续调整的系统。

### 核心原则

1. 证据优先： 记忆必须尽可能保留来源、时间和可信程度。
2. 事实与推断分离： Agent 的推测不能自动成为用户事实。
3. 变化优先于覆盖： 新信息不应无条件覆盖旧信息。
4. 可追溯： 记忆的形成、更新和失效应当能够追踪。
5. 模块独立： 每项能力具有清晰边界，避免整个系统绑定单一宿主。
6. 渐进演化： 新能力应当可以独立测试、替换和逐步接入。
7. 经验复利： 每一次有效经验都应有机会改善未来的判断。

---

## 2. 项目定位

| 属性 | 说明 |
| --- | --- |
| 项目名称 | Mnemosyne |
| 项目定位 | Evolving Memory Infrastructure |
| 项目类型 | AI Agent 记忆基础设施 |
| 核心目标 | 长期记忆、证据管理、认知演化与反馈学习 |
| 核心实现 | Node Host + Python FastAPI Service |
| 接入方向 | DSH、独立 Agent、外部应用 |
| 设计原则 | Modular、Independent、Traceable、Composable |

Mnemosyne 不试图成为一个完整的 Agent 框架。

它不负责替代模型推理、工具执行、任务编排或 Agent 人格，而是为这些系统提供可复用的记忆能力。

Agent 决定如何行动，Mnemosyne 负责让行动能够建立在可靠的历史经验之上。

---

## 3. 核心特点

### 3.1 基础设施优先

Mnemosyne 不将自身限制为某个 Agent 框架的附属插件。

它以独立服务为核心，将记忆处理、存储、检索和演化能力封装为可复用的基础设施。

这意味着：

- 不要求 Agent 与记忆系统使用同一种语言。
- 不要求所有调用者都运行在同一个进程中。
- 不要求记忆能力只能通过某个插件入口访问。
- 不要求未来新增的 Agent 框架重新实现一套记忆系统。

DSH 是重要的集成宿主，但不是 Mnemosyne 唯一的使用方式。

### 3.2 模块化与独立运行

每项能力尽量拥有明确的输入、输出和职责。

例如：

- Schema Evolution 可以独立处理图式演化。
- Feedback Learning 可以独立评估反馈信号。
- Semantic Retrieval 可以独立提供语义相关性信号。
- Memory Bank 负责记忆数据的组织和管理。

模块之间通过明确的数据契约协作，而不是依赖彼此的内部实现。

### 3.3 记忆具有生命周期

一条信息不应该只有内容，还应该有来源、状态和变化过程。

Mnemosyne 将记忆相关过程组织为：

Observation → Evidence → Candidate → Memory → Review → Evolution

让系统能够区分：

- 新出现的信息。
- 已经验证的事实。
- 尚待确认的候选判断。
- 与旧记忆存在冲突的信息。
- 已经失效或被新状态取代的信息。

### 3.4 认知演化

基于图式理论，Mnemosyne 将新经验与既有认知之间的关系分为：

| 类型 | 含义 |
| --- | --- |
| Assimilation | 同化：新经验可以纳入既有图式 |
| Accommodation | 顺应：调整既有图式的内容或适用范围 |
| Conflict | 冲突：反证足以使图式进入争议状态 |

当前实现由 `cognition/schema_evolution.py` 提供。

其中，默认 `confirm=False`，先预览演化结果，确认后才写入版本，避免新证据静默覆盖已有认知。

### 3.5 反馈驱动的学习

Mnemosyne 不把所有反馈混为一谈。

当前将反馈区分为：

| 信号 | 含义 | 权重 |
| --- | --- | ---: |
| `user_explicit` | 用户明确表达的评价或纠正 | 0.10 |
| `outcome` | 实际行为结果 | 0.06 |
| `self_eval` | Agent 自我评估 | 0.02 | 

三种信号具有不同的证据意义。

尤其是 Agent 自评不能直接改变用户事实；负向信号可以要求后续 Review 或 Change Plan 介入。

对应实现：`cognition/feedback_learning.py`。

### 3.6 可选语义能力

语义检索是可插拔能力，不是记忆系统唯一的判断依据。

当前实现：

- 默认使用轻量级 `hashed_embedding()`。
- 允许注入真正的 `EmbeddingProvider`。
- 通过 `SemanticScorer.blend()` 融合词法与语义信号。
- 语义加分权重上限为 0.6。
- 不替代原有 FTS、Planner 和证据、时间、情境评分。

对应实现：`retrieval/semantic.py`。

默认哈希表示是轻量级相似性特征，并不等价于完整的自然语言语义理解。

---

## 4. 整体架构

Mnemosyne 采用 Host 与 Service 分离的架构思路。

```text
                 Agent  Application
                         │
                         ▼
                  Integration Layer
                   DSH  REST  MCP
                         │
                         ▼
                    Node Host
                         │
                Service Integration
                         │
                         ▼
                 Python Memory Service
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Cognition      Retrieval       Memory
          │              │              │
          ▼              ▼              ▼
    Schema Evolution  Semantic       Memory Bank
    Feedback Learning  Scoring       Evidence
    Change Planning    Ranking        History
                         │
                         ▼
                 Persistent Storage
```

### Node Host

负责宿主集成和服务调用。

主要目标：

- 提供统一的应用接入入口。
- 管理宿主侧生命周期。
- 连接独立记忆服务。
- 将底层能力适配为 Agent 可使用的接口。

### Python Memory Service

负责记忆核心处理能力。

主要目标：

- 记忆数据处理。
- 证据与状态管理。
- 认知演化。
- 反馈学习。
- 检索与评分。
- 与存储层协作。

### Memory Bank

负责长期记忆的组织与持久化。

它不应该依赖某一个 Agent 的运行状态，也不应该将所有数据直接绑定到单次对话上下文。

---

## 5. 核心实现方案

### 5.1 Observation → Evidence → Candidate

系统首先接收观察信息，再将其组织为可评估的证据。

这一步重点是保留来源和上下文，而不是急于生成结论。

### 5.2 Memory Evolution

当新信息进入系统时，与现有记忆进行匹配。

根据证据关系决定：

- 补充旧记忆。
- 调整旧记忆的适用范围。
- 创建新版本。
- 标记冲突。
- 提交人工或后续流程审查。

### 5.3 Feedback Learning

行为结果和用户反馈分别进入学习过程。

系统需要区分：

- 用户明确认可。
- 用户明确纠正。
- 实际行动成功。
- 实际行动失败。
- Agent 自我判断。

这样可以避免把一次成功执行错误地解释为用户认同。

### 5.4 Semantic Retrieval

语义信号参与检索排序，但不能压过证据可靠性、时间有效性和情境匹配。

未来可以根据实际需求注入不同的 Embedding Provider，而无需重写整个检索系统。

### 5.5 Experience Loop

最终形成：

```text
Experience
    ↓
Evidence
    ↓
Memory
    ↓
Recall
    ↓
Action
    ↓
Feedback
    ↓
Evolution
    └───────────────↺
```

这条闭环是 Mnemosyne 的长期核心。

---

## 6. 模块化设计

Mnemosyne 希望将能力设计成可独立维护的模块。

| 模块 | 职责 |
| --- | --- |
| Observation | 接收原始观察 |
| Evidence | 管理证据及其来源 |
| Memory | 记忆生命周期管理 |
| Schema Evolution | 图式同化、顺应与冲突处理 |
| Feedback Learning | 用户反馈、结果和自评信号 |
| Retrieval | 记忆召回与排序 |
| Semantic | 语义相关性信号 |
| Memory Bank | 记忆存储与命名空间组织 |
| Integration | DSH 和其他宿主的适配 |

模块化的目标不是拆出尽可能多的文件，而是让模块具备独立演进的能力。

未来可以替换某个模块，而不必重写整个系统。

---

## 7. 安装与运行

### 环境要求

- Node.js 20+
- Python 运行环境
- Git
- 对应 Python 服务所需的依赖

### 获取项目

```bash
git clone https://github.com/canyueY/mnemosyne.git
cd mnemosyne
```

### 安装 Node 侧依赖

```bash
npm install
```

### Python 服务环境

建议使用独立虚拟环境：

```bash
python -m venv .venv
```

Windows：

```powershell
.venv\Scripts\activate
```

Linux / macOS：

```bash
source .venv/bin/activate
```

根据仓库提供的 Python 依赖清单安装服务端依赖。

### 启动方式

Mnemosyne 的运行由 Node Host 与 Python Service 两部分组成。

实际启动脚本、服务地址、环境变量和配置文件应以当前版本仓库中的配置为准。

不要将开发环境中的默认路径和端口直接当作生产环境配置。

 注意：以上为环境准备流程。完整的一键启动命令应在仓库统一启动脚本和服务配置稳定后补入。

---

## 8. DSH 集成

Mnemosyne 提供独立的 DSH 插件接入层。

插件仓库：

https://github.com/DSH-Raising-Plan/dsh-mnemosyne

安装：

```bash
dsh plugin --profile web add github:DSH-Raising-Plan/dsh-mnemosyne#main
```

目前可通过插件入口使用记忆能力，例如：

- `memory_search`
- `memory_context`
- `memory_observe`
- `memory_feedback`

插件负责将 DSH 的调用适配到 Mnemosyne 的记忆能力，不应成为记忆核心逻辑唯一的实现位置。

核心实现与宿主插件保持分离，有利于未来接入其他 Agent 框架。

---

## 9. 开发与测试

Mnemosyne 的开发强调模块级测试与完整回归。

当前经验闭环新增测试：

```text
tests/unit/test_experience_loop.py
```

覆盖：

- 图式演化。
- 反馈学习。
- 语义信号。
- 相关边界行为。

经验闭环提交：

```text
6ce80db
feat: add experience loop
```

当时独立仓全量测试结果：

```text
119 passed
```

测试数量和结果会随项目持续变化，请以当前 CI 和最新提交为准。

开发原则：

1. 新模块必须具有清晰的输入和输出。
2. 重要状态变化必须有测试。
3. 不允许自评直接改变用户事实。
4. 默认采用保守写入策略。
5. 新能力不能破坏既有记忆契约。
6. 接口变更需要考虑向后兼容。

---

## 10. 设计边界

Mnemosyne 当前不试图实现所有心理学理论。

暂不进入主干的方向包括：

- 社会学习四过程的完整模型。
- 道德发展三水平六阶段。
- 完整的心理空间建模。
- 复杂的自主意识模拟。

这些理论可以成为未来的研究参考，但不应为了理论完整而牺牲工程可维护性。

同时，Mnemosyne 本身不代表 Agent 拥有意识或真实情感。

它提供的是可追溯的经验组织、认知更新和反馈机制。

---

## 11. 未来方向

### P0 — Core Infrastructure Stabilization

- 统一核心数据契约。
- 完善服务生命周期。
- 增强事务、幂等与错误恢复。
- 完善模块独立测试。
- 明确服务版本和接口兼容策略。

### P1 — Experience Loop Integration

- 将图式演化接入真实记忆生命周期。
- 将反馈学习与 Recall、Review、Change Plan 联动。
- 验证经验是否实际改善后续检索和行为。
- 建立端到端经验闭环测试。

### P2 — Universal API  SDK

- 统一 REST API。
- SDK。
- MCP Adapter。
- 其他 Agent 框架适配器。

这些属于后续接口建设，不应与当前已完成的服务层能力混淆。

### P3 — Advanced Retrieval

- 更成熟的 Embedding Provider。
- 混合检索优化。
- 多信号校准。
- 语义关联与跨项目检索。

### P4 — Memory Federation

- 多实例协作。
- 跨节点同步。
- 记忆授权与共享。
- 可验证的迁移与恢复。

---

## 12. 项目理念

Mnemosyne 希望探索一种新的 Agent 记忆基础设施：

不是让 Agent 永远保存更多内容，而是让它能够在合适的时间找到正确的证据，理解经验的变化，并在新证据出现时修正过去的判断。

记忆的价值不在于存储了多少，而在于它能否让未来变得更好。

项目：

- 核心实现：https://github.com/canyueY/mnemosyne
- DSH 插件：https://github.com/DSH-Raising-Plan/dsh-mnemosyne

