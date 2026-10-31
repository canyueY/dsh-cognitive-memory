# Mnemosyne Adoption Runbook（收纳手册 · 最小面）

**状态：** Implemented-lite + Admin UI（2026-10-30）  
**上位：** [READINESS](MNEMOSYNE_2.0_READINESS.md) · [INTERCHANGE_SPEC](MNEMOSYNE_INTERCHANGE_SPEC.md) · [E6.5 试点](MNEMOSYNE_E6.5_PILOT.md)  
**警告：** 跑通本手册 ≠ 可正式收纳全体用户（全量仍须单独里程碑；E6.5 仅为小规模试点）。

---

## 1. 原则

1. **迁移成功 ≠ 认知验证通过**  
2. **Staging 未批准不得 Commit**  
3. **Authority 禁止默认双权威**（`dual_sync` 须 `allow_dual`）  
4. **切权威前必须备份**  
5. 登记 Agent / 安装组件 **≠** 已授权读写

---

## 2. 推荐流程

```
Connect / Discover
  → Import Preview（Staging）
  → User Approval
  → Import Commit
  → Validation（health / 抽样检索）
  → Cutover Preview
  → Cutover Execute（confirm）
  → Adoption Complete（mnemosyne_primary）
```

### 2.1 Staging

- 代码：`migration/staging.py`  
- 未 `approve` 时 `commit_batch` 抛 `PermissionError`  
- `preview_batch(..., dedupe=True)`：source/content 去重  
- `rollback_batch(..., layer="soft"|"hard")`：仅 `committed` 可回滚

### 2.2 Cutover

```bash
set PYTHONPATH=services/cognitive-memory/src
set DSH_MEMORY_DATA_DIR=<独立目录>
py -3 -m cognitive_memory.node_cli authority cutover-preview
py -3 -m cognitive_memory.node_cli authority cutover --target mnemosyne_primary --confirm --reason "pilot"
```

REST：

- `GET /api/v1/authority/cutover/preview`
- `POST /api/v1/authority/cutover/execute` `{"confirm":true,"target":"mnemosyne_primary"}`

典型路径：`external_authoritative → importing → mnemosyne_primary`

### 2.3 导出（可选范围）

```bash
py -3 -m cognitive_memory.node_cli adopt export -o export.jsonl --banks personal,shared
# 或 POST /api/v1/adoption/export
```

### 2.4 备份演练（G2）

```bash
py -3 scripts/mnemosyne_backup_restore_drill.py --archive
```

报告：`docs/reports/e1.2-backup-restore-drill.json`（合成 data_dir）

### 2.5 现网备份 V8（切权威前必做）

```bash
py -3 scripts/mnemosyne_production_backup_signoff.py --i-understand-production --confirm-data-dir "%LOCALAPPDATA%/DSH/cognitive-memory" --archive
```

- 恢复仅写入临时目录，**永不覆盖现网**  
- 归档：`docs/reports/v8-production-backup-signoff.json` + 签字 Markdown  
- 夹具自检：`--fixture-demo`（不可冒充现网签字）

### 2.6 Admin Adoption UI

管理后台 → **记忆与知识库 → Mnemosyne Adoption**

- `GET /api/adoption/status`  
- `GET /api/adoption/cutover/preview`  
- `POST /api/adoption/cutover/execute`（须 confirm）  
- `POST /api/adoption/export`

---

## 3. 验收勾选（试点）

| 项 | 标准 |
| --- | --- |
| 备份可恢复 | drill ok；含损坏检测 |
| 现网 V8 | 签字报告 ok + 人工表 |
| Staging | 未批准无法 Commit |
| Cutover | 无 confirm 拒绝；dual 默关；Admin 可预览 |
| 导出 | Interchange JSONL 可读 |
| 多 Agent | Bank 隔离 + 可撤销 |

**小规模试点**按 [E6.5](MNEMOSYNE_E6.5_PILOT.md)。**正式全量收纳**须另开里程碑并更新 [READINESS](MNEMOSYNE_2.0_READINESS.md) Gate H。


### 2.7 执法与运维（补强）

- Memory CRUD：Node Bearer **或** `X-Agent-Id`/`X-Agent-Token`（grant 范围）
- 硬删：`confirm=true` + 能力 `MEMORY_HARD_DELETE`
- 备份包：`mnemosyne backup` → 目录含 db+config；运行中 restore 默认拒绝
- 干净安装：`scripts/mnemosyne_clean_install_e62.py`
