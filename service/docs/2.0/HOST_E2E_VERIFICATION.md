# DSH 0.2.1 宿主端到端验证

**日期：** 2026-10-31  
**插件提交：** `9eb9b93`（含 `bb99351` 宿主 schema 修复）  
**dsh-tools：** `@deepseek-ai/dsh-tools@0.2.1-rc.5`（真实 npm 包，不是 mock）  
**Node：** v24.21.0  
**Python：** 仓库 `.venv` 的 Python 3.10  
**验证方式：** 真实 Cordis `Context` + 真实 `ToolRuntime`，加载 `dsh-mnemosyne` 的 `apply()`，启动真实 Mnemosyne Python 子进程。

> 这是 **dsh-tools ToolRuntime 宿主级验证**，不是 Electron GUI 对话验证。  
> 它验证工具注册、工具执行、服务启动和进程回收；不验证模型对话轮次。

---

## 1. 安装真实 dsh-tools

```bash
npm install @deepseek-ai/dsh-tools@0.2.1-rc.5
```

验证版本：

```text
dsh-host-test
└── @deepseek-ai/dsh-tools@0.2.1-rc.5
```

---

## 2. 宿主加载

测试宿主使用：

```js
import { Context } from '@deepseek-ai/cordis';
import ToolRuntime from '@deepseek-ai/dsh-tools';

const ctx = new Context();
ctx.provide('systemPrompt', { tools() {}, section() {} });
ctx.provide('config', {
  'dsh-mnemosyne': {
    service_root: '<repo>/service',
    data_dir: '<temp>/host-e2e-data',
    python: '<repo>/.venv/Scripts/python.exe',
    auto_start: true,
    auto_capture: false,
    token: 'host-e2e-token',
  },
});
new ToolRuntime(ctx, { mode: 'native' });
```

然后加载插件：

```js
const plugin = await import('<repo>/src/index.js');
const dispose = await plugin.apply(ctx);
```

`DSH_TOOLS_PATH` 指向真实的：

```text
.../node_modules/@deepseek-ai/dsh-tools/lib/index.js
```

---

## 3. 工具注册结果

注册到的工具：

```text
memory_health
memory_search
memory_get
memory_context
memory_propose
memory_feedback
memory_update
memory_forget
memory_task_status
memory_observe
```

结果：

```json
{
  "missing": [],
  "extra": []
}
```

10/10 注册成功。

每个工具的 `output.schema` 都是：

```json
{
  "type": "object",
  "additionalProperties": true
}
```

这证明 `type: "json"` / 空 `{}` 的 0.2.1 不兼容问题已经消除。

---

## 4. `memory_health`

调用成功：

```json
{
  "ok": true,
  "service": "cognitive-memory",
  "version": "2.0.0",
  "memories": 0,
  "observations": 0,
  "schemas": 0,
  "identity": true,
  "banks": true,
  "authority": true,
  "authority_state": "mnemosyne_primary",
  "mnemosyne_version": "2.0"
}
```

说明：

- 插件按 `auto_start` 启动了真实 Python 服务；
- 动态端口绑定成功；
- token / health 检查成功；
- 服务来自 `<repo>/service`，不是另一个已运行实例。

---

## 5. 工具调用

### `memory_observe`

写入一条临时观察：

```text
host-e2e: 主人喜欢测试 Mnemosyne 宿主接口
```

返回 observation id，`persisted_ok: true`，`retrieval_ready: true`。

### `memory_propose`

基于该 observation 写入 candidate memory，返回 memory id。

### `memory_search`

查询 `Mnemosyne 宿主接口`，返回 **2 条**：

- working memory（由 observation 快通道生成）；
- semantic candidate（由 `memory_propose` 生成）。

说明工具参数校验、HTTP 请求、FTS 检索、返回 schema 均正常。

---

## 6. 进程回收

从 `runtime/service.json` 读取：

```json
{
  "pid": 3684,
  "host": "127.0.0.1",
  "port": 32409,
  "api_prefix": "/api/v1"
}
```

调用插件返回的 `dispose()` 后：

```json
{
  "toolsAfterDispose": [],
  "serviceAliveAfterDispose": false
}
```

并额外检查：

```text
Win32_Process python.exe command line 含 host-e2e-data 的进程：0 个
```

说明：

- 工具注册被撤销；
- Python 子进程被终止；
- 没有残留 `python.exe`；
- Node 进程退出码 `0`。

## 7. 真实 DSH Host（headless）验证

在 ToolRuntime 之后，又用真实 `dsh` CLI + 真实模型跑了一次 DSH Host 会话。

| 项 | 值 |
|---|---|
| DSH CLI | `0.2.1-rc.3`（安装的 DSH app） |
| Profile | 隔离 profile `mnemo-e2e`，bundles 含 `dsh-mnemosyne` |
| 模型 | `deepseek-flash`（deepseek-official） |
| Session | `session-a4852cf1-3ce6-44a6-af2d-2bac81430578` |
| 数据目录 | 临时 `tmp/dsh-gui-e2e-data`，未触碰生产 Bank |
| 结果 | **通过** |

真实模型输出中出现了：

```json
{"type":"tool_call","tool":"memory_health","input":{}}
{"type":"tool_result","status":"completed","result":"{... ok: true ...}"}
{"type":"tool_call","tool":"memory_search","input":{"query":"Mnemosyne host","limit":3}}
{"type":"tool_result","status":"completed","result":"{... count: 2 ...}"}
{"type":"status","phase":"turn_end","reason":{"kind":"completed"}}
```

`memory_health` 返回 `ok: true`、`version: 2.0.0`；`memory_search` 返回 2 条（working + episodic candidate）。

进程回收：

- `service.json` 记录 pid `37764`；
- headless 进程退出后 `Get-Process -Id 37764` → **PID_GONE**；
- `Win32_Process python.exe` 中含 `dsh-gui-e2e-data` 的进程：**0 个**；
- `dsh` / node 会话进程：**0 个残留**；
- `exit=0`。

> 说明：ToolRuntime 验证使用 `@deepseek-ai/dsh-tools@0.2.1-rc.5`；安装的 DSH app 自身是 `0.2.1-rc.3`。  
> 插件 `engines.dsh` 范围覆盖两者；真实 DSH headless 已能加载并调用工具。  
> 仍未验证 Electron 浏览器 GUI 的具体点击/流式 UI，但已覆盖真实模型会话与工具调用。

## 8. 结论

| 检查项 | 结果 |
|---|---|
| 真实 `dsh-tools@0.2.1-rc.5` 安装 | 通过 |
| Cordis `ToolRuntime` 宿主启动 | 通过 |
| 加载 `dsh-mnemosyne` | 通过 |
| 10 个 `memory_*` 工具注册 | 通过 |
| `output.schema` 0.2.1 合法 | 通过 |
| `memory_health` | 通过 |
| `memory_observe` / `memory_propose` / `memory_search` | 通过 |
| 动态 Python 子进程启动 | 通过 |
| `dispose()` 回收工具 | 通过 |
| `dispose()` 回收 Python 进程 | 通过 |

**结论：DSH 0.2.1 宿主接口修复不仅通过 schema 单元测试，也通过了真实 ToolRuntime + 真实 Python 子进程的端到端检查。**

ToolRuntime 与真实 DSH headless 会话均已通过；仍剩 Electron 浏览器 GUI 的界面层验证。
