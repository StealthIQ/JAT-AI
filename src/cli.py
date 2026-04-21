from __future__ import annotations

import argparse
import asyncio
import json
import sys

import structlog

from config import load_settings
from clients.jules import JulesClient

log = structlog.get_logger()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JAT - Jules Agent Tree")
    sub = parser.add_subparsers(dest="command")

    list_cmd = sub.add_parser("list-sessions", help="List Jules sessions")
    list_cmd.add_argument("--api-key", help="Jules API key (overrides env)")
    list_cmd.add_argument("--limit", type=int, default=10)

    sources_cmd = sub.add_parser("list-sources", help="List connected sources")
    sources_cmd.add_argument("--api-key", help="Jules API key (overrides env)")

    status_cmd = sub.add_parser("status", help="Get session status")
    status_cmd.add_argument("session_id")
    status_cmd.add_argument("--api-key", help="Jules API key (overrides env)")

    return parser


async def run_list_sessions(api_key: str, limit: int) -> None:
    client = JulesClient(api_key)
    try:
        sessions = await client.list_sessions(page_size=limit)
        for s in sessions:
            print(f"{s.id} | {s.title} | {s.state}")
    finally:
        await client.close()


async def run_list_sources(api_key: str) -> None:
    client = JulesClient(api_key)
    try:
        sources = await client.list_sources()
        for s in sources:
            print(f"{s.name} | {s.id}")
    finally:
        await client.close()


async def run_status(api_key: str, session_id: str) -> None:
    client = JulesClient(api_key)
    try:
        session = await client.get_session(session_id)
        print(json.dumps(session.model_dump(mode="json"), indent=2))
    finally:
        await client.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    settings = load_settings()
    api_key = getattr(args, "api_key", None) or settings.jules_api_key

    if not api_key:
        print("JULES_API_KEY is required. Set it in .env or pass --api-key.")
        sys.exit(1)

    if args.command == "list-sessions":
        asyncio.run(run_list_sessions(api_key, args.limit))
    elif args.command == "list-sources":
        asyncio.run(run_list_sources(api_key))
    elif args.command == "status":
        asyncio.run(run_status(api_key, args.session_id))


if __name__ == "__main__":
    main()
