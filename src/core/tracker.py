from __future__ import annotations

from uuid import UUID

import structlog

from clients.supabase import SupabaseClient

log = structlog.get_logger()


class Tracker:
    def __init__(self, supabase: SupabaseClient) -> None:
        self._db = supabase

    async def get_all_active_tasks(self) -> list[dict]:
        return await self._db.select(
            "agent_tasks",
            filters={"status": "running"},
        )

    async def get_workflow_status(self, workflow_id: UUID) -> dict:
        tasks = await self._db.select(
            "agent_tasks",
            filters={"workflow_id": str(workflow_id)},
        )
        total = len(tasks)
        by_status: dict[str, int] = {}
        for t in tasks:
            status = t.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "workflow_id": str(workflow_id),
            "total_tasks": total,
            "by_status": by_status,
            "tasks": tasks,
        }

    async def get_task_timeline(self, task_id: UUID) -> list[dict]:
        return await self._db.select(
            "context_messages",
            filters={"task_id": str(task_id)},
        )
