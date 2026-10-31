# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from cognitive_memory.migration import MemoryMigrationEngine, MigrationConfig, SourceRecord
from cognitive_memory.migration.checkpoint import CheckpointStore
from cognitive_memory.migration.mapping import map_source_record
from cognitive_memory.migration.sink import RecordingSink
from cognitive_memory.migration.sources import iter_jsonl, source_record_from_dict


def test_map_infers_episodic_from_tags() -> None:
    mapped = map_source_record(
        SourceRecord(source_id="1", content="昨天一起打了怪", tags=["episode", "mc"])
    )
    assert mapped.skip_reason is None
    assert mapped.memory_type == "episodic"
    assert mapped.observation_idempotency_key == "amem:1"
    assert mapped.memory_idempotency_key == "amem-mem:1"


def test_map_skips_short_content() -> None:
    mapped = map_source_record(SourceRecord(source_id="x", content=" ", tags=[]))
    assert mapped.skip_reason == "content_too_short"


def test_jsonl_source(tmp_path: Path) -> None:
    p = tmp_path / "notes.jsonl"
    p.write_text(
        "\n".join(
            [
                json.dumps({"id": "a", "content": "喜欢吃番茄炒蛋", "tags": ["food"]}, ensure_ascii=False),
                json.dumps({"id": "b", "content": "x", "tags": []}, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )
    rows = list(iter_jsonl(p))
    assert len(rows) == 2
    assert rows[0].source_id == "a"
    assert source_record_from_dict({"text": "hello", "keywords": "a,b"}).tags == ["a", "b"]


def test_engine_dry_run_and_resume(tmp_path: Path) -> None:
    ck = tmp_path / "ck.json"
    records = [
        SourceRecord(source_id="1", content="第一条长期偏好：不吃香菜", tags=["preference"]),
        SourceRecord(source_id="2", content="第二条：夜里常打 MC", tags=["episode"]),
        SourceRecord(source_id="3", content="", tags=[]),
    ]
    dry_sink = RecordingSink()
    report = MemoryMigrationEngine(
        dry_sink,
        config=MigrationConfig(dry_run=True, resume=True, checkpoint_path=ck),
    ).run(records)
    assert report.imported == 2
    assert report.skipped == 1
    assert report.failed == 0
    # dry-run 不写 checkpoint 完成态
    assert not CheckpointStore.load(ck).completed

    sink = RecordingSink()
    report2 = MemoryMigrationEngine(
        sink,
        config=MigrationConfig(dry_run=False, resume=True, checkpoint_path=ck),
    ).run(records)
    assert report2.imported == 2
    assert report2.skipped == 1
    assert len(sink.writes) == 2
    store = CheckpointStore.load(ck)
    assert "1" in store.completed and "2" in store.completed

    # 续跑应跳过已完成（含先前因过短而 skip 并记入 checkpoint 的条目）
    sink2 = RecordingSink()
    report3 = MemoryMigrationEngine(
        sink2,
        config=MigrationConfig(dry_run=False, resume=True, checkpoint_path=ck),
    ).run(records)
    assert report3.resumed_skipped == 3
    assert report3.imported == 0
    assert report3.skipped == 0
    assert sink2.writes == []


def test_engine_limit() -> None:
    sink = RecordingSink()
    records = [
        SourceRecord(source_id=str(i), content=f"note-{i}-long-enough", tags=[])
        for i in range(5)
    ]
    report = MemoryMigrationEngine(
        sink, config=MigrationConfig(dry_run=True, limit=2)
    ).run(records)
    assert report.total == 2
    assert report.imported == 2


def test_engine_inprocess_service(tmp_path: Path) -> None:
    from cognitive_memory.bootstrap import build_context

    ctx = build_context(data_dir=str(tmp_path), token="mig-test")
    try:
        report = MemoryMigrationEngine.from_service(
            ctx.service,
            config=MigrationConfig(
                dry_run=False,
                checkpoint_path=tmp_path / "ck.json",
            ),
        ).run(
            [
                SourceRecord(
                    source_id="svc1",
                    content="迁移集成：用户讨厌香菜",
                    tags=["preference"],
                )
            ]
        )
    finally:
        ctx.db.close()
    assert report.imported == 1
    assert report.failed == 0
    assert report.written[0]["memory_id"]

