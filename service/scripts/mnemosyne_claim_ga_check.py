# -*- coding: utf-8 -*-
"""P7 Claim-stack GA check — import + migrations + default gates LOCKED."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

REQUIRED_MIGRATIONS = (
    "009_claims_v1",
    "010_evidence_objects_v1",
    "011_tms_v1",
    "012_strategy_v1",
    "013_ab_v1",
    "014_knowledge_v1",
)

REQUIRED_MODULES = (
    "cognitive_memory.claims.store",
    "cognitive_memory.evidence.object_store",
    "cognitive_memory.tms.engine",
    "cognitive_memory.strategy.strategy_store",
    "cognitive_memory.governance.ab_experiment",
    "cognitive_memory.knowledge.store",
    "cognitive_memory.strategy.metacontroller",
)

GATES_MUST_LOCK = (
    "SCHEMA_MUTATION",
    "BANDIT_EXPERIMENT",
    "RL_OFFLINE_TRAINING",
    "RL_POLICY_DEPLOYMENT",
    "ADVANCED_VALUE_EVALUATION",
    "AUTONOMOUS_VALUE_ADAPTATION",
)


def main() -> int:
    report: dict = {"ok": True, "checks": []}

    for mod in REQUIRED_MODULES:
        try:
            __import__(mod)
            report["checks"].append({"check": f"import:{mod}", "ok": True})
        except Exception as exc:  # noqa: BLE001
            report["ok"] = False
            report["checks"].append(
                {"check": f"import:{mod}", "ok": False, "error": str(exc)}
            )

    from cognitive_memory.governance.capability_gate import check_capability
    from cognitive_memory.storage.db import Database
    from cognitive_memory.storage.migrations import MIGRATIONS

    mig_ids = {m[0] for m in MIGRATIONS}
    for mid in REQUIRED_MIGRATIONS:
        ok = mid in mig_ids
        report["checks"].append({"check": f"migration:{mid}", "ok": ok})
        if not ok:
            report["ok"] = False

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "ga.db")
        applied = db.ensure_schema()
        report["checks"].append(
            {"check": "ensure_schema", "ok": True, "applied": applied}
        )
        for cap in GATES_MUST_LOCK:
            pack = check_capability(db, cap)
            locked = not pack.get("allowed")
            report["checks"].append(
                {
                    "check": f"gate_locked:{cap}",
                    "ok": locked,
                    "level": pack.get("level"),
                }
            )
            if not locked:
                report["ok"] = False
        db.close()

    out = ROOT / "tmp" / "mnemosyne_claim_ga_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "report": str(out)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
