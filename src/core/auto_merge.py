from __future__ import annotations

import asyncio
from enum import StrEnum

import structlog

from clients.github import GitHubClient
from models.github import CheckConclusion, CheckStatus, MergeResult

log = structlog.get_logger()

CHECK_POLL_INTERVAL = 30
CHECK_TIMEOUT = 600


class MergeStrategy(StrEnum):
    SQUASH = "squash"
    MERGE = "merge"
    REBASE = "rebase"


class AutoMerge:
    def __init__(
        self,
        github: GitHubClient,
        strategy: MergeStrategy = MergeStrategy.SQUASH,
    ) -> None:
        self._github = github
        self._strategy = strategy

    async def merge_when_ready(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_title: str = "",
    ) -> MergeResult:
        pr = await self._github.get_pull_request(owner, repo, pr_number)
        if pr.merged:
            return MergeResult(merged=True, message="Already merged")

        await self._wait_for_checks(owner, repo, pr.head_ref)

        return await self._github.merge_pull_request(
            owner, repo, pr_number,
            merge_method=self._strategy.value,
            commit_title=commit_title,
        )

    async def _wait_for_checks(
        self, owner: str, repo: str, ref: str
    ) -> None:
        elapsed = 0
        while elapsed < CHECK_TIMEOUT:
            checks = await self._github.list_check_runs(owner, repo, ref)

            if not checks:
                return

            all_done = all(c.status == CheckStatus.COMPLETED for c in checks)
            if all_done:
                failures = [
                    c for c in checks
                    if c.conclusion not in (CheckConclusion.SUCCESS, CheckConclusion.SKIPPED, CheckConclusion.NEUTRAL)
                ]
                if failures:
                    names = ", ".join(c.name for c in failures)
                    log.warning("checks_failed", pr_ref=ref, failed=names)
                return

            await asyncio.sleep(CHECK_POLL_INTERVAL)
            elapsed += CHECK_POLL_INTERVAL

        log.warning("checks_timed_out", pr_ref=ref)
