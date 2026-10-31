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
  "version": "3.0.0",
  "memories": 0,
  "observations": 0,
  "schemas": 0,
  "identity": true,
  "banks": true,
  "authority": true,
  "authority_state": "mnemosyne_primary",
  "mnemosyne_version": "3.0"
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

---

## 7. 结论

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

仍需补一项：在 Electron DSH GUI 的真实会话里加载插件并完成一次模型工具调用。本次验证不覆盖 GUI 会话、模型生成和用户确认链路。
