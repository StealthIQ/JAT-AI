from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import structlog

from jat.clients.jules import JulesClient
from jat.exceptions import AccountPoolExhausted

log = structlog.get_logger()


@dataclass
class Account:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    api_key: str = ""
    max_concurrent: int = 5
    active_sessions: int = 0
    sources: list[str] = field(default_factory=list)
    enabled: bool = True

    @property
    def has_capacity(self) -> bool:
        return self.enabled and self.active_sessions < self.max_concurrent


class AccountPool:
    def __init__(self) -> None:
        self._accounts: list[Account] = []
        self._clients: dict[UUID, JulesClient] = {}

    def add_account(self, account: Account) -> None:
        self._accounts.append(account)
        self._clients[account.id] = JulesClient(account.api_key)
        log.info("account_added", name=account.name, id=str(account.id))

    def get_client(self, account_id: UUID) -> JulesClient:
        return self._clients[account_id]

    def acquire(self, source: str | None = None) -> Account:
        eligible = [a for a in self._accounts if a.has_capacity]
        if source:
            with_source = [a for a in eligible if source in a.sources]
            if with_source:
                eligible = with_source

        if not eligible:
            raise AccountPoolExhausted("No accounts with available capacity")

        # Least-loaded first
        eligible.sort(key=lambda a: a.active_sessions)
        chosen = eligible[0]
        chosen.active_sessions += 1
        log.info("account_acquired", name=chosen.name, active=chosen.active_sessions)
        return chosen

    def release(self, account_id: UUID) -> None:
        for account in self._accounts:
            if account.id == account_id:
                account.active_sessions = max(0, account.active_sessions - 1)
                log.info("account_released", name=account.name, active=account.active_sessions)
                return

    async def close_all(self) -> None:
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
