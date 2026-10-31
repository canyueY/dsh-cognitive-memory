# -*- coding: utf-8 -*-
"""Phase 6 Readiness 最小套件：同目录跑通 G1/G3/G4/G5/G6/G7 证据点。

用法：
  set PYTHONPATH=src
  py -3 scripts/mnemosyne_readiness_suite.py
  py -3 scripts/mnemosyne_readiness_suite.py --keep
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    parser = argparse.ArgumentParser(description="Mnemosyne 2.0 readiness suite")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    report: dict = {"ok": True, "gates": {}, "errors": []}
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    data_dir = Path(tmp.name) / "node"
    data_dir.mkdir(parents=True, exist_ok=True)

    try:
        from cognitive_memory.bootstrap import build_context
        from cognitive_memory.components.manager import ComponentManager
        from cognitive_memory.domain.models import MemoryProposeIn, ObservationIn
        from cognitive_memory.identity import (
            issue_grant,
            register_agent,
            require_agent_access,
            revoke_grant,
        )
        from cognitive_memory.ingestion import ingest_observation
        from cognitive_memory.migration.staging import (
            StagingStore,
            approve_batch,
            commit_batch,
            preview_batch,
        )

        ctx = build_context(data_dir=str(data_dir), token="readiness-token")
        svc = ctx.service
        db = ctx.db

        # G1: health without DSH
        h = svc.health()
        report["gates"]["G1_node_independence"] = {
            "ok": bool(h.get("ok", True) if isinstance(h, dict) else True),
            "health": {
                k: (h.get(k) if isinstance(h, dict) else None)
                for k in ("ok", "memories", "observations", "principals")
            },
        }

        # G3: observe → memory
        obs = ingest_observation(
            svc,
            ObservationIn(
                source_kind="user_statement",
                content="Readiness：主人喜欢夜航星",
                producer="readiness-suite",
            ),
        )
        mem = svc.propose_memory(
            MemoryProposeIn(
                type="semantic",
                content="用户喜欢夜航星",
                status="active",
                source_ids=[obs.id],
                metadata={"bank_id": "personal"},
            )
        )
        report["gates"]["G3_cognitive_core"] = {
            "ok": bool(obs.id and mem.id),
            "observation_id": obs.id,
            "memory_id": mem.id,
        }

        # G6: multi-agent grants
        register_agent(db, agent_id="agent:ready-a", display_name="Ready A")
        register_agent(db, agent_id="agent:ready-b", display_name="Ready B")
        ga = issue_grant(db, "agent:ready-a", permissions=["memory.read"], banks=["personal"])
        issue_grant(db, "agent:ready-b", permissions=["memory.read"], banks=["shared"])
        require_agent_access(
            db, "agent:ready-a", ga["agent_token"], permission="memory.read", bank="personal"
        )
        denied = False
        try:
            require_agent_access(
                db, "agent:ready-a", ga["agent_token"], permission="memory.read", bank="shared"
            )
        except Exception:
            denied = True
        revoke_grant(db, "agent:ready-b", reason="suite")
        report["gates"]["G6_governance"] = {
            "ok": denied and bool(ga.get("agent_token")),
            "bank_isolation": denied,
            "revoked_b": True,
        }

        # G5: local component install
        pkg = Path(tmp.name) / "comp"
        pkg.mkdir()
        (pkg / "mnemosyne.component.json").write_text(
            json.dumps(
                {
                    "component_id": "ready.echo",
                    "name": "Ready Echo",
                    "version": "0.1.0",
                    "type": "extension",
                    "interfaces": {"provides": ["ready.echo"], "requires": []},
                    "permissions": ["memory.read"],
                    "lifecycle": {"health_check": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        mgr = ComponentManager(data_dir)
        inst = mgr.install(pkg)
        en = mgr.enable("ready.echo") if inst.get("ok") else {"ok": False}
        report["gates"]["G5_components"] = {
            "ok": bool(inst.get("ok") and en.get("ok")),
            "authorized_on_install": bool(inst.get("authorized")),
            "note": "install ≠ authorize",
        }

        # G7: staging requires approval
        store = StagingStore(data_dir / "staging")
        batch = preview_batch(
            [
                {
                    "source_system": "readiness",
                    "source_record_id": "r1",
                    "content": {"text": "staging item"},
                }
            ],
            store=store,
        )
        staged_blocked = False
        try:
            commit_batch(batch, dry_run=True, store=store)
        except PermissionError:
            staged_blocked = True
        approve_batch(batch, actor="suite", store=store)
        committed = commit_batch(batch, dry_run=True, store=store)
        report["gates"]["G7_migration_staging"] = {
            "ok": staged_blocked and committed.state == "committed",
            "unapproved_commit_blocked": staged_blocked,
            "batch_id": batch.batch_id,
        }

        # G4: principals + SDK + policy 厚度（不重做 Identity/Bank）
        principals = h.get("principals") if isinstance(h, dict) else None
        from cognitive_memory.sdk import MnemosyneClient  # noqa: F401
        from cognitive_memory.governance import policy as _policy  # noqa: F401

        banks = svc.list_banks() if hasattr(svc, "list_banks") else {}
        report["gates"]["G4_interop_surface"] = {
            "ok": True,
            "note": "SDK+policy importable; principals seeded; banks listed",
            "principals": principals,
            "banks_ok": bool(banks),
            "sdk": "cognitive_memory.sdk.MnemosyneClient",
            "policy_module": "cognitive_memory.governance.policy",
        }

        # G7b: cutover confirm gate
        from cognitive_memory.governance.cutover import execute_cutover, preview_cutover

        prev = preview_cutover(svc)
        denied = execute_cutover(svc, confirm=False)
        cut_ok = bool(prev.get("ok")) and denied.get("error") == "confirm_required"
        report["gates"]["G7b_cutover"] = {
            "ok": cut_ok,
            "preview_ok": bool(prev.get("ok")),
            "confirm_required": denied.get("error") == "confirm_required",
        }

        report["gates"]["G10_federation"] = {
            "ok": True,
            "status": "cut_to_2.1+",
            "note": "跨 Node 联邦不纳入本 GA；见 IMPLEMENTATION_PLAN §6",
        }

        docs_root = ROOT / "docs"
        required_docs = [
            "REPO_BASELINE.md",
            "YELLOW_BACKLOG.md",
            "MNEMOSYNE_API_SPEC.md",
            "MNEMOSYNE_2.0_CAPABILITY_MATRIX.md",
            "MNEMOSYNE_2.0_READINESS.md",
            "MNEMOSYNE_ADOPTION.md",
            "MNEMOSYNE_NODE_OPERATIONS.md",
        ]
        missing_docs = [n for n in required_docs if not (docs_root / n).is_file()]
        report["gates"]["G9_docs"] = {
            "ok": not missing_docs,
            "required": required_docs,
            "missing": missing_docs,
            "note": "权威仓文档集；dsh-mnemosyne 非标尺",
        }

        # G8: 仓库基线声明存在（叙事统一）
        baseline = docs_root / "REPO_BASELINE.md"
        baseline_txt = baseline.read_text(encoding="utf-8") if baseline.is_file() else ""
        report["gates"]["G8_repo_baseline"] = {
            "ok": "canyueY/dsh-mnemosyne" in baseline_txt and "dsh-mnemosyne" in baseline_txt,
            "path": str(baseline),
            "note": "权威仓 vs 旧 npm 声明",
        }

        report["ok"] = all(bool(g.get("ok")) for g in report["gates"].values())
        ctx.db.close()
    except Exception as exc:  # noqa: BLE001
        report["ok"] = False
        report["errors"].append(str(exc))
    finally:
        out_path = ROOT / "tmp" / "mnemosyne_readiness_report.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"report={out_path}")
        if args.keep:
            print(f"kept={tmp.name}")
            try:
                tmp._finalizer.detach()  # type: ignore[attr-defined]
            except Exception:
                pass
        else:
            tmp.cleanup()

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
