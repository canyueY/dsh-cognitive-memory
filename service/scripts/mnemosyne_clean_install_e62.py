# -*- coding: utf-8 -*-
"""E6.2 干净环境安装验收：独立目录 → config init → doctor → write → health → stop。

用法（仓库根）：
  py -3 scripts/mnemosyne_clean_install_e62.py
  py -3 scripts/mnemosyne_clean_install_e62.py --archive
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
    parser = argparse.ArgumentParser(description="E6.2 clean install acceptance")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    if not (CM_SRC / "cognitive_memory").is_dir():
        print("cognitive_memory missing", file=sys.stderr)
        return 2
    sys.path.insert(0, str(CM_SRC))

    from cognitive_memory.bootstrap import build_context
    from cognitive_memory.domain.models import (
        MemoryProposeIn,
        MemoryStatus,
        MemoryType,
        ObservationIn,
        SourceKind,
    )
    from cognitive_memory.node_config import write_default_config
    from cognitive_memory.node_cli import cmd_doctor

    base = Path(tempfile.mkdtemp(prefix="mnemosyne-e62-"))
    data_dir = base / "node"
    data_dir.mkdir()
    report: dict = {"ok": False, "gate": "E6.2", "data_dir": str(data_dir), "steps": []}

    try:
        cfg_path = write_default_config(data_dir / "node.config.json", data_dir=str(data_dir))
        report["steps"].append({"config_init": str(cfg_path)})

        class NS:
            pass

        doc = NS()
        doc.data_dir = str(data_dir)
        doc.config = str(cfg_path)
        doc.token = "e62-token"
        # doctor may print; capture via return code
        rc = cmd_doctor(doc)
        report["steps"].append({"doctor_rc": rc})
        if rc != 0:
            report["error"] = "doctor_failed"
            return 1

        ctx = build_context(data_dir=str(data_dir), token="e62-token")
        try:
            obs = ctx.service.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.SYSTEM,
                    content="e62 clean install observation",
                    producer="e62",
                    idempotency_key="e62:obs:1",
                )
            )
            mem = ctx.service.propose_memory(
                MemoryProposeIn(
                    type=MemoryType.SEMANTIC,
                    status=MemoryStatus.CANDIDATE,
                    content="e62 clean install memory",
                    source_ids=[obs.id],
                    idempotency_key="e62:mem:1",
                )
            )
            health = ctx.service.health()
            from cognitive_memory.domain.entity import upsert_entity

            ent = upsert_entity(ctx.db, name="e62-entity", kind="concept")
        finally:
            ctx.db.close()

        report["steps"].append(
            {
                "observation_id": obs.id,
                "memory_id": mem.id,
                "entity_id": ent["id"],
                "health": {
                    k: health.get(k)
                    for k in ("ok", "memories", "observations", "authority_state")
                },
            }
        )
        report["ok"] = bool(health.get("ok") and health.get("memories", 0) >= 1)
        report["pass_criteria"] = {
            "config_written": True,
            "doctor_ok": rc == 0,
            "write_ok": True,
            "health_ok": bool(health.get("ok")),
            "independent_data_dir": True,
        }
        report["ok"] = all(report["pass_criteria"].values())
        return 0 if report["ok"] else 1
    finally:
        out = Path(args.report) if args.report else base / "e62-report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.archive:
            arch = ROOT / "docs" / "reports" / "e6.2-clean-install.json"
            arch.parent.mkdir(parents=True, exist_ok=True)
            arch.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            report["archive_path"] = str(arch)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.keep:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
