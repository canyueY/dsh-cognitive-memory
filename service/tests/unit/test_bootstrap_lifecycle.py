from pathlib import Path
from cognitive_memory.onboarding import diagnose,plan_install,install,rollback,verify
from cognitive_memory.bootstrap import build_context
from cognitive_memory.domain.models import MemoryProposeIn


def test_plan_readonly_install_verify_and_upgrade_restore(tmp_path):
    root=tmp_path/"bank"
    assert diagnose(root)["read_only"]
    plan=plan_install(root)
    assert not root.exists()
    assert install(plan)["detail"]=="approval_required"
    out=install(plan,confirm=True)
    assert out["ok"],out
    assert verify(root)["ok"]
    ctx=build_context(data_dir=str(root),token="t")
    try:
        before=ctx.service.propose_memory(MemoryProposeIn(content="before upgrade"))
    finally:
        ctx.db.close()
    plan=plan_install(root,upgrade=True)
    out=install(plan,confirm=True)
    assert out["ok"],out
    ctx=build_context(data_dir=str(root),token="t")
    try:
        after=ctx.service.propose_memory(MemoryProposeIn(content="after upgrade"))
    finally:
        ctx.db.close()
    assert rollback(root,out["receipt"],confirm=True)["ok"]
    ctx=build_context(data_dir=str(root),token="t")
    try:
        assert ctx.service.get_memory(before.id)
        assert ctx.db.connect().execute("SELECT 1 FROM memories WHERE id=?",(after.id,)).fetchone() is None
    finally:
        ctx.db.close()


def test_tampered_plan_and_concurrent_config_change_rejected(tmp_path):
    root=tmp_path/"bank"
    plan=plan_install(root)
    plan["data_dir"]=str(tmp_path/"other")
    assert install(plan,confirm=True)["detail"]=="plan_or_source_changed"
    plan=plan_install(root)
    root.mkdir();(root/"node.config.json").write_text("{}")
    assert install(plan,confirm=True)["detail"]=="configuration_changed"


def test_running_node_detection_is_read_only(tmp_path):
    import os,json
    from cognitive_memory.onboarding import node_running
    root=tmp_path/"bank";(root/"runtime").mkdir(parents=True)
    (root/"runtime/service.json").write_text(json.dumps({"pid":os.getpid()}))
    assert node_running(root)
    assert install(plan_install(root),confirm=True)["detail"]=="stop_node_before_install"
