import sqlite3
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

    def _init_tables(self) -> None:
        conn = self._conn
        assert conn is not None
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                api_key_encrypted TEXT NOT NULL,
                plan TEXT DEFAULT 'free',
                enabled INTEGER DEFAULT 1,
                daily_limit INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
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
        """)
        conn.commit()

    async def select(self, table: str, filters: dict[str, Any] | None = None) -> list[dict]:
        conn = self._get_conn()
        where = ""
        params: list[Any] = []
        if filters:
            clauses = [f"{k} = ?" for k in filters]
            where = " WHERE " + " AND ".join(clauses)
            params = list(filters.values())
        cursor = conn.execute(f"SELECT * FROM {table}{where}", params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    async def insert(self, table: str, data: dict[str, Any]) -> dict:
        conn = self._get_conn()
        keys = list(data.keys())
        placeholders = ", ".join(["?"] * len(keys))
        cols = ", ".join(keys)
        conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(data.values()))
        conn.commit()
        return data

    async def update(self, table: str, id_val: str, data: dict[str, Any]) -> dict:
        conn = self._get_conn()
        sets = ", ".join([f"{k} = ?" for k in data])
        params = list(data.values()) + [id_val]
        conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", params)
        conn.commit()
        return {**data, "id": id_val}

    async def delete(self, table: str, id_val: str) -> bool:
        conn = self._get_conn()
        conn.execute(f"DELETE FROM {table} WHERE id = ?", [id_val])
        conn.commit()
        return True

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
