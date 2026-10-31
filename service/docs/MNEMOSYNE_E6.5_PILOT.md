# E6.5 正式小规模 Adoption 试点手册

**状态：** Runbook Ready（2026-10-30）  
**试点看板：** [docs/reports/e6.5-pilot-status.md](reports/e6.5-pilot-status.md)（当前 `READY`；人工签字后才可 `IN_PROGRESS`）  
**范围：** **小规模**试点（非全量用户收纳）  
**上位：** [ADOPTION](MNEMOSYNE_ADOPTION.md) · [READINESS](MNEMOSYNE_2.0_READINESS.md) · V8 签字脚本

---

## 1. 准入门槛（全部满足才开试点）

| # | 条件 | 证据 |
| --- | --- | --- |
| 1 | G1–G3 / G6 最小面绿 | `mnemosyne_readiness_suite.py` |
| 2 | 合成库备份演练绿 | `docs/reports/e1.2-backup-restore-drill.json` |
| 3 | **现网 V8 签字** | `docs/reports/v8-production-backup-signoff.json` + 人工表 |
| 4 | Admin Adoption UI 可用 | 管理后台 →「Mnemosyne Adoption」 |
| 5 | Staging 未批准不可 Commit | 单元 / 手册勾选 |
| 6 | Cutover 无 confirm 拒绝；dual 默关 | API / UI |

未满足第 3 项：**禁止**对现网执行 Cutover。

---

## 2. 试点规模（建议）

- 用户数：1–3 台现网桌宠 / 独立 Node data_dir  
- 窗口：≤ 7 天观察期  
- 回滚：保留 V8 备份；Authority 可退回 `importing` / 外部权威（按 cutover 合法边）  
- **不做：** 市场组件、跨 Node 联邦、全量默认切换

---

## 3. 执行步骤

### 3.1 现网备份 V8

```bat
py -3 scripts\mnemosyne_production_backup_signoff.py --i-understand-production --confirm-data-dir "%LOCALAPPDATA%\DSH\cognitive-memory" --archive
```

- 恢复只写入临时目录，**永不覆盖现网**  
- 通过后归档 JSON + 填写同目录 `.md` 签字表  
- 夹具自检（不可代替现网）：`--fixture-demo --archive`

### 3.2 Admin 预览

1. 启动管理后台（`scripts/log_viewer.py`）  
2. 打开 **记忆与知识库 → Mnemosyne Adoption**  
3. 「刷新状态 / Cutover 预览」核对 Authority、清单、建议路径  
4. （可选）导出 Interchange JSONL

### 3.3 Cutover（仍须确认）

- UI：勾选确认 → 执行；或 CLI：

```bat
set PYTHONPATH=services\cognitive-memory\src
set DSH_MEMORY_DATA_DIR=%LOCALAPPDATA%\DSH\cognitive-memory
py -3 -m cognitive_memory.node_cli authority cutover-preview
py -3 -m cognitive_memory.node_cli authority cutover --target mnemosyne_primary --confirm --reason "e6.5-pilot"
```

### 3.4 试点验收勾选

| 项 | Pass |
| --- | --- |
| V8 报告 ok + 人工签字 | ☐ |
| Cutover 后 health 正常 | ☐ |
| 抽样检索 / 对话注入无回归 | ☐ |
| dual_sync 未误开 | ☐ |
| 回滚演练（至少文档级） | ☐ |

---

## 4. 退出与升级

- **失败退出：** 停止扩大试点；保留备份；记录 `docs/reports/`  
- **成功但不等于全量：** 更新 READINESS Gate H 为「小规模试点通过」；全量另开里程碑  
- **禁止**将 E6.5 标成「全体用户已收纳」

---

## 5. 相关 API（Admin 代理）

| 方法 | 路径 |
| --- | --- |
| GET | `/api/adoption/status` |
| GET | `/api/adoption/cutover/preview` |
| POST | `/api/adoption/cutover/execute` |
| POST | `/api/adoption/export` |
