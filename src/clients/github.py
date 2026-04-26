from __future__ import annotations

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from exceptions import GitHubApiError
from models.github import CheckRun, MergeResult, PullRequest

log = structlog.get_logger()

GITHUB_API_URL = "https://api.github.com"
DEFAULT_TIMEOUT = 30.0


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, GitHubApiError) and exc.is_retryable


_retry = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
)


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_URL,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=DEFAULT_TIMEOUT,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _raise_on_error(self, response: httpx.Response) -> None:
        self._check_rate_limit(response)
        if response.status_code >= 400:
            raise GitHubApiError(response.status_code, response.text)

    def _check_rate_limit(self, response: httpx.Response) -> None:
        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining is not None and int(remaining) < 10:
            reset = response.headers.get("x-ratelimit-reset", "unknown")
            log.warning("rate_limit_low", remaining=remaining, reset_at=reset)

    @_retry
    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> PullRequest:
        response = await self._client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}"
        )
        self._raise_on_error(response)
        data = response.json()
        return PullRequest(
            number=data["number"],
            title=data.get("title", ""),
            state=data.get("state", ""),
            html_url=data.get("html_url", ""),
            head_ref=data.get("head", {}).get("ref", ""),
            base_ref=data.get("base", {}).get("ref", ""),
            mergeable=data.get("mergeable"),
            merged=data.get("merged", False),
        )

    @_retry
    async def list_check_runs(
        self, owner: str, repo: str, ref: str
    ) -> list[CheckRun]:
        response = await self._client.get(
            f"/repos/{owner}/{repo}/commits/{ref}/check-runs"
        )
        self._raise_on_error(response)
        data = response.json()
        return [
            CheckRun(
                id=cr["id"],
                name=cr.get("name", ""),
                status=cr.get("status", "queued"),
                conclusion=cr.get("conclusion"),
            )
            for cr in data.get("check_runs", [])
        ]

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        merge_method: str = "squash",
        commit_title: str = "",
    ) -> MergeResult:
        payload: dict = {"merge_method": merge_method}
        if commit_title:
            payload["commit_title"] = commit_title

        response = await self._client.put(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
            json=payload,
        )
        self._raise_on_error(response)
        data = response.json()
        return MergeResult(
            sha=data.get("sha", ""),
            merged=data.get("merged", False),
            message=data.get("message", ""),
        )

    @_retry
    async def list_pr_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict]:
        response = await self._client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        )
        self._raise_on_error(response)
        return response.json()

    async def create_repo(
        self,
        name: str,
        private: bool = True,
        description: str = "",
        auto_init: bool = True,
    ) -> dict:
        payload: dict = {
            "name": name,
            "private": private,
            "auto_init": auto_init,
        }
        if description:
            payload["description"] = description

        response = await self._client.post("/user/repos", json=payload)
        self._raise_on_error(response)
        data = response.json()
        return {
            "id": data["id"],
            "full_name": data["full_name"],
            "owner": data["owner"]["login"],
            "name": data["name"],
            "html_url": data["html_url"],
            "private": data["private"],
            "default_branch": data.get("default_branch", "main"),
            "source": f"sources/github/{data['owner']['login']}/{data['name']}",
        }
