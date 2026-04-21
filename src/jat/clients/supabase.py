from __future__ import annotations

import structlog
from supabase import create_client, Client

log = structlog.get_logger()


class SupabaseClient:
    def __init__(self, url: str, key: str) -> None:
        self._client: Client = create_client(url, key)

    @property
    def client(self) -> Client:
        return self._client

    async def insert(self, table: str, data: dict) -> dict:
        result = self._client.table(table).insert(data).execute()
        return result.data[0] if result.data else {}

    async def upsert(self, table: str, data: dict) -> dict:
        result = self._client.table(table).upsert(data).execute()
        return result.data[0] if result.data else {}

    async def select(
        self, table: str, columns: str = "*", filters: dict | None = None
    ) -> list[dict]:
        query = self._client.table(table).select(columns)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        result = query.execute()
        return result.data or []

    async def update(
        self, table: str, data: dict, filters: dict
    ) -> list[dict]:
        query = self._client.table(table).update(data)
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.execute()
        return result.data or []

    async def delete(self, table: str, filters: dict) -> None:
        query = self._client.table(table).delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        query.execute()
