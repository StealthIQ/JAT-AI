from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import structlog

log = structlog.get_logger()

MODELS_CACHE_PATH = Path(__file__).parent.parent.parent / ".cache" / "models.json"


class ProviderType(StrEnum):
    CLOUDFLARE = "cloudflare"
    GROQ = "groq"
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


# Verified free tier limits as of April 2026
PROVIDER_LIMITS = {
    ProviderType.CLOUDFLARE: {
        "daily_neurons": 10000,
        "rpm": 0,
        "notes": "10K neurons/day free. Beta models unlimited.",
    },
    ProviderType.GROQ: {
        "models": {
            "llama-3.1-8b-instant": {"rpm": 30, "rpd": 14400, "tpm": 6000, "tpd": 500000},
            "llama-3.3-70b-versatile": {"rpm": 30, "rpd": 1000, "tpm": 12000, "tpd": 100000},
            "llama-4-scout-17b-16e-instruct": {"rpm": 30, "rpd": 1000, "tpm": 30000, "tpd": 500000},
        },
        "notes": "Per-org limits. No credit card needed.",
    },
    ProviderType.GOOGLE: {
        "models": {
            "gemini-2.5-flash": {"rpm": 10, "rpd": 250, "tpm": 250000},
            "gemini-2.5-flash-lite": {"rpm": 30, "rpd": 1000, "tpm": 250000},
            "gemini-1.5-flash": {"rpm": 15, "rpd": 1000, "tpm": 250000},
        },
        "notes": "Per-project limits. Multiple API keys share one quota per project.",
    },
    ProviderType.OPENROUTER: {
        "free_no_credits": {"rpd": 50, "rpm": 20},
        "with_10_credits": {"rpd": 1000, "rpm": 20},
        "notes": "Free models end with :free. $10 deposit unlocks 1000 rpd.",
    },
    ProviderType.OLLAMA: {
        "notes": "Local. No limits. Requires GPU.",
    },
}


class ProviderAccount:
    def __init__(
        self,
        provider_type: ProviderType,
        name: str,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
    ) -> None:
        self.id: UUID = uuid4()
        self.provider_type = provider_type
        self.name = name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or self._default_base_url()
        self.daily_used = 0
        self.total_used = 0
        self.last_reset = datetime.now(timezone.utc)
        self.last_error: str | None = None
        self.enabled = True

    @property
    def limits(self) -> dict:
        provider_info = PROVIDER_LIMITS.get(self.provider_type, {})
        models = provider_info.get("models", {})
        if self.model in models:
            return models[self.model]
        return provider_info

    @property
    def daily_limit(self) -> int:
        lim = self.limits
        return lim.get("rpd", lim.get("daily_neurons", 0))

    @property
    def remaining(self) -> int:
        self._maybe_reset_daily()
        if not self.daily_limit:
            return 999999
        return max(0, self.daily_limit - self.daily_used)

    @property
    def available(self) -> bool:
        return self.enabled and self.remaining > 0

    def status(self) -> dict:
        self._maybe_reset_daily()
        return {
            "id": str(self.id),
            "provider": self.provider_type,
            "name": self.name,
            "model": self.model,
            "daily_used": self.daily_used,
            "daily_limit": self.daily_limit,
            "remaining": self.remaining,
            "total_used": self.total_used,
            "available": self.available,
            "enabled": self.enabled,
            "configured": bool(self.api_key) or self.provider_type == ProviderType.OLLAMA,
            "last_error": self.last_error,
        }

    def _maybe_reset_daily(self) -> None:
        now = datetime.now(timezone.utc)
        if (now - self.last_reset).total_seconds() > 86400:
            self.daily_used = 0
            self.last_reset = now

    def _default_base_url(self) -> str:
        defaults = {
            ProviderType.GROQ: "https://api.groq.com/openai/v1",
            ProviderType.GOOGLE: "https://generativelanguage.googleapis.com/v1beta",
            ProviderType.CLOUDFLARE: "https://api.cloudflare.com/client/v4/accounts",
            ProviderType.OPENROUTER: "https://openrouter.ai/api/v1",
            ProviderType.OLLAMA: "http://localhost:11434",
        }
        return defaults.get(self.provider_type, "")


