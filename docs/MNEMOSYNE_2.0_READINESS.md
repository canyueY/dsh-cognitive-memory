# Mnemosyne 2.0 Readiness Gate（证据账本）

**状态：** Partial Evidence（2026-10-30）— 可跑套件；**不等于**正式收纳全体用户  
**套件：** `scripts/mnemosyne_readiness_suite.py` → `tmp/mnemosyne_readiness_report.json`  
**上位：** [IMPLEMENTATION_PLAN §8](MNEMOSYNE_2.0_IMPLEMENTATION_PLAN.md) · [CAPABILITY_MATRIX](MNEMOSYNE_2.0_CAPABILITY_MATRIX.md)

---

## Gate 对照

| Gate | 必要性 | 现状 | 证据 |
| --- | --- | --- | --- |
| G1 Node Independence | 必须 | ✅ | `mnemosyne doctor/health`；套件 health |
| G2 Storage Safety | 必须 | ✅ 证据 | 合成库 `e1.2-…json`；现网 V8 `docs/reports/v8-production-backup-signoff.json`（57k memories 备份恢复一致；未覆盖现网） |
| G3 Cognitive Core | 必须 | ✅ | Observation→Memory；黄金样本；套件 G3 |
| G4 Interoperability | 必须 | Partial→增强 | Python+TS SDK；CRUD Agent 执法；SSE；standalone + DSH 薄化 E2E；[API_SPEC](MNEMOSYNE_API_SPEC.md) |
| G5 Component Management | 必须 | Partial | 本地 Component Manager；无市场（裁切） |
| G6 Governance | 必须 | ✅ 增强 | grants + CRUD + policy(store/forward/train/retention)；硬删闸；MCP 写确认 |
| G7 Migration | 必须 | Partial→增强 | Staging(dedupe+分层回滚)+Cutover；Admin Adoption；export 受 allow_forward |
| G8 Compatibility | 必须 | Partial | Compat Gateway；宿主 A-MEM/Mem0 仍并行 |
| G9 Documentation | 必须 | Partial→增强 | + API_SPEC / Matrix 刷账 / E6.5 pilot-status；全量仍另开 |
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

## 复现命令

```bash
set PYTHONPATH=services/cognitive-memory/src
py -3 scripts/mnemosyne_readiness_suite.py
py -3 -m pytest services/cognitive-memory/tests/unit/test_agent_grants.py -q
```
