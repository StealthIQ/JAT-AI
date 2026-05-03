from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from clients.supabase import SupabaseClient
from config import load_settings

router = APIRouter()
settings = load_settings()
db = SupabaseClient(settings.supabase_url, settings.supabase_key)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    provider_type: str
    model: str
    messages: list[ChatMessage]
    system: str = ""
    image_base64: str | None = None
    repo: str | None = None


class ChatResponse(BaseModel):
    response: str
    provider_id: str
    model: str
    tokens_used: int = 0


def _decrypt_key(stored: str) -> str:
    from core.ai_interface import KeyVault
    vault = KeyVault(settings.encryption_key)
    try:
        if stored.startswith("\\x"):
            stored = bytes.fromhex(stored[2:]).decode()
        return vault.decrypt(stored)
    except Exception:
        return stored


async def _get_enabled_keys(provider_type: str) -> list[dict]:
    try:
        rows = await db.select("ai_providers", filters={"provider_type": provider_type, "enabled": True})
    except Exception:
        rows = []
    return rows


def _build_messages(request: ChatRequest) -> list[dict]:
    messages = []
    for msg in request.messages:
        if msg.role == "user" and request.image_base64 and msg == request.messages[-1]:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": msg.content},
                    {"type": "image_url", "image_url": {"url": request.image_base64}},
                ],
            })
        else:
            messages.append({"role": msg.role, "content": msg.content})
    return messages


async def _call_google(api_key: str, model: str, messages: list[dict], system: str) -> str:
    import httpx

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    contents = []
    for m in messages:
        parts = []
        if isinstance(m["content"], list):
            for part in m["content"]:
                if part["type"] == "text":
                    parts.append({"text": part["text"]})
                elif part["type"] == "image_url":
                    data = part["image_url"]["url"]
                    if data.startswith("data:"):
                        mime, b64 = data.split(";base64,", 1)
                        mime = mime.replace("data:", "")
                        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
        else:
            parts.append({"text": m["content"]})
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": parts})

    body: dict = {"contents": contents}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(url, json=body, headers={"Content-Type": "application/json"})
    if res.status_code == 429:
        raise RateLimitError("google")
    if res.status_code != 200:
        raise ProviderError(f"Google API {res.status_code}: {res.text[:200]}")
    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_openai_compat(api_key: str, provider_type: str, model: str, messages: list[dict], system: str) -> str:
    import httpx
    from clients.ai_providers import DEFAULT_BASE_URLS, ProviderType

    pt = ProviderType(provider_type)
    base_url = DEFAULT_BASE_URLS.get(pt, "")
    if not base_url:
        raise ValueError(f"No base URL for provider: {provider_type}")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload: dict = {"model": model, "messages": messages}
    if system:
        payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)

    if res.status_code == 429:
        raise RateLimitError(provider_type)
    if res.status_code != 200:
        raise ProviderError(f"{provider_type} API {res.status_code}: {res.text[:200]}")

    data = res.json()
    return data["choices"][0]["message"]["content"]


async def _call_provider(api_key: str, provider_type: str, model: str, messages: list[dict], system: str) -> str:
    if provider_type == "google":
        return await _call_google(api_key, model, messages, system)
    return await _call_openai_compat(api_key, provider_type, model, messages, system)


class RateLimitError(Exception):
    pass


class ProviderError(Exception):
    pass


REPOMIX_TRIGGERS = {"rrpo", "repomix", "/repomix", "/rrpo"}


def _is_repomix_trigger(messages: list) -> bool:
    if not messages:
        return False
    last = messages[-1]
    content = last.content if hasattr(last, "content") else last.get("content", "")
    return content.strip().lower() in REPOMIX_TRIGGERS


@router.post("/api/chat/send")
async def chat_send(request: ChatRequest):
    if _is_repomix_trigger(request.messages) and request.repo:
        from core.repomix import analyze_repo
        parts = request.repo.split("/", 1)
        if len(parts) == 2:
            token = settings.github_token
            try:
                xml = await analyze_repo(parts[0], parts[1], token)
                summary = f"Repo re-analyzed ({len(xml):,} chars). Fresh codebase context loaded."
                return ChatResponse(response=summary, provider_id="system", model="repomix")
            except Exception as e:
                return ChatResponse(response=f"Repomix failed: {e}", provider_id="system", model="repomix")

    keys = await _get_enabled_keys(request.provider_type)
    if not keys:
        raise HTTPException(400, f"No enabled keys for provider: {request.provider_type}")

    messages = _build_messages(request)
    last_error = ""

    for key_row in keys:
        api_key = _decrypt_key(key_row.get("api_key_encrypted", ""))
        provider_id = str(key_row["id"])
        try:
            response = await _call_provider(
                api_key=api_key,
                provider_type=request.provider_type,
                model=request.model,
                messages=messages,
                system=request.system,
            )
            return ChatResponse(
                response=response,
                provider_id=provider_id,
                model=request.model,
            )
        except RateLimitError:
            last_error = f"Rate limited on key {key_row.get('name', provider_id)}, trying next..."
            continue
        except ProviderError as e:
            last_error = str(e)
            continue
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            continue

    raise HTTPException(429, f"All keys exhausted for {request.provider_type}. Last error: {last_error}")
