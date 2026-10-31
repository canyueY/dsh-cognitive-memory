# Mnemosyne 2.0 GA 状态收口（2026-10-31）

> **权威仓：** [`canyueY/dsh-mnemosyne`](https://github.com/canyueY/dsh-mnemosyne) · **基线：** [REPO_BASELINE](REPO_BASELINE.md) · **黄项：** [YELLOW_BACKLOG](YELLOW_BACKLOG.md)
> **旧 0.2 插件：** `legacy/dsh-plugin/`（非标尺）

---

## 一句话结论

**2.0 统一版继承的旧版最小面已基本落地**（Node CLI / Identity / Bank / Authority·Cutover / Agent grants / Staging / 本地 D8 / SDK·policy / standalone E2E）。
**不应**再说「D2–D8 基本未开始 / 只是 V1.5」。
剩余是 **黄区加厚与人工签字**，不是从零重做绿项。

---

## Gate 快照

| Gate | 判定 | 说明 |
| --- | --- | --- |
| G1 | 可绿 | Node 独立 doctor/health |
| G2 | 可绿 | 现网 V8 production 双签完成（Y3）；E6.5 `IN_PROGRESS` |
| G3 | 可绿 | 认知核 + Y4 情绪/反馈/Bank 抽样 E2E |
| G4 | 黄偏绿 | `/api/v1` + SDK + SSE；裸 `/v1` 不做（Y7 关闭） |
| G5 | 黄 | 本地组件面；市场裁切；禁直连 sqlite 契约（Y5 可选加厚） |
| G6 | 可绿 | grants + policy 执法 |
| G7 | 黄 | Staging/Cutover 最小面；**全量 Adoption = Y6 另开** |
| G8 | 增强 | Compat + 权威仓叙事（Y1） |
| G9 | 增强 | Matrix / READINESS / 本文件（Y2） |
| G10 | 裁切 | 联邦 → **2.1+** |

---

## Adoption 边界（写死）

| 层级 | 含义 | 状态 |
| --- | --- | --- |
| E6.5 | **小规模**试点 Runbook + 看板 | 技术 READY；**人工签字后**才 IN_PROGRESS |
| 全量 Adoption | 全体用户默认收纳 | **≠ E6.5**；Y6 / 另开里程碑 |
| GA 最小面声明 | 本文件 + READINESS | 可对外说「最小面就绪」；不可说「全量已收纳」 |

---

## 后续只做

1. **Y3** — **完成**（现网 V8 + 看板 `IN_PROGRESS`）
2. **Y4** — **完成**（契约 E2E）；试点期内可再抽样
3. **Y6** — 全量 Adoption（另里程碑）；观察期结束后再评估 E6.5 → PASSED
4. **旧 0.2 插件** — 归档在 `legacy/dsh-plugin/`；2.0 统一版由根目录适配层启动 `service/`

## 明确禁止重做

Identity / Memory Bank / Node CLI / Agent grants / 本地 Component / Staging·Cutover 最小面 / Python+TS SDK 从零 Epic。
