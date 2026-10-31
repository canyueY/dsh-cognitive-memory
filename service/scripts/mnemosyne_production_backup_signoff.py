# -*- coding: utf-8 -*-
"""V8 现网备份签字：对真实 data_dir 做备份 → 独立目录恢复校验（永不覆盖现网）。

安全闸：
  必须同时提供 --i-understand-production 与 --confirm-data-dir <绝对路径>
  --confirm-data-dir 必须与解析后的现网 data_dir 完全一致
  默认禁止向现网 data_dir 执行 restore（无开关可关此保护）

用法（仓库根）：
  py -3 scripts/mnemosyne_production_backup_signoff.py --i-understand-production ^
      --confirm-data-dir "%LOCALAPPDATA%\\DSH\\cognitive-memory"
  py -3 scripts/mnemosyne_production_backup_signoff.py --i-understand-production ^
      --confirm-data-dir <path> --archive
  # CI / 受控夹具（标记 mode=controlled-fixture，不可冒充现网签字）：
  py -3 scripts/mnemosyne_production_backup_signoff.py --fixture-demo --archive
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CM_SRC = ROOT / "src"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_data_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    sys.path.insert(0, str(CM_SRC))
    from cognitive_memory.storage.paths import default_data_root

    return default_data_root().resolve()


def _ensure_cm() -> None:
    if not (CM_SRC / "cognitive_memory").is_dir():
        raise SystemExit("cognitive_memory package not found under ./src")
    if str(CM_SRC) not in sys.path:
        sys.path.insert(0, str(CM_SRC))


def _write_signoff_md(path: Path, report: dict) -> None:
    lines = [
        "# V8 现网备份恢复签字单",
        "",
        f"- 生成时间（UTC）：`{report.get('generated_at')}`",
        f"- 模式：`{report.get('mode')}`",
        f"- data_dir：`{report.get('data_dir')}`",
        f"- 备份文件：`{(report.get('backup') or {}).get('path', '')}`",
        f"- 恢复校验目录：`{report.get('restore_dir')}`",
        f"- 脚本判定 ok：`{report.get('ok')}`",
        "",
        "## 自动检查",
        "",
        "```json",
        json.dumps(report.get("pass_criteria") or {}, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 人工签字（必填）",
        "",
        "| 项 | 填写 |",
        "| --- | --- |",
        "| 操作人 | _待填_ |",
        "| 复核人 | _待填_ |",
        "| 日期 |  |",
        "| 现网实例说明（机器/用户） |  |",
        "| 是否确认未覆盖现网 DB | 是 / 否 |",
        "| 是否批准作为 E6.5 准入 | 是 / 否 |",
        "| 备注 |  |",
        "",
        "### 签字完成判定",
        "",
        "- [ ] 自动检查全部 true",
        "- [ ] 操作人已签",
        "- [ ] 复核人已签",
        "- [ ] 已更新 `docs/reports/e6.5-pilot-status.md`（READY→IN_PROGRESS 或 DEFERRED）",
        "",
        "> `mode=controlled-fixture` 仅证明脚本可用，**不能**代替现网签字。",
        "> `mode=production` 且 `ok=true`：技术准入；**人工两栏未填前不得**开 E6.5 `IN_PROGRESS`。",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _run_signoff(data_dir: Path, *, mode: str, keep: bool, report_path: Path | None, archive: bool) -> int:
    _ensure_cm()
    from cognitive_memory.bootstrap import build_context
    from cognitive_memory.cli import cmd_backup, cmd_restore
    from cognitive_memory.storage.paths import ensure_layout

    paths = ensure_layout(data_dir)
    db = paths["db"]
    report: dict = {
        "ok": False,
        "gate": "V8",
        "mode": mode,
        "generated_at": _utc(),
        "data_dir": str(data_dir),
        "db_path": str(db),
        "db_present": db.is_file(),
        "db_bytes": db.stat().st_size if db.is_file() else 0,
        "steps": [],
        "note": "restore 仅写入临时目录；永不覆盖现网 data_dir",
    }

    if not db.is_file():
        report["error"] = "production_db_missing"
        report["detail"] = f"no memory.db at {db}"
        _finalize(report, report_path, archive, keep, None)
        return 2

    base = Path(tempfile.mkdtemp(prefix="mnemosyne-v8-"))
    bak_dir = base / "backups"
    rst_dir = base / "restored"
    bak_dir.mkdir()
    rst_dir.mkdir()
    report["work_dir"] = str(base)
    report["restore_dir"] = str(rst_dir)

    try:
        # health before
        ctx = build_context(data_dir=str(data_dir), token="v8-signoff")
        try:
            health_before = ctx.service.health()
        finally:
            ctx.db.close()
        report["steps"].append({"health_before": health_before})

        class NS:
            pass

        bak_args = NS()
        bak_args.data_dir = str(data_dir)
        bak_args.output = str(bak_dir)
        rc = cmd_backup(bak_args)
        if rc != 0:
            report["error"] = "backup_failed"
            return 1

        backups = sorted(bak_dir.glob("memory-*.db"))
        if not backups:
            report["error"] = "no_backup_file"
            return 1
        backup_db = backups[-1]
        report["backup"] = {
            "path": str(backup_db),
            "bytes": backup_db.stat().st_size,
        }

        # safety: restore target must not equal production
        if rst_dir.resolve() == data_dir.resolve():
            report["error"] = "refuse_restore_onto_production"
            return 1

        rst_args = NS()
        rst_args.backup = str(backup_db)
        rst_args.data_dir = str(rst_dir)
        rst_args.force = True
        rc = cmd_restore(rst_args)
        if rc != 0:
            report["error"] = "restore_failed"
            return 1

        ctx2 = build_context(data_dir=str(rst_dir), token="v8-signoff")
        try:
            health_after = ctx2.service.health()
        finally:
            ctx2.db.close()

        # corrupt detection
        corrupt_path = bak_dir / "memory-corrupt.db"
        raw = backup_db.read_bytes()
        corrupt_path.write_bytes(raw[: max(64, len(raw) // 10)])
        corrupt_dir = base / "corrupt-restore"
        corrupt_dir.mkdir()
        cor_args = NS()
        cor_args.backup = str(corrupt_path)
        cor_args.data_dir = str(corrupt_dir)
        cor_args.force = True
        corrupt_rc = cmd_restore(cor_args)
        corrupt_detected = corrupt_rc != 0
        if not corrupt_detected:
            try:
                ctx3 = build_context(data_dir=str(corrupt_dir), token="v8-signoff")
                try:
                    ctx3.service.health()
                finally:
                    ctx3.db.close()
                # opened truncated db — still flag as weak detection
                corrupt_detected = False
            except Exception:
                corrupt_detected = True

        memories_match = int(health_before.get("memories") or 0) == int(
            health_after.get("memories") or 0
        )
        obs_match = int(health_before.get("observations") or 0) == int(
            health_after.get("observations") or 0
        )
        never_overwrote = str(data_dir.resolve()) != str(rst_dir.resolve())

        report["steps"].append(
            {
                "health_after": health_after,
                "corrupt_restore_rc": corrupt_rc,
                "corrupt_detected": corrupt_detected,
            }
        )
        report["pass_criteria"] = {
            "db_present": True,
            "backup_ok": True,
            "restore_ok": True,
            "memories_match": memories_match,
            "observations_match": obs_match,
            "corrupt_detected": corrupt_detected,
            "never_overwrote_production": never_overwrote,
        }
        report["ok"] = all(report["pass_criteria"].values())
        return 0 if report["ok"] else 1
    finally:
        _finalize(report, report_path, archive, keep, base)


def _finalize(
    report: dict,
    report_path: Path | None,
    archive: bool,
    keep: bool,
    base: Path | None,
) -> None:
    out = report_path or (ROOT / "tmp" / "v8-production-backup-signoff.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(out)

    md = out.with_suffix(".md")
    _write_signoff_md(md, report)
    report["signoff_md"] = str(md)

    if archive:
        arch = ROOT / "docs" / "reports" / "v8-production-backup-signoff.json"
        if report.get("mode") == "production" and report.get("ok"):
            arch.parent.mkdir(parents=True, exist_ok=True)
            arch.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            (arch.with_suffix(".md")).write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
            report["archive_path"] = str(arch)
        else:
            pending = ROOT / "docs" / "reports" / "v8-production-backup-signoff.pending.json"
            pending.parent.mkdir(parents=True, exist_ok=True)
            pending.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            report["pending_archive_path"] = str(pending)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if base is not None and not keep:
        shutil.rmtree(base, ignore_errors=True)
    elif base is not None:
        print(f"kept={base}", file=sys.stderr)


def _seed_fixture(base: Path) -> Path:
    _ensure_cm()
    from cognitive_memory.bootstrap import build_context
    from cognitive_memory.domain.models import (
        MemoryProposeIn,
        MemoryStatus,
        MemoryType,
        ObservationIn,
        SourceKind,
    )

    data_dir = base / "prod-like"
    data_dir.mkdir(parents=True, exist_ok=True)
    ctx = build_context(data_dir=str(data_dir), token="v8-fixture")
    try:
        obs = ctx.service.capture_observation(
            ObservationIn(
                source_kind=SourceKind.SYSTEM,
                content="v8-fixture observation",
                producer="v8-fixture",
                idempotency_key="v8:obs:1",
            )
        )
        ctx.service.propose_memory(
            MemoryProposeIn(
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.CANDIDATE,
                content="v8-fixture memory",
                source_ids=[obs.id],
                metadata={"v8_fixture": True},
                idempotency_key="v8:mem:1",
            )
        )
    finally:
        ctx.db.close()
    return data_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="V8 production backup sign-off")
    parser.add_argument("--i-understand-production", action="store_true")
    parser.add_argument(
        "--confirm-data-dir",
        default="",
        help="必须与现网 data_dir 绝对路径一致",
    )
    parser.add_argument("--data-dir", default="", help="覆盖默认现网根（仍须 confirm）")
    parser.add_argument(
        "--fixture-demo",
        action="store_true",
        help="受控夹具演练（mode=controlled-fixture，不可作现网签字）",
    )
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--report", default="")
    parser.add_argument("--archive", action="store_true")
    args = parser.parse_args()

    report_path = Path(args.report) if args.report else None

    if args.fixture_demo:
        base = Path(tempfile.mkdtemp(prefix="mnemosyne-v8-fix-"))
        try:
            data_dir = _seed_fixture(base)
            return _run_signoff(
                data_dir,
                mode="controlled-fixture",
                keep=args.keep,
                report_path=report_path,
                archive=args.archive,
            )
        finally:
            if not args.keep:
                shutil.rmtree(base, ignore_errors=True)

    if not args.i_understand_production:
        print(
            "refused: pass --i-understand-production (and --confirm-data-dir)",
            file=sys.stderr,
        )
        return 2
    if not args.confirm_data_dir.strip():
        print("refused: --confirm-data-dir required", file=sys.stderr)
        return 2

    data_dir = _resolve_data_dir(args.data_dir or None)
    confirm = Path(args.confirm_data_dir).expanduser().resolve()
    if confirm != data_dir:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "confirm_mismatch",
                    "data_dir": str(data_dir),
                    "confirm_data_dir": str(confirm),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    # expand env-style confirm for Windows convenience already handled by Path
    _ = os.environ  # keep import used for docs parity
    return _run_signoff(
        data_dir,
        mode="production",
        keep=args.keep,
        report_path=report_path,
        archive=args.archive,
    )


if __name__ == "__main__":
    raise SystemExit(main())