class AIProviderPool:
    def __init__(self) -> None:
        self._accounts: list[ProviderAccount] = []
        self._client = httpx.AsyncClient(timeout=60.0)

    def add_account(self, account: ProviderAccount) -> None:
        self._accounts.append(account)

    def remove_account(self, account_id: UUID) -> None:
        self._accounts = [a for a in self._accounts if a.id != account_id]

    def list_accounts(self) -> list[dict]:
        return [a.status() for a in self._accounts]

    def get_limits_info(self) -> dict:
        return PROVIDER_LIMITS

    async def list_models(self, account_id: UUID, force_refresh: bool = False) -> list[dict]:
        account = self.get_account(account_id)
        cache_key = f"{account.provider_type}:{account.name}"

        if not force_refresh:
            cached = _read_cache(cache_key)
            if cached is not None:
                return cached

        models = await self._fetch_models(account)
        _write_cache(cache_key, models)
        return models

    async def _fetch_models(self, account: ProviderAccount) -> list[dict]:
        if account.provider_type == ProviderType.OLLAMA:
            return await self._list_ollama_models(account)
        if account.provider_type == ProviderType.GROQ:
            return await self._list_openai_models(account)
        if account.provider_type == ProviderType.OPENROUTER:
            return await self._list_openrouter_models(account)
        if account.provider_type == ProviderType.GOOGLE:
            return await self._list_google_models(account)
        if account.provider_type == ProviderType.CLOUDFLARE:
            return await self._list_cloudflare_models(account)
        return []

    async def _list_ollama_models(self, account: ProviderAccount) -> list[dict]:
        resp = await self._client.get(f"{account.base_url}/api/tags")
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [{"id": m["name"], "name": m["name"], "size": m.get("size")} for m in models]

    async def _list_openai_models(self, account: ProviderAccount) -> list[dict]:
        resp = await self._client.get(
            f"{account.base_url}/models",
            headers={"Authorization": f"Bearer {account.api_key}"},
        )
        resp.raise_for_status()
        models = resp.json().get("data", [])
        return [{"id": m["id"], "name": m["id"], "owned_by": m.get("owned_by")} for m in models]

    async def _list_openrouter_models(self, account: ProviderAccount) -> list[dict]:
        resp = await self._client.get(f"{account.base_url}/models")
        resp.raise_for_status()
        models = resp.json().get("data", [])
        free = [m for m in models if ":free" in m.get("id", "")]
        return [{"id": m["id"], "name": m.get("name", m["id"]), "context_length": m.get("context_length")} for m in free[:50]]

    async def _list_google_models(self, account: ProviderAccount) -> list[dict]:
        resp = await self._client.get(
            f"{account.base_url}/models?key={account.api_key}"
        )
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [{"id": m["name"].replace("models/", ""), "name": m.get("displayName", m["name"])} for m in models]

    async def _list_cloudflare_models(self, account: ProviderAccount) -> list[dict]:
        parts = account.api_key.split(":", 1)
        if len(parts) != 2:
            return []
        cf_account_id, token = parts
        resp = await self._client.get(
            f"{account.base_url}/{cf_account_id}/ai/models/search",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        models = resp.json().get("result", [])
        return [{"id": m["name"], "name": m.get("description", m["name"]), "task": m.get("task")} for m in models[:50]]

    def get_account(self, account_id: UUID) -> ProviderAccount:
        for a in self._accounts:
            if a.id == account_id:
                return a
        raise ValueError(f"Account {account_id} not found")

    def find_by_name(self, name: str) -> ProviderAccount:
        for a in self._accounts:
            if a.name == name:
                return a
        raise ValueError(f"Account '{name}' not found")

    async def complete(
        self, prompt: str, account_id: UUID, system: str = ""
    ) -> str:
        account = self.get_account(account_id)
        if not account.available:
            raise RuntimeError(
                f"{account.name} not available "
                f"({account.daily_used}/{account.daily_limit} used)"
            )
        if account.provider_type != ProviderType.OLLAMA and not account.api_key:
            raise RuntimeError(f"{account.name} not configured (no API key)")

        try:
            result = await self._call(account, prompt, system)
            account.daily_used += 1
            account.total_used += 1
            account.last_error = None
            return result
        except Exception as exc:
            account.last_error = str(exc)
            raise

    async def _call(
        self, account: ProviderAccount, prompt: str, system: str
    ) -> str:
        if account.provider_type == ProviderType.OLLAMA:
            return await self._call_ollama(account, prompt, system)
        if account.provider_type == ProviderType.GOOGLE:
            return await self._call_google(account, prompt, system)
        if account.provider_type == ProviderType.CLOUDFLARE:
            return await self._call_cloudflare(account, prompt, system)
        return await self._call_openai_compat(account, prompt, system)

    async def _call_openai_compat(
        self, account: ProviderAccount, prompt: str, system: str
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = await self._client.post(
            f"{account.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {account.api_key}"},
            json={"model": account.model, "messages": messages, "max_tokens": 2000},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def _call_ollama(
        self, account: ProviderAccount, prompt: str, system: str
    ) -> str:
        resp = await self._client.post(
            f"{account.base_url}/api/generate",
            json={"model": account.model, "prompt": prompt, "system": system, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["response"]

    async def _call_google(
        self, account: ProviderAccount, prompt: str, system: str
    ) -> str:
        url = (
            f"{account.base_url}/models/{account.model}:generateContent"
            f"?key={account.api_key}"
        )
        body: dict = {"contents": [{"parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        resp = await self._client.post(url, json=body)
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if not candidates:
            raise ValueError("No candidates in Google response")
        return candidates[0]["content"]["parts"][0]["text"]

    async def _call_cloudflare(
        self, account: ProviderAccount, prompt: str, system: str
    ) -> str:
        # api_key format: "account_id:token"
        parts = account.api_key.split(":", 1)
        if len(parts) != 2:
            raise ValueError("Cloudflare api_key must be 'account_id:token'")
        cf_account_id, token = parts

        url = f"{account.base_url}/{cf_account_id}/ai/run/{account.model}"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = await self._client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"messages": messages},
        )
        resp.raise_for_status()
        return resp.json()["result"]["response"]

    async def close(self) -> None:
        await self._client.aclose()


# Cache expires after 24 hours
CACHE_TTL_SECONDS = 86400


def _read_cache(key: str) -> list[dict] | None:
    if not MODELS_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(MODELS_CACHE_PATH.read_text(encoding="utf-8"))
        entry = data.get(key)
        if not entry:
            return None
        cached_at = datetime.fromisoformat(entry["cached_at"])
        if (datetime.now(timezone.utc) - cached_at).total_seconds() > CACHE_TTL_SECONDS:
            return None
        return entry["models"]
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def _write_cache(key: str, models: list[dict]) -> None:
    MODELS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if MODELS_CACHE_PATH.exists():
        try:
            data = json.loads(MODELS_CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            data = {}
    data[key] = {
        "models": models,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    MODELS_CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
