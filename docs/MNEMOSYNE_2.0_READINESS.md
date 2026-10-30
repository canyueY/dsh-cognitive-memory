# Mnemosyne 2.0 Readiness Gate（证据账本）

> **权威仓：** [`canyueY/mnemosyne`](https://github.com/canyueY/mnemosyne) · **非标尺：** [`dsh-mnemosyne`](https://github.com/canyueY/dsh-mnemosyne)（见 [REPO_BASELINE](REPO_BASELINE.md)）

**状态：** Partial Evidence（2026-10-31）— 最小面可声明就绪；**不等于**正式收纳全体用户  
**套件：** `scripts/mnemosyne_readiness_suite.py` → `tmp/mnemosyne_readiness_report.json`  
**上位：** [GA_STATUS](GA_STATUS.md) · [CAPABILITY_MATRIX](MNEMOSYNE_2.0_CAPABILITY_MATRIX.md) · [YELLOW_BACKLOG](YELLOW_BACKLOG.md) · [REPO_BASELINE](REPO_BASELINE.md)

---

## Gate 对照

| Gate | 必要性 | 现状 | 证据 |
| --- | --- | --- | --- |
| G1 Node Independence | 必须 | ✅ | `mnemosyne doctor/health`；套件 health |
| G2 Storage Safety | 必须 | ✅ | 现网 V8 `mode=production` ok（57168 memories）；[签字单](reports/v8-production-backup-signoff.md)；E6.5 `IN_PROGRESS` |
| G3 Cognitive Core | 必须 | ✅ | Observation→Memory；情绪/反馈/Bank E2E（Y4）；套件 G3 |
| G4 Interoperability | 必须 | Partial→增强 | Python+TS SDK；CRUD Agent 执法；SSE；standalone + DSH 薄化 E2E；[API_SPEC](MNEMOSYNE_API_SPEC.md) |
| G5 Component Management | 必须 | Partial | 本地 Component Manager；无市场（裁切） |
| G6 Governance | 必须 | ✅ 增强 | grants + CRUD + policy(store/forward/train/retention)；硬删闸；MCP 写确认 |
| G7 Migration | 必须 | Partial→增强 | Staging(dedupe+分层回滚)+Cutover；Admin Adoption；export 受 allow_forward |
| G8 Compatibility | 必须 | Partial→增强 | Compat Gateway；**仓库叙事已统一到本仓**；宿主 A-MEM/Mem0 仍可并行过渡 |
| G9 Documentation | 必须 | Partial→增强 | API_SPEC / Matrix / REPO_BASELINE / YELLOW_BACKLOG；全量收纳仍另开 |
| G10 Federation | **裁切 → 2.1+** | N/A | 跨 Node 联邦不做本 GA 完成声明 |

---

## 同 Node 多 Agent（2.0 必须）

| 能力 | API / 模块 |
| --- | --- |
| 登记主体 | `POST /api/v1/agents/register` |
| 发授权（权限/Bank/有效期/consent） | `POST /api/v1/agents/{id}/grants` |
| 撤销 | `POST /api/v1/agents/{id}/revoke` |
| 审计 | `GET /api/v1/agents/audit` |
| Agent 检索入口 | `POST /api/v1/agents/act/search`（须 agent_token） |

**原则：** Node Bearer = 运维超管；Agent Token 仅 grant 范围内有效；安装组件 ≠ 授权 Agent。

---

## 裁切签字（执行记录）

- **纳入 2.0 GA：** 同 Node 多 Agent 身份/权限/审计；D8 本地组件面；Migration Staging 最小面。  
- **排除（2.1+）：** 跨 Node 联邦 / PCIP 生产 / P2P / Relay / 组件市场。  
- **禁止**将排除项标为已完成。

---

## 复现命令（本仓库根）

```bat
set PYTHONPATH=src
py -3 scripts\mnemosyne_readiness_suite.py
py -3 -m pytest tests -q
```

人工试点（不代签）：[reports/HUMAN_SIGNOFF_CHECKLIST.md](reports/HUMAN_SIGNOFF_CHECKLIST.md) · [reports/e6.5-pilot-status.md](reports/e6.5-pilot-status.md)
