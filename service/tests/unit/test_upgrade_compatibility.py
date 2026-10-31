import sqlite3
from cognitive_memory.storage.db import Database
from cognitive_memory.storage.migrations import MIGRATIONS
from cognitive_memory.onboarding import manifest,BootstrapManifest


def test_foundation_database_upgrades_with_backup_and_preserves_rows(tmp_path):
    path=tmp_path/"memory.db"
    conn=sqlite3.connect(path)
    conn.execute("CREATE TABLE schema_migrations(id TEXT PRIMARY KEY,applied_at TEXT NOT NULL)")
    for mid,sql in MIGRATIONS[:9]:
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_migrations VALUES (?,?)",(mid,"2026-01-01T00:00:00Z"))
        conn.commit()
    conn.execute("""INSERT INTO memories(id,type,status,content,created_at,updated_at)
                  VALUES ('legacy','semantic','candidate','preserve legacy content','2026-01-01','2026-01-01')""")
    conn.commit();conn.close()
    db=Database(path)
    try:
        assert db.ensure_schema()
        assert db.connect().execute("SELECT content FROM memories WHERE id='legacy'").fetchone()[0]=="preserve legacy content"
        assert db.connect().execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        backups=list((tmp_path/"migration-backups").glob("*.db"))
        assert len(backups)==1
        old=sqlite3.connect(backups[0])
        try:
            assert old.execute("SELECT content FROM memories WHERE id='legacy'").fetchone()[0]=="preserve legacy content"
            assert old.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]==9
        finally:
            old.close()
        assert db.ensure_schema()==[]
    finally:
        db.close()


def test_machine_manifest_is_valid_and_source_is_local():
    m=BootstrapManifest.model_validate(manifest())
    assert m.source["type"]=="local_checkout"
    assert len(m.checksums["source_sha256"])==64
    assert m.signatures==[]


def test_bank_copy_snapshots_wal_and_does_not_transfer_live_runtime(tmp_path):
    from cognitive_memory.storage.paths import copy_memory_bank,ensure_layout
    source=tmp_path/"source";target=tmp_path/"target"
    ensure_layout(source)
    connection=sqlite3.connect(source/"data/memory.db")
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE fixture(value TEXT)")
        connection.execute("INSERT INTO fixture VALUES ('wal snapshot')")
        connection.commit()
        (source/"runtime/service.json").write_text('{"pid":12345}')
        result=copy_memory_bank(source,target)
        assert result["ok"]
        assert not (target/"runtime/service.json").exists()
        copied=sqlite3.connect(target/"data/memory.db")
        try:
            assert copied.execute("SELECT value FROM fixture").fetchone()[0]=="wal snapshot"
        finally:
            copied.close()
        assert copy_memory_bank(source,source/"nested")["error"]=="overlapping_source_and_target"
    finally:
        connection.close()
