# Judgment Supersession & Temporal Traceability

**状态：** Phase 1/2 垂直切片已实现；完整历史重放/L0–L6 全链路仍未完成  
**迁移：** `015_judgment_temporal_v1`  
**新增测试：** `tests/unit/test_claim_temporal.py`（7 项）

## 1. 已实现的时间字段

Claim 行新增：

```text
validity_from
validity_to
superseded_at
superseded_by
retracted_at
expired_at
last_confirmed_at
```

语义：

| 字段 | 含义 |
|---|---|
| `validity_from` / `validity_to` | 判断成立的半开区间起点/终点 |
| `superseded_at` | 系统正式确认旧判断被替代的时间 |
| `superseded_by` | 替代它的新 Claim ID |
| `retracted_at` | 原判断被确认错误并撤销的时间 |
| `expired_at` | 自然过期时间 |
| `last_confirmed_at` | 最近一次确认仍成立的时间 |

反证出现不会自动填写 `superseded_at`；只有显式 `supersede` / `retract` / `expire` 才写入终止时间。

## 2. 生命周期

新增 `retracted` 状态：

```text
proposed
supported
qualified
verified
disputed
rejected
retracted
expired
superseded
```

状态转换仍由 `ClaimLifecycleEngine` 统一执行；`superseded` 为终态，`retracted` 只能再转 `superseded`。

## 3. DecisionRecord

新增表：

```text
claim_decision_records
```

字段：

```text
decision_id
claim_id
operation
previous_status
next_status
trigger_evidence_json
replacement_claim_id
reason
decision_at
actor
confidence
trace_id
schema_version
created_at
```

- `propose` 产生一条 `propose` 决策；
- `transition` / `supersede` / `retract` / `expire` 产生对应决策；
- `verified` 产生 `verified` 决策；
- `redirect` 产生 `superseded` 决策；
- 决策记录 append-only，不覆盖历史。

`claim_lifecycle_events` 同步新增 `trace_id` / `decision_id`，从而与 `JudgmentTrace` 关联。

## 4. API

新增：

```text
POST /api/v1/claims/{claim_id}/supersede
POST /api/v1/claims/{claim_id}/retract
POST /api/v1/claims/{claim_id}/expire
GET  /api/v1/claims/{claim_id}/decisions
```

`POST /claims/propose` 支持：

```json
{
  "text": "...",
  "validity_from": "2026-01-01T00:00:00Z",
  "validity_to": null
}
```

`POST /claims/{id}/supersede`：

```json
{
  "replacement_claim_id": "clm_...",
  "reason": "preference changed",
  "evidence_refs": ["obs_..."],
  "actor": "user",
  "confidence": 0.9
}
```

## 5. 下游影响

`transition` / `supersede` 返回 `impact`：

```json
{
  "impact": { ... TMS impact ... }
}
```

当前只做到 **TMS 影响预览**，尚未自动生成下游 Knowledge/Strategy 的重新评估任务；这属于下一步。

## 6. 已验证场景

`test_claim_temporal.py` 覆盖：

1. 新判断替代旧判断：旧 Claim 保留、`superseded_at` / `validity_to` / `superseded_by` 正确；
2. 撤销：`retracted_at` 写入，不被误标为 `superseded`；
3. 自然过期：`expired_at` 写入，不与撤销混用；
4. `verified` 写入 `last_confirmed_at`；
5. 非法 replacement 不修改旧 Claim；
6. API `supersede` + `decisions`；
7. API `retract`。

执行结果：

```text
pytest -q tests/unit/test_claim_temporal.py
7 passed
```

完整套件：

```text
pytest -q
228 passed
```

## 7. 尚未完成

- 按历史时刻重建 Claim 状态（as-of query）；
- 从 Observation → Evidence → Claim → DecisionRecord 的完整 Replay；
- 下游 Knowledge/Strategy 的自动重新评估任务；
- “反证出现 → contested/needs_review → 决策提交”的完整时间回路；
- L0–L6 的 Trace 完整性/异常检测指标；
- 生产历史数据迁移。

这次完成的是 **可追溯失效事件的最小闭环**，不是完整的时间回路终态。
