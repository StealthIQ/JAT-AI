import sqlite3
import uuid
from pathlib import Path
from typing import Any


class LocalDB:
    def __init__(self, db_path: str = "./data/jat.db"):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_tables()
        return self._conn

    def _schema(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                api_key_encrypted TEXT NOT NULL,
                plan TEXT DEFAULT 'free',
                plan_tier TEXT DEFAULT 'free',
                enabled INTEGER DEFAULT 1,
                daily_limit INTEGER DEFAULT 0,
                sessions_today INTEGER DEFAULT 0,
                max_daily_tasks INTEGER DEFAULT 300,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS account_sources (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                repo_owner TEXT NOT NULL,
                repo_name TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                UNIQUE (account_id, source_name)
            );
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id TEXT PRIMARY KEY,
                workflow_id TEXT,
                session_id TEXT,
                prompt TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                repo_owner TEXT,
                repo_name TEXT,
                branch TEXT,
                pr_url TEXT,
                error TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS session_activities (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                activity_type TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS context_messages (
                id TEXT PRIMARY KEY,
                workflow_id TEXT,
                from_task_id TEXT,
                to_task_id TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                definition TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS ai_providers (
                id TEXT PRIMARY KEY,
                provider_type TEXT NOT NULL,
                name TEXT NOT NULL UNIQUE,
                api_key_encrypted TEXT NOT NULL,
                model TEXT,
                base_url TEXT,
                enabled INTEGER DEFAULT 1,
                daily_limit INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS prompts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'user',
                category TEXT DEFAULT 'general',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS merge_queue (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                pr_url TEXT NOT NULL,
                strategy TEXT DEFAULT 'squash',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT DEFAULT 'New Conversation',
                mode TEXT DEFAULT 'ask',
                repo_owner TEXT DEFAULT '',
                repo_name TEXT DEFAULT '',
                model TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS token_usage (
                id TEXT PRIMARY KEY,
                provider_type TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                conversation_id TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                title TEXT DEFAULT '',
                plan_json TEXT NOT NULL DEFAULT '{}',
                status TEXT DEFAULT 'draft',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """

    def _seed_prompts(self) -> None:
        conn = self._get_conn()
        seeds = [
            ("security-audit", "Perform a security audit following OWASP Top 10", "builtin"),
            ("add-tests", "Add comprehensive test coverage", "builtin"),
            ("code-review", "Review code for correctness, performance, and security", "builtin"),
            ("new-project", "Scaffold a new project with best practices", "builtin"),
            ("fix-issues", "Diagnose and fix reported issues", "builtin"),
        ]
        for name, content, source in seeds:
            conn.execute(
                "INSERT OR IGNORE INTO prompts (id, name, content, source) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), name, content, source),
            )
        conn.commit()

    def _init_tables(self) -> None:
        conn = self._conn
        assert conn is not None
        conn.executescript(self._schema())
        conn.commit()
        self._seed_prompts()

    async def select(self, table: str, filters: dict[str, Any] | None = None, columns: str | None = None, order_by: str | None = None) -> list[dict]:
        conn = self._get_conn()
        cols = columns if columns else "*"
        where = ""
        params: list[Any] = []
        if filters:
            clauses = [f"{k} = ?" for k in filters]
            where = " WHERE " + " AND ".join(clauses)
            params = list(filters.values())
        order = f" ORDER BY {order_by}" if order_by else ""
        cursor = conn.execute(f"SELECT {cols} FROM {table}{where}{order}", params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    async def insert(self, table: str, data: dict[str, Any]) -> dict:
        conn = self._get_conn()
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        keys = list(data.keys())
        placeholders = ", ".join(["?"] * len(keys))
        cols = ", ".join(keys)
        conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(data.values()))
        conn.commit()
        return data

    async def update(self, table: str, data: dict[str, Any], filters: dict[str, Any] | None = None) -> list[dict]:
        conn = self._get_conn()
        sets = ", ".join([f"{k} = ?" for k in data])
        params = list(data.values())
        where = ""
        if filters:
            clauses = [f"{k} = ?" for k in filters]
            where = " WHERE " + " AND ".join(clauses)
            params.extend(filters.values())
        elif isinstance(filters, str):
            where = " WHERE id = ?"
            params.append(filters)
        conn.execute(f"UPDATE {table} SET {sets}{where}", params)
        conn.commit()
        return [data]

    async def delete(self, table: str, filters: dict[str, Any] | str | None = None) -> bool:
        conn = self._get_conn()
        where = ""
        params: list[Any] = []
        if isinstance(filters, dict):
            clauses = [f"{k} = ?" for k in filters]
            where = " WHERE " + " AND ".join(clauses)
            params = list(filters.values())
        elif isinstance(filters, str):
            where = " WHERE id = ?"
            params = [filters]
        conn.execute(f"DELETE FROM {table}{where}", params)
        conn.commit()
        return True

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
