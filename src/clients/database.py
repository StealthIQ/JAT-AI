import asyncio
import structlog
from enum import Enum
from typing import Any

from clients.local_db import LocalDB
from clients.supabase import SupabaseClient

logger = structlog.get_logger()


class DBMode(str, Enum):
    LOCAL = "local"
    SUPABASE = "supabase"
    HYBRID = "hybrid"


class Database:

    def __init__(self, mode: str = "local", local_path: str = "./data/jat.db", sync_interval: int = 30):
        self._mode = DBMode(mode)
        self._local = LocalDB(local_path) if self._mode in (DBMode.LOCAL, DBMode.HYBRID) else None
        self._remote: SupabaseClient | None = None
        self._sync_interval = sync_interval
        self._sync_task: asyncio.Task | None = None

    def set_remote(self, client: SupabaseClient) -> None:
        self._remote = client
        if self._mode == DBMode.SUPABASE and self._local:
            self._local = None

    async def select(self, table: str, filters: dict[str, Any] | None = None, columns: str | None = None, order_by: str | None = None) -> list[dict]:
        if self._mode == DBMode.LOCAL:
            return await self._local.select(table, filters, columns, order_by)
        if self._mode == DBMode.SUPABASE:
            return await self._remote_select(table, filters, columns, order_by)
        return await self._local.select(table, filters, columns, order_by)

    async def insert(self, table: str, data: dict[str, Any]) -> dict:
        if self._mode == DBMode.LOCAL:
            return await self._local.insert(table, data)
        if self._mode == DBMode.SUPABASE:
            return await self._remote_insert(table, data)
        result = await self._local.insert(table, data)
        asyncio.create_task(self._sync_insert(table, data))
        return result

    async def update(self, table: str, data: dict[str, Any], filters: dict[str, Any] | None = None) -> list[dict]:
        if self._mode == DBMode.LOCAL:
            return await self._local.update(table, data, filters)
        if self._mode == DBMode.SUPABASE:
            id_val = filters.get("id", "") if filters else ""
            return [await self._remote_update(table, id_val, data)]
        result = await self._local.update(table, data, filters)
        id_val = filters.get("id", "") if filters else ""
        if id_val:
            asyncio.create_task(self._sync_update(table, id_val, data))
        return result

    async def delete(self, table: str, filters: dict[str, Any] | str | None = None) -> bool:
        if self._mode == DBMode.LOCAL:
            return await self._local.delete(table, filters)
        id_val = filters.get("id", "") if isinstance(filters, dict) else (filters or "")
        if self._mode == DBMode.SUPABASE:
            return await self._remote_delete(table, id_val)
        await self._local.delete(table, filters)
        if id_val:
            asyncio.create_task(self._sync_delete(table, id_val))
        return True

    @property
    def mode(self) -> str:
        return self._mode.value

    async def _remote_select(self, table: str, filters: dict[str, Any] | None, columns: str | None = None, order_by: str | None = None) -> list[dict]:
        if not self._remote:
            return []
        cols = columns if columns else "*"
        query = self._remote.client.table(table).select(cols)
        if filters:
            for k, v in filters.items():
                query = query.eq(k, v)
        if order_by:
            desc = order_by.endswith(" DESC")
            col = order_by.replace(" DESC", "").replace(" ASC", "").strip()
            query = query.order(col, desc=desc)
        res = query.execute()
        return res.data or []

    async def _remote_insert(self, table: str, data: dict[str, Any]) -> dict:
        if not self._remote:
            return data
        res = self._remote.client.table(table).insert(data).execute()
        return res.data[0] if res.data else data

    async def _remote_update(self, table: str, id_val: str, data: dict[str, Any]) -> dict:
        if not self._remote:
            return data
        res = self._remote.client.table(table).update(data).eq("id", id_val).execute()
        return res.data[0] if res.data else data

    async def _remote_delete(self, table: str, id_val: str) -> bool:
        if not self._remote:
            return True
        self._remote.client.table(table).delete().eq("id", id_val).execute()
        return True

    async def _sync_insert(self, table: str, data: dict[str, Any]) -> None:
        try:
            await self._remote_insert(table, data)
        except Exception as e:
            logger.warning("sync_insert_failed", table=table, error=str(e))

    async def _sync_update(self, table: str, id_val: str, data: dict[str, Any]) -> None:
        try:
            await self._remote_update(table, id_val, data)
        except Exception as e:
            logger.warning("sync_update_failed", table=table, id=id_val, error=str(e))

    async def _sync_delete(self, table: str, id_val: str) -> None:
        try:
            await self._remote_delete(table, id_val)
        except Exception as e:
            logger.warning("sync_delete_failed", table=table, id=id_val, error=str(e))

    def close(self) -> None:
        if self._local:
            self._local.close()
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
