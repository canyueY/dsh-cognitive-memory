# Mnemosyne API Spec（REST / MCP / SDK）

**状态：** Implemented-lite（2026-10-30）— 对齐现网代码与 `schemas/openapi.v1.yaml`  
**上位：** [ARCHITECTURE](MNEMOSYNE_2.0_ARCHITECTURE.md) · [ENGINEERING_CONSTRAINTS](ENGINEERING_CONSTRAINTS.md)  
**机器可读契约：** `services/cognitive-memory/schemas/openapi.v1.yaml`  
**前缀：** 所有稳定 REST 路径均为 **`/api/v1/...`**（不是裸 `/v1`）。

本文件描述**已实现**接口与鉴权约定。规划中的额外资源若未出现在 OpenAPI / 本表，不得当作已交付。

---

## 1. 鉴权

| 模式 | 头 | 含义 |
| --- | --- | --- |
| Node Bearer | `Authorization: Bearer <token>` 或 `X-Memory-Token` | 运维超管；可跨 Bank |
| Agent Grant | `X-Agent-Id` + `X-Agent-Token` | 仅 grant 内 permissions / banks；有 Agent 头则**必须**过 grant，不可混用伪造 Bearer 绕过 |

原则：

- 安装组件 ≠ 授权 Agent。  
- 注册 Agent ≠ 已发 grant。  
- 硬删另需 Capability Gate `MEMORY_HARD_DELETE` + `confirm=true`。  
- 策略字段 `allow_train` / `allow_forward` / `allow_store`：见 §6；执法入口在 `governance/policy.py`。

健康探活：`GET /healthz`（无鉴权，仅进程存活）。

---

## 2. 核心资源（已实现）

| 方法 | 路径 | 职责 |
| --- | --- | --- |
| GET | `/api/v1/health` | 服务健康与计数 |
| GET | `/api/v1/node` | Node 信息与鉴权约定 |
| GET | `/api/v1/contract` | Memory Service Contract 快照（`adapter_may_bypass_service=false`） |
| POST | `/api/v1/observations` | 提交 Observation |
| POST | `/api/v1/memories` | 提案/写入记忆 |
| GET | `/api/v1/memories/{id}` | 读记忆 |
| PATCH | `/api/v1/memories/{id}` | 更新（含版本冲突 409） |
| DELETE | `/api/v1/memories/{id}` | 软删；`?hard=true&confirm=true` 硬删 |
| POST | `/api/v1/memories/search` | 检索 |
| POST | `/api/v1/retrieve` | 统一检索（Planner） |
| POST | `/api/v1/contexts/build` | 构建上下文 |
| POST | `/api/v1/feedback` | 反馈（可触发 promote 闭环） |
| POST | `/api/v1/evidence` | 附着证据 |
| GET | `/api/v1/memories/{id}/evidence` | 列出证据 |
| GET | `/api/v1/banks` | Memory Banks |
| GET/POST | `/api/v1/entities` | Entity 最小面 |
| GET | `/api/v1/events/stream` | SSE 事件流 |

---

## 3. Identity / Agent / Authority / Adoption

| 方法 | 路径 | 职责 |
| --- | --- | --- |
| GET/POST | `/api/v1/identities` | Principals |
| GET | `/api/v1/identities/{id}` | 单个主体 |
| POST | `/api/v1/agents/register` | 登记 Agent（≠ 授权） |
| POST | `/api/v1/agents/{id}/grants` | 发 grant |
| GET | `/api/v1/agents/grants` | 列出 grants |
| POST | `/api/v1/agents/{id}/revoke` | 撤销 |
| POST | `/api/v1/agents/check` | 权限预检 |
| GET | `/api/v1/agents/audit` | 审计 |
| POST | `/api/v1/agents/act/search` | Agent 检索入口（须 agent_token） |
| GET | `/api/v1/authority` | 权威状态 |
| POST | `/api/v1/authority/transition` | 状态转移（`dual_sync` 须 `allow_dual`） |
| GET | `/api/v1/authority/cutover/preview` | Cutover 预览 |
| POST | `/api/v1/authority/cutover/execute` | Cutover（须 `confirm`） |
| POST | `/api/v1/adoption/export` | 导出 Interchange JSONL（受 `allow_forward` 执法） |

---

## 4. 组件 / 任务 / 认知扩展

| 方法 | 路径 | 职责 |
| --- | --- | --- |
| GET | `/api/v1/components` | 已装组件 |
| GET | `/api/v1/components/profiles` | Composition Profiles |
| POST | `/api/v1/components/install` | 本地安装 |
| POST | `/api/v1/components/{id}/authorize\|enable\|disable\|configure\|remove` | 生命周期 |
| GET | `/api/v1/components/{id}/health` | 组件健康 |
| POST/GET | `/api/v1/tasks` / `{id}` | 后台任务 |
| POST | `/api/v1/relations` | 关系边 |
| GET | `/api/v1/memories/{id}/relations` | 列出关系 |
| POST/GET | `/api/v1/changes/*` | 变化检测 / ChangePlan |
| POST | `/api/v1/emotion/*` | 情绪 shadow（默认不写 LT） |
| POST/GET | `/api/v1/schemas/*` | Schema 网络 |
| GET/POST | `/api/v1/capabilities*` | Capability Gate |
| POST | `/api/v1/rl/train` / `/rl/deploy` | RL stubs（默认 LOCKED + `allow_train`） |
| POST | `/api/v1/value/*` | Value 分析 stubs |

完整枚举以 OpenAPI 与 `api/app.py` 为准；契约测试：`tests/contract/test_openapi_contract.py`。

---

## 5. MCP / SDK

### MCP（`cognitive_memory.mcp`）

建议工具面（写操作须确认）：

- `memory_search` / `memory_get` / `memory_context`
- `memory_observe`（写确认）
- `memory_feedback`
- `memory_import_preview`（写确认）

MCP **不是**唯一协议；与 REST 共用 MemoryService。

### SDK

| SDK | 位置 | 说明 |
| --- | --- | --- |
| Python | `cognitive_memory.sdk.MnemosyneClient` | 主参考实现 |
| TypeScript | `services/cognitive-memory/sdk-ts`（`@mnemosyne/client`） | 薄封装子集 |

---

## 6. 策略字段执法（字段 ≠ 默认可信）

记忆 `metadata.policy`（或顶层兼容键）：

```json
{
  "allow_store": true,
  "allow_forward": false,
  "allow_train": false,
  "retain_until": "2027-01-01T00:00:00Z"
}
```

| 字段 | 默认 | 执法点 |
| --- | --- | --- |
| `allow_store` | `true` | 提案写入前拒绝 `false` |
| `allow_forward` | `false` | Adoption/Interchange 导出过滤 |
| `allow_train` | `false` | RL train 入口拒绝未允许样本 |
| `retain_until` | 无 | 过期则禁止 forward，并标 `retention_expired` |

未声明时按上表默认；**声明存在不等于历史数据已回溯执法**——新写入与导出/训练路径强制检查。

---

## 7. 错误与兼容

- `401` 未鉴权 / token 无效  
- `403` grant 拒绝 / capability locked / 策略拒绝  
- `404` 资源不存在  
- `409` 版本冲突 / 非法 Authority 转移  

破坏性变更须：升 OpenAPI version、更新本文件、契约测试失败即阻断。

---

## 8. 非目标（本 Spec 不承诺）

- 裸路径 `/v1/*` 别名  
- 跨 Node 联邦 / PCIP 生产 API  
- 组件市场远程 Registry API  
- Exactly-once 事件投递（仅至少一次 + 幂等）
