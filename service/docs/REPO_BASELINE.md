# 仓库基线声明（Mnemosyne 3.0）

**生效：** 2026-10-31  
**用途：** 任何 Mnemosyne 3.0 完成度 / GA / Matrix 核对必须先读本文件。

---

## 1. 唯一权威实现

| 角色 | 位置 | 说明 |
| --- | --- | --- |
| **权威仓** | [`canyueY/dsh-mnemosyne`](https://github.com/canyueY/dsh-mnemosyne) | 3.0 合并后的唯一权威仓 |
| **Node / Core** | `service/` | 独立 Python Memory Service、REST/MCP、Memory Bank、测试与文档 |
| **DSH 适配层** | 根目录 `src/` + `package.json` | 启动/守护 Node，注册 `memory_*` 工具 |
| **数据目录** | `%LOCALAPPDATA%\Mnemosyne Memory Bank` | 物理 Memory Bank；不是代码仓 |
| **旧 0.2 插件** | `legacy/dsh-plugin/` | 仅归档追溯，不参与 3.0 主路径 |
| **旧 2.0 仓** | [`canyueY/mnemosyne`](https://github.com/canyueY/mnemosyne) | 已归档，只保留 2.0 历史 |
| **Memory Bank 说明仓** | [`canyueY/mnemosyne-memory-bank`](https://github.com/canyueY/mnemosyne-memory-bank) | 数据契约说明；不是独立数据库 |

> **3.0 不再把 DSH 插件壳与 Node 分成两个仓维护。**  
> 旧 npm `dsh-mnemosyne@0.2` 仍可在 npm 历史中安装，但不再接收新能力；旧状态见 tag `legacy/dsh-plugin-0.2.0`。

---

## 2. 口径

- `service/` 是 Node 与认知核心的权威实现；
- 根目录 `src/` 只是 DSH 接入层，不承载核心记忆逻辑；
- `legacy/dsh-plugin/` 是历史归档，**不得**作为 3.0 能力核对依据；
- 旧 `canyueY/mnemosyne` 不得作为 3.0 新入口；
- 不把路线图（跨 Node 联邦、完整心理建模、通用 SDK/API 等）写成已交付；
- 不声称系统让 Agent 产生意识或真实情感；
- 测试数量、性能指标以当前 CI / 本地测试报告为准，不作营销数字。

---

## 3. 当前最小面（3.0 继承 2.0）

已完成、禁止重做：

- Node CLI、Identity、Memory Bank、Authority、Agent grants；
- 本地 D8 组件、Staging/Cutover、Python + TS SDK；
- 记忆生命周期、图式演化、反馈学习、检索与治理基础；
- Memory Bank 数据目录与旧 DSH 路径迁出。

仍偏黄：

| ID | 项 | 说明 |
| --- | --- | --- |
| Y3 | E6.5 / V8 人工签字 | 2.0 现网 production 双签已归档；3.0 需要按新仓重新确认发布口径 |
| Y4 | D3 闭环 | 2.0 已有情绪 shadow → Bank → feedback E2E；3.0 继续沿用 |
| Y5 | 组件硬沙箱 / 远程 Registry | 可选扩展 |
| Y6 | 全量用户收纳 | ≠ E6.5 小规模试点 |

---

## 4. 宿主与 DSH

- 桌宠 / 其他宿主通过 HTTP / SDK / MCP 接入 `service/`；
- DSH 插件通过根目录适配层启动 Node；
- 插件不是核心逻辑的唯一实现位置；
- 数据目录由 Node 管理，插件不直接写 SQLite。
