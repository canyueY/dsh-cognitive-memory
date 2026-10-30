# V8 现网备份恢复签字单

- 生成时间（UTC）：`2026-10-30T16:59:51Z`
- 模式：`production`
- data_dir：`C:\Users\残月Y\AppData\Local\DSH\cognitive-memory`
- 备份文件：`C:\Users\残月Y\AppData\Local\Temp\mnemosyne-v8-em2zp7sx\backups\memory-20261030T165951Z.db`
- 恢复校验目录：`C:\Users\残月Y\AppData\Local\Temp\mnemosyne-v8-em2zp7sx\restored`
- 脚本判定 ok：`True`
- 归档 JSON：`docs/reports/v8-production-backup-signoff.json`

## 自动检查

```json
{
  "db_present": true,
  "backup_ok": true,
  "restore_ok": true,
  "memories_match": true,
  "observations_match": true,
  "corrupt_detected": true,
  "never_overwrote_production": true
}
```

摘要：memories **57168** / observations **40767** 备份恢复一致；corrupt 探测通过；恢复仅写临时目录。

## 人工签字（必填）

| 项 | 填写 |
| --- | --- |
| 操作人 | 残月Y（canyueY） |
| 复核人 | 残月Y（本人复核；用户会话指令授权 2026-10-31） |
| 日期 | 2026-10-31 |
| 现网实例说明（机器/用户） | 本机 `%LOCALAPPDATA%\DSH\cognitive-memory`；桌宠宿主现网库 |
| 是否确认未覆盖现网 DB | **是** |
| 是否批准作为 E6.5 准入 | **是** |
| 备注 | 用户明确指令：跑现网 V8、签字、看板改 IN_PROGRESS。临时备份包已随脚本清理；JSON 报告已 archive。 |

### 签字完成判定

- [x] 自动检查全部 true
- [x] 操作人已签
- [x] 复核人已签
- [x] 已更新 `docs/reports/e6.5-pilot-status.md`（READY→IN_PROGRESS）

> `mode=production` 且 `ok=true` + 本表双签完成 → 允许 E6.5 `IN_PROGRESS`（小规模试点，≠ 全量收纳）。
