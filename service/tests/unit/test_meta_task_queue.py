import time
from pathlib import Path
from cognitive_memory.storage.db import Database
from cognitive_memory.strategy.task_queue import MetaTaskQueue,stamp


def test_restart_dedup_cooldown_and_retry(tmp_path):
    db=Database(tmp_path/"tasks.db")
    try:
        q=MetaTaskQueue(db)
        first=q.submit(trigger="periodic",now=100,cooldown_seconds=10)
        assert q.submit(trigger="periodic",now=101)["deduplicated"]
        assert MetaTaskQueue(db).run_once(now=102)["status"]=="done"
        assert q.submit(trigger="periodic",now=103)["deduplicated"]
        assert not q.submit(trigger="periodic",now=113)["deduplicated"]
        def fail(ref,p):
            raise RuntimeError("controlled failure")
        assert q.run_once(now=114,handler=fail)["status"]=="pending"
        assert not q.run_once(now=115)["executed"]
        assert q.run_once(now=117)["status"]=="done"
        assert q.get(first["task_id"])["payload"]["result"]
    finally:
        db.close()


def test_aging_lease_recovery_and_budget(tmp_path):
    db=Database(tmp_path/"tasks.db")
    try:
        q=MetaTaskQueue(db)
        old=q.submit(trigger="old",priority=0,now=0)
        q.submit(trigger="new",priority=100,now=4000)
        assert q.run_once(now=4001)["task_id"]==old["task_id"]
        with db.transaction() as conn:
            conn.execute("UPDATE tasks SET status='running',next_attempt_at=?,attempts=1 WHERE status='pending'",(stamp(4002),))
        assert q.run_once(now=4003)["status"]=="done"
        q.submit(trigger="budget",now=5000,budget_ms=1)
        def slow(ref,p):
            time.sleep(0.01)
            return {"ok":True}
        assert q.run_once(now=5001,handler=slow)["status"]=="budget_exceeded"
    finally:
        db.close()
