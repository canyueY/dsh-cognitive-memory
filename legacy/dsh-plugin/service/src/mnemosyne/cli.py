# -*- coding: utf-8 -*-
"""运维 CLI：备份 / 恢复 / 迁移 / 健康检查。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def cmd_backup(args: argparse.Namespace) -> int:
    from mnemosyne.storage.paths import ensure_layout

    paths = ensure_layout(Path(args.data_dir).resolve() if args.data_dir else None)
    db = paths["db"]
    if not db.is_file():
        print(f"no db at {db}", file=sys.stderr)
        return 1
    out_dir = Path(args.output or (paths["root"] / "backups")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"memory-{_now_stamp()}.db"
    # 用 SQLite backup API 更安全
    import sqlite3

    src = sqlite3.connect(db)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    meta = {
        "created_at": _now_stamp(),
        "source": str(db),
        "backup": str(dest),
        "bytes": dest.stat().st_size,
    }
    meta_path = dest.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    from mnemosyne.storage.paths import ensure_layout

    src = Path(args.backup).resolve()
    if not src.is_file():
        print(f"backup not found: {src}", file=sys.stderr)
        return 1
    paths = ensure_layout(Path(args.data_dir).resolve() if args.data_dir else None)
    db = paths["db"]
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.is_file() and not args.force:
        bak = db.with_suffix(f".pre-restore-{_now_stamp()}.db")
        shutil.copy2(db, bak)
        print(f"existing db copied to {bak}")
    shutil.copy2(src, db)
    print(json.dumps({"ok": True, "restored_to": str(db), "from": str(src)}, ensure_ascii=False))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    from mnemosyne.bootstrap import build_context

    ctx = build_context(data_dir=args.data_dir or None, token=args.token or "cli-health")
    print(json.dumps(ctx.service.health(), ensure_ascii=False, indent=2))
    ctx.db.close()
    return 0


def cmd_migrate_amem(args: argparse.Namespace) -> int:
    """从 A-MEM / JSONL 导入为 observations + candidate memories。"""
    from mnemosyne.bootstrap import build_context
    from mnemosyne.domain.models import (
        MemoryProposeIn,
        MemoryStatus,
        MemoryType,
        ObservationIn,
        SourceKind,
    )

    notes: list[dict] = []
    if args.jsonl:
        path = Path(args.jsonl)
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            notes.append(json.loads(line))
    else:
        # 尝试经桌宠桥接读引擎（可选）
        try:
            root = Path(args.project_root or Path.cwd()).resolve()
            sys.path.insert(0, str(root))
            from Murasame.a_mem_bridge import get_a_mem_engine  # type: ignore
            from Murasame.utils import get_config  # type: ignore

            engine = get_a_mem_engine(get_config())
            if engine is None:
                print("A-MEM engine unavailable; pass --jsonl export", file=sys.stderr)
                return 2
            for mid, note in (engine.memories or {}).items():
                content = getattr(note, "content", None) or (note.get("content") if isinstance(note, dict) else "")
                tags = getattr(note, "tags", None) or (note.get("tags") if isinstance(note, dict) else [])
                notes.append({"id": str(mid), "content": str(content or ""), "tags": tags or []})
        except Exception as exc:
            print(f"cannot load A-MEM: {exc}", file=sys.stderr)
            return 2

    ctx = build_context(data_dir=args.data_dir or None, token=args.token or "cli-migrate")
    imported = 0
    skipped = 0
    for note in notes:
        content = str(note.get("content") or "").strip()
        if len(content) < 2:
            skipped += 1
            continue
        if args.dry_run:
            imported += 1
            continue
        obs = ctx.service.capture_observation(
            ObservationIn(
                source_kind=SourceKind.SYSTEM,
                content=content[:4000],
                producer="migrate.amem",
                metadata={"amem_id": note.get("id"), "tags": note.get("tags") or []},
                idempotency_key=f"amem:{note.get('id') or format(hash(content) & 0xFFFFFFFF, 'x')}",
            )
        )
        ctx.service.propose_memory(
            MemoryProposeIn(
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.CANDIDATE,
                content=content[:2000],
                source_ids=[obs.id],
                metadata={"migrated_from": "a_mem", "tags": note.get("tags") or []},
                idempotency_key=f"amem-mem:{note.get('id') or obs.id}",
            )
        )
        imported += 1
    ctx.db.close()
    print(json.dumps({"ok": True, "imported": imported, "skipped": skipped, "dry_run": bool(args.dry_run)}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mnemosyne")
    parser.add_argument("--data-dir", default="")
    parser.add_argument("--token", default="")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bak = sub.add_parser("backup", help="备份 memory.db")
    p_bak.add_argument("-o", "--output", default="")
    p_bak.set_defaults(func=cmd_backup)

    p_res = sub.add_parser("restore", help="从备份恢复")
    p_res.add_argument("backup")
    p_res.add_argument("--force", action="store_true")
    p_res.set_defaults(func=cmd_restore)

    p_h = sub.add_parser("health", help="本地打开库并打印 health")
    p_h.set_defaults(func=cmd_health)

    p_m = sub.add_parser("migrate-amem", help="从 A-MEM 或 JSONL 导入")
    p_m.add_argument("--jsonl", default="")
    p_m.add_argument("--project-root", default="")
    p_m.add_argument("--dry-run", action="store_true")
    p_m.set_defaults(func=cmd_migrate_amem)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
