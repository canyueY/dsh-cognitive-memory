# 2.0 黄项厚度清单（禁止重做已绿最小面）

**权威仓：** [`canyueY/dsh-mnemosyne`](https://github.com/canyueY/dsh-mnemosyne)  
**上位：** [REPO_BASELINE](REPO_BASELINE.md) · [READINESS](MNEMOSYNE_2.0_READINESS.md) · [GA_STATUS](GA_STATUS.md)

本清单**只**跟踪仍偏黄的厚度。下列已完成，**禁止**再开 Identity / Bank / Node CLI / 本地 D8 / Staging 从零 Epic：

- Node：`doctor/start/stop/status/config/backup`  
- Identity / Banks / Authority + Cutover  
- Agent grants / revoke / audit  
- Interchange + Staging preview/approve/rollback  
- 本地 Component Manifest/Installer/Profiles  
- Python + TS SDK、SSE、policy 执法基础、standalone/DSH 薄化 E2E  

---

## 开放黄项

| ID | Gate/域 | 内容 | 验收 | 状态 |
| --- | --- | --- | --- | --- |
| Y1 | G8 | `dsh-mnemosyne` Legacy Banner + Description 指向本仓 | 公开 README 可见声明 | **完成**（2026-10-31） |
| Y2 | G9 | README/Matrix/READINESS 顶部权威仓声明 | 三处互链 REPO_BASELINE | **完成** |
| Y3 | G2/H | V8 / E6.5 **人工**操作人·复核人签字 | 现网 `mode=production` ok；看板 `IN_PROGRESS` | **完成**（2026-10-31；残月Y 双签） |
| Y4 | G3/D3 | 情绪/反馈闭环与 Bank 抽样 E2E 加厚 | `tests/contract/test_emotion_feedback_bank_e2e.py` | **完成**（2026-10-31） |
| Y5 | G5 | 组件「禁直连 sqlite」已有契约测；可选扩到更多包 | `test_storage_provider_boundary`（components+adapters+mcp） | 可选 |
| Y6 | G7 | 全量 Adoption ≠ E6.5 | 另开里程碑 | 裁切/另开 |
| Y7 | G4 | 裸 `/v1` 别名 | **不做**；文档已标明 `/api/v1` | 关闭 |
| Y8 | G3/P0 | 图式演化：同化/顺应/冲突/版本历史 | `cognition/schema_evolution.py`；4 项经验闭环测试 | **完成（服务层）** |
| Y9 | G3/P1 | 反馈学习：用户/结果/自评分开 | `cognition/feedback_learning.py`；不冒充用户同意 | **完成（服务层）** |
| Y10 | G4/P2 | 可选语义空间：n-gram/可注入 embedding | `retrieval/semantic.py`；只加分不压主排序 | **完成（服务层）** |

更新本表时：只改状态，不把 Missing 能力误写成需重做的绿项。
