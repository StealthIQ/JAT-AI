from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from core.account_pool import AccountPool
from core.context_store import ContextStore
from models.workflow import AgentTask, TaskStatus
from models.jules import SessionState

log = structlog.get_logger()

POLL_INTERVAL = 30
SESSION_TIMEOUT = 1800


class AgentCoordinator:
    def __init__(
        self, pool: AccountPool, store: ContextStore
    ) -> None:
        self._pool = pool
        self._store = store
        self._completion_events: dict[UUID, asyncio.Event] = {}

    def _get_or_create_event(self, task_id: UUID) -> asyncio.Event:
        if task_id not in self._completion_events:
            self._completion_events[task_id] = asyncio.Event()
        return self._completion_events[task_id]

    async def wait_for_task(self, task_id: UUID, timeout: float = SESSION_TIMEOUT) -> dict:
        event = self._get_or_create_event(task_id)
        await asyncio.wait_for(event.wait(), timeout=timeout)
        return await self._store.get_task_state(task_id)

    async def wait_for_dependencies(self, task: AgentTask) -> list[dict]:
        if not task.depends_on:
            return []

        results = await asyncio.gather(
            *[self.wait_for_task(dep_id) for dep_id in task.depends_on]
        )
        return list(results)

    async def run_task(self, task: AgentTask) -> AgentTask:
        source = f"sources/github/{task.repo_owner}/{task.repo_name}"
        account = self._pool.acquire(source)
        task.account_id = account.id
        task.status = TaskStatus.WAITING

        try:
            dep_results = await self.wait_for_dependencies(task)
            task.status = TaskStatus.RUNNING

            client = self._pool.get_client(account.id)

            prompt = task.prompt
            if dep_results:
                context_summary = "\n".join(
                    f"- {r.get('prompt', 'task')}: {r.get('status', 'unknown')}, PR: {r.get('pr_url', 'none')}"
                    for r in dep_results
                )
                prompt = f"{task.prompt}\n\nContext from dependencies:\n{context_summary}"

            session = await client.create_session(
                prompt=prompt,
                source=source,
                branch=task.branch,
                title=task.prompt[:80],
            )
            task.session_id = session.id

            task = await self._poll_session(client, task)

        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            log.error("task_failed", task_id=str(task.id), error=str(exc))
        finally:
            self._pool.release(account.id)
            await self._store.save_task_state(task.id, task.model_dump(mode="json"))
            event = self._get_or_create_event(task.id)
            event.set()

        return task

    async def _poll_session(self, client, task: AgentTask) -> AgentTask:
        elapsed = 0
        while elapsed < SESSION_TIMEOUT:
            session = await client.get_session(task.session_id)

            if session.state == SessionState.COMPLETED:
                task.status = TaskStatus.COMPLETED
                for output in session.outputs:
                    if output.pull_request:
                        task.pr_url = output.pull_request.url
                return task

            if session.state == SessionState.FAILED:
                task.status = TaskStatus.FAILED
                task.error = "Jules session failed"
                return task

            terminal = {SessionState.FAILED, SessionState.COMPLETED}
            if session.state in terminal:
                return task

            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

        task.status = TaskStatus.FAILED
        task.error = "Session timed out"
        return task
