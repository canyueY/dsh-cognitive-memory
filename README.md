# Mnemosyne

**Independent Personal Cognitive Infrastructure** — 可独立安装、配置、运行的个人认知记忆 Node。

> **基线声明（必读）**  
> - **权威仓（2.0 Node）：** 本仓库 [`canyueY/mnemosyne`](https://github.com/canyueY/mnemosyne)  
> - **不是 2.0 标尺：** 公开 npm / GitHub [`dsh-mnemosyne`](https://github.com/canyueY/dsh-mnemosyne)（DSH 插件历史壳）  
> - 完成度 / GA / Matrix 核对见 [`docs/REPO_BASELINE.md`](docs/REPO_BASELINE.md) · [`docs/GA_STATUS.md`](docs/GA_STATUS.md)；**禁止**用旧 `dsh-mnemosyne/service` 盘点否定本仓能力。

本仓库从桌宠 monorepo 的 `services/cognitive-memory` **拆出**，与宿主（大肥鱼 / DSH / 其他 Agent）**地址分离、配置独立**，通过 HTTP / SDK / MCP 接入。

> **经验闭环：** 记忆不是越积越多，而是让新经验改善下一次检索与行动。  
> 图式演化（同化/顺应/冲突）、反馈学习（用户/结果/自评）与可选语义空间见 [`docs/MNEMOSYNE_EXPERIENCE_LOOP.md`](docs/MNEMOSYNE_EXPERIENCE_LOOP.md)。

| | |
| --- | --- |
| GitHub | https://github.com/canyueY/mnemosyne |
| 包名（pip） | `mnemosyne` |
| Python 包 | `cognitive_memory`（导入名保持稳定） |
| 默认端口 | `127.0.0.1:8765` |
| CLI | `mnemosyne` |
| 本地常见路径 | 桌宠根目录下 `mnemosyne/` |

---

## 1. 独立安装

```bat
cd /d D:\path\to\mnemosyne
py -3 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

初始化数据目录与配置（任意空目录，**不必**放在桌宠仓库内）：

```bat
set MNEMOSYNE_HOME=D:\path\to\mnemosyne
set DSH_MEMORY_DATA_DIR=%LOCALAPPDATA%\Mnemosyne\node
set DSH_MEMORY_TOKEN=change-me
mnemosyne --data-dir "%DSH_MEMORY_DATA_DIR%" config init
mnemosyne --data-dir "%DSH_MEMORY_DATA_DIR%" doctor
mnemosyne --data-dir "%DSH_MEMORY_DATA_DIR%" start --host 127.0.0.1 --port 8765 --token %DSH_MEMORY_TOKEN%
```

健康检查：

```bat
curl -H "Authorization: Bearer %DSH_MEMORY_TOKEN%" http://127.0.0.1:8765/api/v1/health
```

示例配置字段见 [`config/node.example.yaml`](config/node.example.yaml)。运维说明：[`docs/MNEMOSYNE_NODE_OPERATIONS.md`](docs/MNEMOSYNE_NODE_OPERATIONS.md)。

---

## 2. 与桌宠 / 其他宿主对接

宿主**不内嵌**记忆库代码，只作为 Client：

1. 本仓库独立启动 Node（或由宿主 `auto_start` 指向本仓库根目录）。
2. 宿主配置：

```json
{
  "cognitive_memory": {
    "enable": true,
    "auto_start": true,
    "service_root": "D:/HuaweiMoveData/Users/残月Y/Desktop/桌宠/mnemosyne",
    "base_url": "http://127.0.0.1:8765",
    "token": "与 DSH_MEMORY_TOKEN 一致",
    "data_dir": ""
  }
}
```

也可不设 `service_root`，只填 `base_url` + `auto_start: false`（完全外置进程）。

环境变量（可选）：

| 变量 | 含义 |
| --- | --- |
| `MNEMOSYNE_HOME` | 本仓库根目录（宿主解析启动入口时优先） |
| `DSH_MEMORY_DATA_DIR` | Node 数据目录 |
| `DSH_MEMORY_TOKEN` | Bearer token |
| `DSH_MEMORY_BASE_URL` | 已运行 Node 的 URL |
| `DSH_MEMORY_HOST` / `PORT` | 监听地址 |

对接细节：[`docs/HOST_INTEGRATION.md`](docs/HOST_INTEGRATION.md)。

---

## 3. 自检

```bat
set PYTHONPATH=src
py -3 -m pytest tests -q
py -3 scripts\mnemosyne_readiness_suite.py
py -3 scripts\mnemosyne_clean_install_e62.py
```

---

## 4. 与旧 monorepo 的关系

- **权威源码**：本仓库（独立演进、独立发版）。
- 桌宠仓库内若仍有 `services/cognitive-memory`，视为**过渡副本/兼容回退**；新改动应落在本仓。
- 公开 npm `dsh-mnemosyne` 不是本仓；本仓是 Python Node + REST/MCP。

许可：AGPL-3.0-or-later（见 `LICENSE`）。
