from __future__ import annotations

from typing import Callable
from uuid import UUID

import structlog

from clients.supabase import SupabaseClient

log = structlog.get_logger()


class Tracker:
    def __init__(self, supabase: SupabaseClient) -> None:
        self._db = supabase
        self._channels: list = []

    async def get_active_tasks(self) -> list[dict]:
        return await self._db.select(
            "agent_tasks",
            filters={"status": "running"},
        )

    async def get_workflow_status(self, workflow_id: UUID) -> dict:
        tasks = await self._db.select(
            "agent_tasks",
            filters={"workflow_id": str(workflow_id)},
        )
        by_status: dict[str, int] = {}
        for t in tasks:
            status = t.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "workflow_id": str(workflow_id),
            "total_tasks": len(tasks),
            "by_status": by_status,
            "tasks": tasks,
        }

    async def subscribe_task_updates(
        self, callback: Callable[[dict], None]
    ) -> None:
        channel = self._db.client.channel("task-updates")
        channel.on_postgres_changes(
            "*",
            schema="public",
            table="agent_tasks",
            callback=callback,
        )
        await channel.subscribe()
        self._channels.append(channel)
        log.info("subscribed", table="agent_tasks")

    async def subscribe_activity_updates(
        self, callback: Callable[[dict], None]
    ) -> None:
        channel = self._db.client.channel("activity-updates")
        channel.on_postgres_changes(
            "INSERT",
            schema="public",
            table="session_activities",
            callback=callback,
        )
        await channel.subscribe()
        self._channels.append(channel)
        log.info("subscribed", table="session_activities")

    async def subscribe_workflow_tasks(
        self, workflow_id: UUID, callback: Callable[[dict], None]
    ) -> None:
        channel = self._db.client.channel(f"workflow-{workflow_id}")
        channel.on_postgres_changes(
            "*",
            schema="public",
            table="agent_tasks",
            filter=f"workflow_id=eq.{workflow_id}",
            callback=callback,
        )
        await channel.subscribe()
        self._channels.append(channel)
        log.info("subscribed", table="agent_tasks", workflow_id=str(workflow_id))

    async def unsubscribe_all(self) -> None:
        for channel in self._channels:
            await self._db.client.remove_channel(channel)
        self._channels.clear()
        log.info("unsubscribed_all")
