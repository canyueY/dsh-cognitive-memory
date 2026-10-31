# DSH 外置演化记忆系统 — 总体技术方案（落地索引）

> 架构版本 **V1.0** · 代码位置：`services/mnemosyne` + `_dsh_plugins/dsh-mnemosyne`  
> 目标：独立可替换的外置记忆服务；**当前默认副记忆**，与 A-MEM 并行试用，转正门槛见插件 [TRIAL.md](../_dsh_plugins/dsh-mnemosyne/TRIAL.md)（零配置启动、对话闭环、备份迁移、CI、一周无丢数据）。

本文是立项与开发拆分的**落地索引**；原则与接口以实现代码与 OpenAPI 为准。

**文档地图**

| 文档 | 内容 |
| --- | --- |
| [`../services/mnemosyne/README.md`](../services/mnemosyne/README.md) | 愿景、拟人化价值、结构选型 |
| [`MNEMOSYNE_ROADMAP.md`](./MNEMOSYNE_ROADMAP.md) | 算法优化清单、借鉴项目、P0–P3 排期 |
| [`MNEMOSYNE_STATE_MACHINE.md`](./MNEMOSYNE_STATE_MACHINE.md) | 状态机、证据分层、冲突/衰减、验收测试 |

核心链路：`原始事件 → 短期缓冲 → 事件关联 → 情节 → 行为模式 → 筛选 → 长期记忆 → 用户模型`  
视频：`runStoryboard → 片段 → 主题/实体 → 临时记忆 → 跨来源兴趣 → 长期记忆`

**六问（优化焦点，而非继续加层）：** 值得记什么？如何组成经历？何种证据够晋升？冲突如何更新？如何改善对话行为？如何证明有效？

## 目标摘要

独立记忆子进程，双通道：

- **快速**：工作记忆、即时检索、上下文构建（不阻塞对话）。
- **慢速**：情节归纳、兴趣候选、冲突/晋升、反馈修正（Outbox + Tasks 可恢复）。

底线：观察≠记忆、推断≠事实、事件可恢复、检索可降级、MCP/REST 共用一个 `MemoryService`。

图谱（P1 拟接 Graphiti）负责时间关系与混合检索；**心理学状态机**负责准入 / 证据 / 晋升 / 衰减 / 纠错。

## 仓库布局

```
services/mnemosyne/          # Python FastAPI + SQLite 服务
_dsh_plugins/dsh-mnemosyne/  # Node Host Adapter（子进程 + DSH tools）
docs/MNEMOSYNE_SPEC.md       # 本索引
docs/MNEMOSYNE_ROADMAP.md    # 优化清单与排期
docs/MNEMOSYNE_STATE_MACHINE.md  # 状态机规格草案
```

数据目录（不进仓库）：`%LOCALAPPDATA%/DSH/mnemosyne/`

## 实施阶段对照

| 阶段 | 状态（V0.1 骨架） |
| --- | --- |
| 1 工程骨架 · 健康检查 · 子进程 | ✅ REST `/health` · `MemoryProcessHost` |
| 2 CRUD · 版本 · 幂等 | ✅ `MemoryService` |
| 3 Outbox / Inbox / Tasks | ✅ `BackgroundRuntime` |
| 4 FTS5 · contexts/build | ✅ 可降级 LIKE |
| 5 认知流水线 | ✅ 规则版 consolidate / promote（可换 LLM） |
| 6 桌宠对话闭环 | ✅ `mnemosyne_bridge` + orchestrator / gatekeeper |
| 7 迁移备份恢复测试 | ✅ `cli backup/restore` + `tests/recovery` |
| 8 管理后台 / A-MEM 迁移 | ✅ 面板 + `migrate-amem` / `scripts/migrate_amem_to_cognitive.py` |
| 9 视频观察 → observation | ✅ `episode_write` → `submit_video_observation` |
| 10 状态机 + 证据规则（P0） | ⏳ 见 STATE_MACHINE 草案 |
| 11 Graphiti 混合检索（P1） | ⏳ |
| 12 兴趣证据分层与晋升（P2） | ⏳ |
| 13 空闲巩固与算法实验（P3） | ⏳ |

## 桌宠接入（已落地 · 默认副记忆）

1. `Murasame/mnemosyne_bridge.py`：HTTP 客户端，可 `auto_start` 拉起子进程。
2. `memory_orchestrator`：可把 `mnemosyne` 放进 retrieval/persist；**仅当 `replace_a_mem=true` 时跳过 A-MEM**（默认 `false`）。
3. `gatekeeper_memory`：启用时优先 `contexts/build`；无命中/未启用时回退 A-MEM。
4. `config.example.json`：`mnemosyne.enable=true`，`replace_a_mem=false`；勿在试用期关掉 A-MEM。
5. 管理后台「外置演化记忆」面板：`/api/mnemosyne/*`。
6. 运维：`python -m mnemosyne.cli backup|restore|migrate-amem`（日备脚本见插件 `scripts/backup-daily.ps1`）。

**尚未验收（不能当主记忆的原因）：** 真实对话 `observe → 下一轮自动 context`；安装进 DSH profile 后零配置启动的现场验证；连续一周无丢/串记忆；端到端 CI。

## 相关文档

- 现状记忆总图（含 A-MEM）：[MEMORY_MAP.md](./MEMORY_MAP.md)
- 算法优化与借鉴：[MNEMOSYNE_ROADMAP.md](./MNEMOSYNE_ROADMAP.md)
- 状态机与证据规范：[MNEMOSYNE_STATE_MACHINE.md](./MNEMOSYNE_STATE_MACHINE.md)
- 试用 / 转正：[TRIAL.md](../_dsh_plugins/dsh-mnemosyne/TRIAL.md)
- A-MEM 仍为 **并行主线之一**；外置服务转正前勿标记为已废弃。
