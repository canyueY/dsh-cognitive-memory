# 仓库基线声明（防过时审计）

**生效：** 2026-10-31  
**用途：** 任何 2.0 完成度 / GA / Matrix 核对必须先读本文件。

---

## 1. 权威实现

| 角色 | 仓库 | 说明 |
| --- | --- | --- |
| **权威 Node（2.0）** | [`canyueY/mnemosyne`](https://github.com/canyueY/mnemosyne) | 独立 Personal Cognitive Node；本地路径通常为桌宠根下 `mnemosyne/` |
| 宿主（桌宠） | [`canyueY/MurasamePet`](https://github.com/canyueY/MurasamePet) | **Client only**；`cognitive_memory_bridge` HTTP 接入 |
| 过渡副本 | `MurasamePet/services/cognitive-memory` | **仅归档**；宿主**不再**静默回退 |
| **Mnemosyne Memory Bank** | `%LOCALAPPDATA%\Mnemosyne Memory Bank` | 独立数据目录（≠ 代码仓；≠ `DSH\cognitive-memory`） |
| **非标尺** | [`canyueY/dsh-mnemosyne`](https://github.com/canyueY/dsh-mnemosyne)（npm `dsh-mnemosyne`） | DSH 插件发行壳 / 历史公开包；**不得**作为 2.0 GA 完成度尺子 |

**禁止**用下列材料否定本仓已实现能力：

- 仅打开旧 `dsh-mnemosyne/service/` 目录结构做盘点  
- 仅统计 `services/cognitive-memory` 早期 34 个 unit 测试  
- 把「没有裸路径 `/v1`」当成「没有 REST」（实际前缀为 **`/api/v1`**）

---

## 2. `dsh-mnemosyne` 归档 / 同步策略

### 2.1 定位

`dsh-mnemosyne` = **DSH 宿主侧插件分发通道**（可选 peer：DSH）。  
`canyueY/mnemosyne` = **独立 Node + 认知核心 + 2.0 契约**。

二者不是同一提交、同一产品面。

### 2.2 策略（签字）

| 项 | 决定 |
| --- | --- |
| 是否 GitHub Archive 整个 `dsh-mnemosyne` | **暂不强制 Archive**（避免打断 npm 既有安装）；改为 **Legacy Banner + 描述跳转** |
| 是否把本仓全量 Node 同步进 npm 包 | **否**。Node 以本仓 / PyPI（未来）为准；npm 包不假装已是 2.0 Node |
| 允许同步进 `dsh-mnemosyne` 的内容 | 仅：README 指向、版本说明、可选 **薄 Client / tool-spec**；禁止把未发布的 Node 内核 silently 覆盖进旧 `service/` 冒充已同步 |
| 审计规则 | Capability Matrix / GA Gate **只认** `canyueY/mnemosyne`（及本仓 tag） |
| 宿主集成 | 桌宠 `service_root=mnemosyne` 或 `MNEMOSYNE_HOME`；DSH 插件若仍安装 npm 包，应通过 HTTP/SDK 连本 Node，而不是内嵌旧 `service/` 写库 |

### 2.3 操作清单

1. `dsh-mnemosyne` README 顶部增加 Legacy 声明（指向本仓）。  
2. GitHub 仓库 Description / About 增加「2.0 Node → canyueY/mnemosyne」。  
3. 本仓 Matrix / README / READINESS 引用本文件。  
4. 若未来 npm 大版本：发布 **client-only** 包或 major bump 并弃用内嵌旧 service；另开里程碑，不阻塞当前 GA 最小面。

---

## 3. 仍偏黄的厚度（非「没做 Identity/Bank/CLI」）

下列**不得**再开重复 Epic 重做已有最小面：

| ID | 项 | 说明 |
| --- | --- | --- |
| Y1 | G8 仓库叙事统一 | 本文件 + Legacy Banner |
| Y2 | G9 文档索引 | README/Matrix/READINESS 互链权威仓 |
| Y3 | E6.5 / V8 人工签字 | **完成**：现网 production 双签；试点 `IN_PROGRESS` |
| Y4 | D3 闭环验收加厚 | **完成**：情绪 shadow→Bank 隔离→feedback promote E2E |
| Y5 | 组件硬沙箱 / 远程 Registry | 市场裁切；禁直连 sqlite 契约可再扩包（可选） |
| Y6 | 全量用户收纳 | ≠ E6.5 小规模试点 |

**已完成最小面、禁止重做：** Node CLI、Identity、Memory Bank、Authority、Agent grants、本地 D8、Staging/Cutover、Python+TS SDK、policy 执法基础。
