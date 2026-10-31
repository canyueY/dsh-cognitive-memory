# Host Integration — 桌宠 / 外部 Agent 接入独立 Mnemosyne

## 原则

1. **Node 不依赖宿主**：无 DSH、无桌宠亦可 `mnemosyne start`。  
2. **宿主不拥有 Node**：桌宠只是 Client；权威数据在 **Mnemosyne Memory Bank**（`data_dir`）。  
3. **代码仓 ≠ 记忆库**：`mnemosyne/` 是源码/CLI；`Mnemosyne Memory Bank` 是独立数据目录。  
4. **禁止**宿主 / 插件 `sqlite3.connect` 直连 `memory.db`；一律 REST / SDK / MCP。  
5. **禁止**静默回退 `services/cognitive-memory`。

## 两个文件夹

| 角色 | 默认位置 | 内容 |
| --- | --- | --- |
| Mnemosyne（Node 代码） | 桌宠根下 `mnemosyne/` 或独立 clone | Python 包、CLI、组件 |
| **Mnemosyne Memory Bank** | `%LOCALAPPDATA%\Mnemosyne Memory Bank` | `data/memory.db`、`runtime/`、`logs/` |

环境变量（优先级高→低）：`MNEMOSYNE_MEMORY_BANK` → `MNEMOSYNE_DATA_DIR` → `DSH_MEMORY_DATA_DIR`（旧兼容）→ 上述默认。

旧路径 `%LOCALAPPDATA%\DSH\cognitive-memory` **不再是默认**。迁移：

```bat
set PYTHONPATH=src
py -3 -m cognitive_memory.node_cli memory-bank migrate-legacy
```

## 桌宠（大肥鱼）

配置块 `cognitive_memory`：

| 字段 | 说明 |
| --- | --- |
| `service_root` | **本仓库路径**（`mnemosyne` 或绝对路径） |
| `base_url` | 已运行 Node 的 URL |
| `auto_start` | `true`：宿主代启；`false`：只连已有 Node |
| `data_dir` | 空 → Memory Bank 默认路径；**一个实例一个 data_dir** |
| `token` | 与 Node `DSH_MEMORY_TOKEN` 相同 |

解析优先级（宿主 bridge）：

1. 环境变量 `MNEMOSYNE_HOME`  
2. 配置 `service_root`  
3. `桌宠/mnemosyne`  
4. 同级 `../mnemosyne`  
5. **找不到则报错提示**（不再回退 `services/cognitive-memory`）

## 外部 Agent

```python
from cognitive_memory.sdk import MnemosyneClient

client = MnemosyneClient("http://127.0.0.1:8765", token="...")
client.health()
```

## 独立配置示例

见 [`config/node.example.yaml`](../config/node.example.yaml)：

```bat
mnemosyne memory-bank init
mnemosyne config init
mnemosyne doctor
```
