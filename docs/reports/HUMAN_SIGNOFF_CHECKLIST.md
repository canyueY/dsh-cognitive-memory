# Y3 人工签字清单（不代签）

本页只组织**人**要做的事。脚本与 fixture **不能**代替现网双签。

**权威仓：** [`canyueY/mnemosyne`](https://github.com/canyueY/mnemosyne)  
**关联：** [YELLOW_BACKLOG Y3](../YELLOW_BACKLOG.md) · [E6.5 试点](../MNEMOSYNE_E6.5_PILOT.md) · [试点看板](e6.5-pilot-status.md)

---

## A. 现网 V8（Gate G2 / 备份安全）

在**真实** data_dir 上执行（示例路径按本机改）：

```bat
cd /d D:\path\to\mnemosyne
set PYTHONPATH=src
py -3 scripts\mnemosyne_production_backup_signoff.py --i-understand-production --confirm-data-dir "%LOCALAPPDATA%\DSH\cognitive-memory" --archive
```

验收：

1. 生成 `docs/reports/v8-production-backup-signoff.json`（`mode=production`，`ok=true`）。
2. 打开同目录 `.md`，填写 **操作人 / 复核人 / 日期 / 未覆盖现网**。
3. `controlled-fixture` / `*.pending.json` **不算**完成 Y3。

自检（不可代替现网）：

```bat
py -3 scripts\mnemosyne_production_backup_signoff.py --fixture-demo --archive
```

---

## B. E6.5 试点看板（Gate H / 小规模 Adoption）

1. 确认 A 已人工双签。
2. 打开 [e6.5-pilot-status.md](e6.5-pilot-status.md)，填人工栏。
3. 仅当批准时把状态 `READY` → `IN_PROGRESS`。
4. **不要**把 E6.5 写成「全量用户已收纳」（那是 Y6，另开里程碑）。

---

## C. 完成后更新

| 文件 | 动作 |
| --- | --- |
| `docs/YELLOW_BACKLOG.md` | Y3 → **完成**（注明日期与签字人） |
| `docs/MNEMOSYNE_2.0_READINESS.md` | G2 / Adoption 备注改为「现网已双签」 |
| `docs/reports/e6.5-pilot-status.md` | 状态机前进 |

---

## 明确不做

- AI / CI **代填**操作人、复核人姓名  
- 用 fixture 报告冒充 production 签字  
- 未签 V8 就对现网 Cutover  
