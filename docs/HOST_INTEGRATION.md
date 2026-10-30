# Host Integration — 桌宠 / 外部 Agent 接入独立 Mnemosyne

## 原则

1. **Node 不依赖宿主**：无 DSH、无桌宠亦可 `mnemosyne start`。  
2. **宿主不拥有 Node**：桌宠只是 Client；权威数据在 Node `data_dir`。  
3. **禁止**宿主 / 插件 `sqlite3.connect` 直连 `memory.db`；一律 REST / SDK / MCP。

## 桌宠（大肥鱼）

配置块 `cognitive_memory`：

| 字段 | 说明 |
| --- | --- |
| `service_root` | **本仓库绝对路径**（用于 `auto_start` 拉起 `src/cognitive_memory/main.py`） |
| `base_url` | 已运行 Node 的 URL；与 token 一致即可通信 |
| `auto_start` | `true`：宿主可代启本仓库进程；`false`：只连已有 Node |
| `data_dir` | 空则默认 `%LOCALAPPDATA%/DSH/cognitive-memory` 或你指定的独立目录 |
| `token` | 与 Node `DSH_MEMORY_TOKEN` 相同 |

解析优先级（宿主 bridge）：

1. 环境变量 `MNEMOSYNE_HOME`  
2. 配置 `service_root`（绝对路径或相对桌宠根）  
3. 同级目录 `mnemosyne`（若存在）  
4. 旧路径 `services/cognitive-memory`（过渡回退）

## 外部 Agent

使用 Python SDK：

```python
from cognitive_memory.sdk import MnemosyneClient

client = MnemosyneClient("http://127.0.0.1:8765", token="...")
client.health()
client.observe({"source_kind": "system", "content": "hi", "producer": "agent-x"})
```

或 TypeScript：`sdk-ts/`（`@mnemosyne/client`）。

Agent 授权见 REST `/api/v1/agents/*`（登记 ≠ 授权；须发 grant）。

## 独立配置示例

见仓库根 [`config/node.example.yaml`](../config/node.example.yaml) 与 CLI：

```bat
mnemosyne config init
mnemosyne config show
mnemosyne doctor
```
