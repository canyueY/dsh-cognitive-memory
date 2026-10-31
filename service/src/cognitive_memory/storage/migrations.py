# -*- coding: utf-8 -*-
"""SQLite schema migrations（V1.0 核心表）。"""

from __future__ import annotations

import sqlite3

MIGRATIONS: list[tuple[str, str]] = [
    (
        "001_core",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS observations (
          id TEXT PRIMARY KEY,
          source_kind TEXT NOT NULL,
          content TEXT NOT NULL,
          occurred_at TEXT,
          created_at TEXT NOT NULL,
          producer TEXT NOT NULL DEFAULT 'dsh',
          correlation_id TEXT,
          data_ref TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS memories (
          id TEXT PRIMARY KEY,
          type TEXT NOT NULL,
          status TEXT NOT NULL,
          content TEXT NOT NULL,
          source_ids_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_confirmed_at TEXT,
          version INTEGER NOT NULL DEFAULT 1,
          confidence REAL,
          expires_at TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS memory_versions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_id TEXT NOT NULL,
          version INTEGER NOT NULL,
          snapshot_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(memory_id, version)
        );

        CREATE TABLE IF NOT EXISTS memory_evidence (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_id TEXT NOT NULL,
          observation_id TEXT NOT NULL,
          relation TEXT NOT NULL DEFAULT 'supports',
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          UNIQUE(memory_id, observation_id, relation)
        );

        CREATE TABLE IF NOT EXISTS memory_relations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          from_id TEXT NOT NULL,
          to_id TEXT NOT NULL,
          relation TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memory_feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_id TEXT NOT NULL,
          useful INTEGER,
          incorrect INTEGER,
          note TEXT NOT NULL DEFAULT '',
          producer TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
          event_id TEXT PRIMARY KEY,
          event_type TEXT NOT NULL,
          event_version INTEGER NOT NULL DEFAULT 1,
          occurred_at TEXT NOT NULL,
          recorded_at TEXT NOT NULL,
          producer TEXT NOT NULL,
          correlation_id TEXT,
          causation_id TEXT,
          payload_version INTEGER NOT NULL DEFAULT 1,
          payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS outbox (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_id TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL DEFAULT 'pending',
          attempts INTEGER NOT NULL DEFAULT 0,
          next_attempt_at TEXT,
          last_error TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inbox (
          event_id TEXT PRIMARY KEY,
          consumer TEXT NOT NULL,
          processed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
          id TEXT PRIMARY KEY,
          task_type TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          payload_json TEXT NOT NULL DEFAULT '{}',
          attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          next_attempt_at TEXT
        );

        CREATE TABLE IF NOT EXISTS idempotency_keys (
          key TEXT PRIMARY KEY,
          scope TEXT NOT NULL,
          response_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
          memory_id UNINDEXED,
          content,
          type UNINDEXED,
          status UNINDEXED,
          tokenize = 'unicode61'
        );

        CREATE INDEX IF NOT EXISTS idx_memories_type_status ON memories(type, status);
        CREATE INDEX IF NOT EXISTS idx_observations_kind ON observations(source_kind);
        CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status, next_attempt_at);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, next_attempt_at);
        """,
    ),
    (
        "002_spatiotemporal",
        """
        -- 记忆间时空/演化关系扩展（仍属同一 Memory DB）
        ALTER TABLE memory_relations ADD COLUMN valid_from TEXT;
        ALTER TABLE memory_relations ADD COLUMN valid_until TEXT;
        ALTER TABLE memory_relations ADD COLUMN confidence REAL;
        ALTER TABLE memory_relations ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';

        CREATE INDEX IF NOT EXISTS idx_memory_relations_from ON memory_relations(from_id);
        CREATE INDEX IF NOT EXISTS idx_memory_relations_to ON memory_relations(to_id);
        CREATE INDEX IF NOT EXISTS idx_memory_relations_rel ON memory_relations(relation);

        -- 变化候选审计（运行态，不是第二套个人记忆）
        CREATE TABLE IF NOT EXISTS change_candidates (
          id TEXT PRIMARY KEY,
          change_type TEXT NOT NULL,
          source_observation_id TEXT,
          target_memory_id TEXT,
          payload_json TEXT NOT NULL DEFAULT '{}',
          dry_run INTEGER NOT NULL DEFAULT 1,
          applied INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          applied_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_change_candidates_applied ON change_candidates(applied, created_at);
        """,
    ),
    (
        "003_mnemosyne_emotion",
        """
        -- 情绪候选审计（运行态 shadow；非正式个人长期记忆）
        CREATE TABLE IF NOT EXISTS emotion_candidates (
          id TEXT PRIMARY KEY,
          observation_id TEXT,
          source_kind TEXT,
          payload_json TEXT NOT NULL DEFAULT '{}',
          shadow_only INTEGER NOT NULL DEFAULT 1,
          written INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_emotion_candidates_obs ON emotion_candidates(observation_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_emotion_candidates_written ON emotion_candidates(written, created_at);
        """,
    ),
    (
        "004_change_plans",
        """
        -- ChangePlan：治理审计（非第二套个人记忆正文）
        CREATE TABLE IF NOT EXISTS change_plans (
          id TEXT PRIMARY KEY,
          observation_id TEXT,
          change_type TEXT NOT NULL,
          risk_level TEXT NOT NULL DEFAULT 'medium',
          confidence REAL,
          approval_requirement TEXT NOT NULL DEFAULT 'human',
          execution_status TEXT NOT NULL DEFAULT 'proposed',
          verification_status TEXT NOT NULL DEFAULT 'pending',
          payload_json TEXT NOT NULL DEFAULT '{}',
          rollback_reference TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          applied_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_change_plans_status ON change_plans(execution_status, created_at);
        CREATE INDEX IF NOT EXISTS idx_change_plans_obs ON change_plans(observation_id, created_at);
        """,
    ),
    (
        "005_cognitive_schema_v2",
        """
        -- 认知图式：规律/假设（引用记忆证据，非正式个人 LT 正文）
        CREATE TABLE IF NOT EXISTS cognitive_schemas (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '',
          schema_type TEXT NOT NULL DEFAULT 'KNOWLEDGE',
          state TEXT NOT NULL DEFAULT 'PROPOSED',
          confidence REAL NOT NULL DEFAULT 0.4,
          version INTEGER NOT NULL DEFAULT 1,
          payload_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_state ON cognitive_schemas(state, updated_at);
        CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_type ON cognitive_schemas(schema_type, state);

        CREATE TABLE IF NOT EXISTS schema_versions (
          id TEXT PRIMARY KEY,
          schema_id TEXT NOT NULL,
          version INTEGER NOT NULL,
          change_type TEXT NOT NULL,
          reason TEXT NOT NULL DEFAULT '',
          payload_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_schema_versions_sid ON schema_versions(schema_id, version);

        CREATE TABLE IF NOT EXISTS cognitive_change_plans (
          id TEXT PRIMARY KEY,
          operation TEXT NOT NULL,
          risk_level TEXT NOT NULL DEFAULT 'MEDIUM',
          approval_required INTEGER NOT NULL DEFAULT 1,
          status TEXT NOT NULL DEFAULT 'PROPOSED',
          payload_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          applied_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cog_plans_status ON cognitive_change_plans(status, created_at);

        CREATE TABLE IF NOT EXISTS capability_permissions (
          capability TEXT PRIMARY KEY,
          enabled INTEGER NOT NULL DEFAULT 0,
          level TEXT NOT NULL DEFAULT 'LOCKED',
          requirements_json TEXT NOT NULL DEFAULT '[]',
          approved_at TEXT,
          expires_at TEXT,
          version INTEGER NOT NULL DEFAULT 1,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS capability_audit (
          id TEXT PRIMARY KEY,
          capability TEXT NOT NULL,
          action TEXT NOT NULL,
          detail_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_capability_audit_cap ON capability_audit(capability, created_at);
        """,
    ),
    (
        "006_identity_principals",
        """
        -- 单 Node Identity 最小模型（User / Node / Agent / External）
        CREATE TABLE IF NOT EXISTS identity_principals (
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          display_name TEXT NOT NULL DEFAULT '',
          external_ref TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_identity_principals_kind
          ON identity_principals(kind, id);
        """,
    ),
    (
        "007_evidence_bank_authority",
        """
        -- Evidence provenance 加固
        ALTER TABLE memory_evidence ADD COLUMN confidence REAL;
        ALTER TABLE memory_evidence ADD COLUMN evidence_kind TEXT NOT NULL DEFAULT 'observation';
        ALTER TABLE memory_evidence ADD COLUMN validation_state TEXT NOT NULL DEFAULT 'unverified';
        ALTER TABLE memory_evidence ADD COLUMN producer TEXT NOT NULL DEFAULT '';
        ALTER TABLE memory_evidence ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';

        -- Memory Bank 逻辑空间
        CREATE TABLE IF NOT EXISTS memory_banks (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        ALTER TABLE memories ADD COLUMN bank_id TEXT NOT NULL DEFAULT 'personal';
        CREATE INDEX IF NOT EXISTS idx_memories_bank ON memories(bank_id, status);

        -- Adoption Authority 五态
        CREATE TABLE IF NOT EXISTS authority_state (
          id TEXT PRIMARY KEY,
          state TEXT NOT NULL,
          previous_state TEXT,
          reason TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        """,
    ),
    (
        "008_agent_grants_audit",
        """
        -- 同 Node 多 Agent：授权（权限/Bank/有效期/撤销）+ 审计
        CREATE TABLE IF NOT EXISTS agent_grants (
          id TEXT PRIMARY KEY,
          agent_id TEXT NOT NULL,
          token_hash TEXT NOT NULL,
          permissions_json TEXT NOT NULL DEFAULT '[]',
          banks_json TEXT NOT NULL DEFAULT '[]',
          consent_json TEXT NOT NULL DEFAULT '{}',
          expires_at TEXT,
          revoked_at TEXT,
          revoke_reason TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_agent_grants_agent
          ON agent_grants(agent_id, revoked_at, expires_at);

        CREATE TABLE IF NOT EXISTS agent_audit (
          id TEXT PRIMARY KEY,
          agent_id TEXT NOT NULL,
          action TEXT NOT NULL,
          resource TEXT NOT NULL DEFAULT '',
          decision TEXT NOT NULL,
          detail_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_agent_audit_agent
          ON agent_audit(agent_id, created_at);
        """,
    ),
    (
        "009_claims_v1",
        """
        -- P2 Claim vertical slice: first-class Claim rows (not Memory projections)
        CREATE TABLE IF NOT EXISTS claims (
          id TEXT PRIMARY KEY,
          bank_id TEXT NOT NULL DEFAULT 'personal',
          ast_version TEXT NOT NULL,
          ast_json TEXT NOT NULL,
          surface TEXT NOT NULL DEFAULT '',
          normalized_hash TEXT NOT NULL,
          lifecycle TEXT NOT NULL DEFAULT 'proposed',
          verification_status TEXT NOT NULL DEFAULT 'unverified',
          scope_json TEXT NOT NULL DEFAULT '{}',
          source_memory_id TEXT,
          redirects_to TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_claims_bank_life
          ON claims(bank_id, lifecycle, updated_at);
        CREATE INDEX IF NOT EXISTS idx_claims_hash
          ON claims(normalized_hash);
        CREATE INDEX IF NOT EXISTS idx_claims_source_mem
          ON claims(source_memory_id);
        CREATE INDEX IF NOT EXISTS idx_claims_redirect
          ON claims(redirects_to);

        CREATE TABLE IF NOT EXISTS claim_evidence (
          id TEXT PRIMARY KEY,
          claim_id TEXT NOT NULL,
          evidence_ref TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'support',
          independent INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim
          ON claim_evidence(claim_id, role);

        CREATE TABLE IF NOT EXISTS claim_lifecycle_events (
          id TEXT PRIMARY KEY,
          claim_id TEXT NOT NULL,
          from_status TEXT NOT NULL,
          to_status TEXT NOT NULL,
          reason TEXT NOT NULL DEFAULT '',
          actor TEXT NOT NULL DEFAULT '',
          policy_version TEXT NOT NULL DEFAULT 'claim.lifecycle.v1',
          evidence_refs_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_claim_life_events
          ON claim_lifecycle_events(claim_id, created_at);

        CREATE TABLE IF NOT EXISTS verification_records (
          id TEXT PRIMARY KEY,
          claim_id TEXT NOT NULL,
          status TEXT NOT NULL,
          evidence_refs_json TEXT NOT NULL DEFAULT '[]',
          actor TEXT NOT NULL DEFAULT '',
          verified_at TEXT,
          expired_at TEXT,
          detail_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_verification_claim
          ON verification_records(claim_id, created_at);
        """,
    ),
    (
        "010_evidence_objects_v1",
        """
        -- P3: first-class Evidence objects (memory_evidence remains legacy bridge)
        CREATE TABLE IF NOT EXISTS evidences (
          id TEXT PRIMARY KEY,
          bank_id TEXT NOT NULL DEFAULT 'personal',
          source_type TEXT NOT NULL,
          source_ref TEXT NOT NULL DEFAULT '',
          fingerprint TEXT NOT NULL,
          provenance_status TEXT NOT NULL DEFAULT 'unknown',
          independence_key TEXT NOT NULL DEFAULT '',
          root_source_id TEXT NOT NULL DEFAULT '',
          producer TEXT NOT NULL DEFAULT '',
          role_hint TEXT NOT NULL DEFAULT 'support',
          validation_state TEXT NOT NULL DEFAULT 'unverified',
          security_json TEXT NOT NULL DEFAULT '{}',
          chain_json TEXT NOT NULL DEFAULT '[]',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          legacy_memory_id TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_evidences_fingerprint
          ON evidences(fingerprint);
        CREATE INDEX IF NOT EXISTS idx_evidences_source
          ON evidences(source_type, source_ref);
        CREATE INDEX IF NOT EXISTS idx_evidences_indep
          ON evidences(independence_key);
        CREATE INDEX IF NOT EXISTS idx_evidences_bank
          ON evidences(bank_id, created_at);
        """,
    ),
    (
        "011_tms_v1",
        """
        -- P4 Truth Maintenance: justifications + belief snapshots
        CREATE TABLE IF NOT EXISTS tms_justifications (
          id TEXT PRIMARY KEY,
          conclusion_id TEXT NOT NULL,
          premises_json TEXT NOT NULL DEFAULT '[]',
          kind TEXT NOT NULL DEFAULT 'support',
          valid INTEGER NOT NULL DEFAULT 1,
          reason TEXT NOT NULL DEFAULT '',
          actor TEXT NOT NULL DEFAULT '',
          policy_version TEXT NOT NULL DEFAULT 'tms.v1',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tms_just_conclusion
          ON tms_justifications(conclusion_id, valid);
        CREATE TABLE IF NOT EXISTS tms_beliefs (
          node_id TEXT PRIMARY KEY,
          status TEXT NOT NULL,
          reason_codes_json TEXT NOT NULL DEFAULT '[]',
          updated_at TEXT NOT NULL
        );
        """,
    ),
]


def apply_migrations(conn: sqlite3.Connection) -> list[str]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )
    applied = {
        row[0]
        for row in conn.execute("SELECT id FROM schema_migrations").fetchall()
    }
    done: list[str] = []
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for mid, sql in MIGRATIONS:
        if mid in applied:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(id, applied_at) VALUES (?, ?)",
            (mid, now),
        )
        done.append(mid)
    conn.commit()
    return done
