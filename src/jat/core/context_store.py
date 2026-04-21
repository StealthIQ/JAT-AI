from __future__ import annotations

from uuid import UUID

import structlog

from jat.clients.supabase import SupabaseClient

log = structlog.get_logger()


class ContextStore:
    def __init__(self, supabase: SupabaseClient) -> None:
        self._db = supabase

    async def save_task_state(self, task_id: UUID, state: dict) -> None:
        await self._db.upsert("agent_tasks", {"id": str(task_id), **state})

    async def get_task_state(self, task_id: UUID) -> dict:
        rows = await self._db.select("agent_tasks", filters={"id": str(task_id)})
        return rows[0] if rows else {}

    async def save_context(self, task_id: UUID, context: dict) -> None:
        await self._db.upsert(
            "context_messages",
            {"task_id": str(task_id), "context": context},
        )

    async def get_context(self, task_id: UUID) -> dict:
        rows = await self._db.select(
            "context_messages", filters={"task_id": str(task_id)}
        )
        return rows[0].get("context", {}) if rows else {}

    async def get_task_results(self, task_ids: list[UUID]) -> list[dict]:
        results = []
        for task_id in task_ids:
            state = await self.get_task_state(task_id)
            if state:
                results.append(state)
        return results

    async def publish_message(
        self, from_task: UUID, to_task: UUID, message: dict
    ) -> None:
        await self._db.insert(
            "context_messages",
            {
                "from_task_id": str(from_task),
                "to_task_id": str(to_task),
                "message": message,
            },
        )

    async def get_messages_for_task(self, task_id: UUID) -> list[dict]:
        return await self._db.select(
            "context_messages", filters={"to_task_id": str(task_id)}
        )
