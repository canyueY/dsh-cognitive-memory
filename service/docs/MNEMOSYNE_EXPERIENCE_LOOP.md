# 经验闭环：记忆、图式、回忆与反馈

> 上位：[REPO_BASELINE](REPO_BASELINE.md) · [ARCHITECTURE](MNEMOSYNE_2.0_ARCHITECTURE.md) · [YELLOW_BACKLOG](YELLOW_BACKLOG.md)

目标不是让记忆越来越多，而是让**新经验改善未来的检索、判断和行动**。

```text
                ┌─────────────────────┐
                │      新经历           │
                │ Observation / Event  │
                └──────────┬──────────┘
                           ↓
                ┌─────────────────────┐
                │      记忆编码         │
                │ Evidence / Candidate │
                └──────────┬──────────┘
                           ↓
                ┌─────────────────────┐
                │      记忆组织         │
                │ Memory Bank / Schema │
                └──────────┬──────────┘
                           ↓
                ┌─────────────────────┐
                │      情境回忆         │
                │ Retrieval / Planner  │
                └──────────┬──────────┘
                           ↓
                ┌─────────────────────┐
                │      行为与反馈       │
                │ Action / Feedback    │
                └──────────┬──────────┘
                           ↓
                ┌─────────────────────┐
                │      经验重新评估     │
                │ Consolidation        │
                └──────────┬──────────┘
                           │
                           └────→ 更新记忆与图式
```

## P0 — 图式演化

**问题：** 新经验是在补充旧认知，还是推翻旧认知？

**实现：** `src/cognitive_memory/cognition/schema_evolution.py`

| 模式 | 条件 | 行为 |
| --- | --- | --- |
| `assimilation` | 无反证 | 置信度小幅上升，图式保持 ACTIVE |
| `accommodation` | 有反证但仍是少数，或 applicability 改变 | 修正证据/边界/置信度，保留图式身份 |
| `conflict` | 反证达到或超过支持证据 | 图式进入 `CONTESTED`，不静默覆盖 |

- 复用 `cognitive_schemas` / `schema_versions` / `network_links`；
- 在 schema payload 内记录 `evolution_history`；
- `evolve_schema(..., confirm=False)` 默认只预览，`confirm=True` 才写版本；
- 与 `change_plan` / `schema_network` 的拆分、合并、影响追踪兼容。

## P1 — 反馈学习

**问题：** Agent 的行为结果如何改变下一次决策？

**实现：** `src/cognitive_memory/cognition/feedback_learning.py`

三类信号分开：

| 来源 | 信号 | 置信度权重 | 能否直接晋升 |
| --- | --- | ---: | --- |
| `user_explicit` | 用户明确说有用/错误 | 0.10 | 有用时可走既有 promote |
| `outcome` | 实际结果成功/失败 | 0.06 | 否 |
| `self_eval` | Agent 自评 | 0.02 | 否 |

- `apply_feedback_learning()` 把信号写入 `metadata.learning_history`；
- `user_explicit` 继续复用 `MemoryService.feedback()` 的审计、review task、promote 闭环；
- 结果/自评只调置信度，不冒充用户同意；
- 负信号生成 `review_required`，交给后续 review / change plan。

## P2 — 可选语义空间

**问题：** 如何发现不同时间、不同表达之间的隐含关联？

**实现：** `src/cognitive_memory/retrieval/semantic.py`

- 默认 `hashed_embedding()`：字符 n-gram + 稳定哈希，零依赖、离线可用；
- 可注入 `EmbeddingProvider` 换成真实模型向量；
- `SemanticScorer.blend(lexical, semantic, weight<=0.6)`：语义只做加分，不压过证据/时间/情境主排序；
- 不替换现有 FTS / planner / scoring，只是可选信号。

```python
from cognitive_memory.retrieval.semantic import SemanticScorer

scorer = SemanticScorer()
score = scorer.score("喜欢夜航星", "夜航星是用户喜欢的歌")
final = SemanticScorer.blend(lexical=0.8, semantic=score, weight=0.25)
```

## 不进入主干

- **社会学习四过程**（注意/保持/复现/动机）与**道德发展三水平六阶段**暂不产品化；
- 它们是未来扩展能力，不应为了理论完整增加工程复杂度；
- 当前只保留接口位置：反馈来源可区分、图式可演化、关系可审计。

## 验收状态

| 项 | 状态 |
| --- | --- |
| P0 图式演化模块 + 单元测试 | ✅ |
| P1 反馈学习模块 + 单元测试 | ✅ |
| P2 可选语义评分 + 单元测试 | ✅ |
| API / MCP 暴露 | 后续（当前是服务层能力） |
| 全量测试 | `pytest` 119 passed |
| 正式 GA | 仍需 V8 / E6.5 人工签字与全量 Adoption |
