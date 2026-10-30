# V8 现网备份恢复签字单（模板）

> 正式文件由脚本生成：`scripts/mnemosyne_production_backup_signoff.py --i-understand-production --confirm-data-dir <绝对路径> --archive`  
> 生成后请改名/覆盖为同目录 `v8-production-backup-signoff.md`（与 `.json` 成对）。  
> `*.pending.json` / `mode=controlled-fixture` **不能**当作本表已签。

- 生成时间（UTC）：`_脚本填写_`
- 模式：必须为 `production`
- data_dir：`_现网绝对路径_`
- 脚本判定 ok：必须为 `true`

## 人工签字（必填）

| 项 | 填写 |
| --- | --- |
| 操作人 | _待填_ |
| 复核人 | _待填_ |
| 日期 |  |
| 现网实例说明（机器/用户） |  |
| 是否确认未覆盖现网 DB | 是 / 否 |
| 是否批准作为 E6.5 准入 | 是 / 否 |
| 备注 |  |

### 签字完成判定

- [ ] 自动检查全部 true
- [ ] 操作人已签
- [ ] 复核人已签
- [ ] 已更新 [e6.5-pilot-status.md](e6.5-pilot-status.md)
