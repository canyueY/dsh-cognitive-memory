# -*- coding: utf-8 -*-
"""E1.2 备份恢复演练：独立 data_dir → 写入 → backup → 另一目录 restore → 校验。

用法（仓库根）：
  py -3 scripts/mnemosyne_backup_restore_drill.py
  py -3 scripts/mnemosyne_backup_restore_drill.py --keep
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CM_SRC = ROOT / "src"


def main() -> int:
    parser = argparse.ArgumentParser(description="Mnemosyne backup/restore drill")
    parser.add_argument("--keep", action="store_true", help="保留临时目录")
    parser.add_argument("--report", default="", help="写出 JSON 报告路径")
    parser.add_argument(
        "--archive",
        action="store_true",
        help="额外把报告写入 docs/reports/e1.2-backup-restore-drill.json",
    )
    args = parser.parse_args()

    if not (CM_SRC / "cognitive_memory").is_dir():
        print("cognitive_memory package not found under ./src", file=sys.stderr)
        return 2

    sys.path.insert(0, str(CM_SRC))

    from cognitive_memory.bootstrap import build_context
    from cognitive_memory.cli import cmd_backup, cmd_restore
    from cognitive_memory.domain.models import (
        MemoryProposeIn,
        MemoryStatus,
        MemoryType,
        ObservationIn,
        SourceKind,
    )

    base = Path(tempfile.mkdtemp(prefix="mnemosyne-drill-"))
    src_dir = base / "source"
    rst_dir = base / "restored"
    bak_dir = base / "backups"
    src_dir.mkdir()
    rst_dir.mkdir()
    bak_dir.mkdir()

    report: dict = {
        "ok": False,
        "base": str(base),
        "steps": [],
    }

    try:
        ctx = build_context(data_dir=str(src_dir), token="drill-token")
        try:
            obs = ctx.service.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.SYSTEM,
                    content="drill-observation: user prefers quiet rain sounds",
                    producer="backup-restore-drill",
                    idempotency_key="drill:obs:1",
                )
            )
            mem = ctx.service.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.SEMANTIC,
                    status=MemoryStatus.CANDIDATE,
                    content="drill-memory: prefers quiet rain sounds",
                    source_ids=[obs.id],
                    metadata={"drill": True},
                    idempotency_key="drill:mem:1",
                )
            )
            health_before = ctx.service.health()
        finally:
            ctx.db.close()

        report["steps"].append(
            {
                "write": True,
                "observation_id": obs.id,
                "memory_id": mem.id,
                "health": health_before,
            }
        )

        class NS:
            pass

        bak_args = NS()
        bak_args.data_dir = str(src_dir)
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

        rst_args = NS()
        rst_args.backup = str(backup_db)
        rst_args.data_dir = str(rst_dir)
        rst_args.force = True
        rc = cmd_restore(rst_args)
        if rc != 0:
            report["error"] = "restore_failed"
            return 1

        ctx2 = build_context(data_dir=str(rst_dir), token="drill-token")
        try:
            health_after = ctx2.service.health()
            got = ctx2.service.get_memory(mem.id)
            if hasattr(got, "content"):
                text = got.content or ""
            elif isinstance(got, dict):
                text = str(got.get("content") or "")
            else:
                text = str(got or "")
            content_ok = "quiet rain" in text
        finally:
            ctx2.db.close()

        # 重复恢复
        rc = cmd_restore(rst_args)
        repeat_ok = rc == 0

        # 损坏备份：截断文件后 restore 应失败或打开库失败
        corrupt_path = bak_dir / "memory-corrupt.db"
        raw = backup_db.read_bytes()
        corrupt_path.write_bytes(raw[: max(64, len(raw) // 10)])
        corrupt_dir = base / "corrupt-restore"
        corrupt_dir.mkdir()
        cor_args = NS()
        cor_args.backup = str(corrupt_path)
        cor_args.data_dir = str(corrupt_dir)
        cor_args.force = True
        corrupt_restore_rc = cmd_restore(cor_args)
        corrupt_detected = False
        if corrupt_restore_rc != 0:
            corrupt_detected = True
        else:
            try:
                ctx3 = build_context(data_dir=str(corrupt_dir), token="drill-token")
                try:
                    ctx3.service.health()
                    # 若仍能打开，尝试读原 memory 应失败或不完整
                    try:
                        ctx3.service.get_memory(mem.id)
                        corrupt_detected = False
                    except Exception:
                        corrupt_detected = True
                finally:
                    ctx3.db.close()
            except Exception:
                corrupt_detected = True

        report["steps"].append(
            {
                "backup": str(backup_db),
                "restore_dir": str(rst_dir),
                "health_after": health_after,
                "content_ok": content_ok,
                "repeat_restore_ok": repeat_ok,
                "corrupt_detected": corrupt_detected,
                "corrupt_restore_rc": corrupt_restore_rc,
            }
        )
        report["ok"] = bool(content_ok and repeat_ok and corrupt_detected)
        report["pass_criteria"] = {
            "independent_dirs": str(src_dir) != str(rst_dir),
            "content_ok": content_ok,
            "repeat_restore_ok": repeat_ok,
            "corrupt_detected": corrupt_detected,
        }
        return 0 if report["ok"] else 1
    finally:
        out = Path(args.report) if args.report else base / "drill-report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.archive:
            arch = ROOT / "docs" / "reports" / "e1.2-backup-restore-drill.json"
            arch.parent.mkdir(parents=True, exist_ok=True)
            arch.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            report["archive_path"] = str(arch)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.keep:
            shutil.rmtree(base, ignore_errors=True)
        else:
            print(f"kept={base}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
