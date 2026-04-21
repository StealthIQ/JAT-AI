# JAT-AI — Jules Agent Tree

A distributed orchestrator for Google Jules AI coding agent. Manages multiple Jules accounts, coordinates async agent workflows, persists context memory in Supabase, and auto-merges pull requests.

## What It Does

JAT-AI treats Jules sessions as nodes in a workflow tree. A parent task can spawn child tasks that run in parallel across different Jules accounts. Children share context through a central Supabase store. When a child finishes and creates a PR, the orchestrator can automatically merge it after CI passes. Other agents waiting on that result get notified and continue their work.

This is not a wrapper around the Jules API. It is a coordination engine for running multiple Jules agents simultaneously, with shared memory and dependency resolution.

## Architecture

```
Workflow Definition
    -> Agent Coordinator (spawns agents)
        -> Account Pool (picks best Jules account)
            -> Jules Client (creates session, polls, sends messages)
                -> Supabase (stores context, activities, artifacts)
                    -> Other Agents (subscribe to updates, wait for results)
        -> GitHub API (monitor CI, auto-merge PRs)
```

### Core Components

- **Jules Client** — Async wrapper around the Jules REST API v1alpha. Covers sessions, activities, plans, messages, sources, and deletion. Typed with Pydantic, retries with tenacity.

- **Account Pool** — Manages multiple Jules API keys. Dispatches work to the best available account based on repo access, capacity, and load. Fails over automatically.

- **Context Store** — Supabase-backed persistence for all session state, prompts, plans, activities, artifacts, and inter-agent messages. Agents write here; other agents subscribe via Realtime or poll.

- **Agent Coordinator** — Async engine where each agent is a task running a Jules session. Agents declare dependencies, publish results, subscribe to state changes, and wait on conditions.

- **Workflow Engine** — Executes DAGs of tasks. Parents spawn children, children run concurrently, parents collect results before proceeding.

- **Auto-Merge** — Monitors PRs from Jules, checks CI status via GitHub API, merges when conditions are met. Supports squash, merge, and rebase strategies.

- **Real-Time Tracker** — Supabase Realtime subscriptions provide live updates on agent state transitions, session progress, and PR status changes.

- **MCP Server** — Exposes the full system to external AI agents via Model Context Protocol.

## Tech Stack

- Python 3.11+, fully async
- httpx for HTTP (Jules API, GitHub API)
- Pydantic v2 for data models
- supabase-py for database and Realtime
- tenacity for retry logic
- structlog for structured logging
- MCP Python SDK for the MCP server

## Project Structure

```
src/jules_orchestrator/
    __init__.py
    cli.py                  # CLI entry point
    config.py               # Settings via pydantic-settings
    models/
        __init__.py
        jules.py            # Jules API types
        workflow.py         # Workflow and agent task models
        github.py           # GitHub PR and check models
    clients/
        __init__.py
        jules.py            # Async Jules API client
        github.py           # Async GitHub API client
        supabase.py         # Supabase client wrapper
    core/
        __init__.py
        account_pool.py     # Multi-account management
        coordinator.py      # Agent coordination engine
        workflow_engine.py  # Workflow tree execution
        context_store.py    # Context memory via Supabase
        auto_merge.py       # PR monitoring and merge logic
        tracker.py          # Real-time agent tracking
    mcp/
        __init__.py
        server.py           # MCP server
tests/
```

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/iceyxsm/JAT-AI.git
   cd JAT-AI
   ```

2. Create a virtual environment and install:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -e ".[dev]"
   ```

3. Copy the environment template and fill in your keys:
   ```bash
   cp jules-orchestrator/.env.example .env
   ```

4. Set up Supabase tables (schema migration scripts in `migrations/`).

5. Run the CLI:
   ```bash
   jules --help
   ```

## Configuration

All configuration is via environment variables or a `.env` file:

| Variable | Required | Description |
|----------|----------|-------------|
| JULES_API_KEY | Yes | At least one Jules API key. For multiple accounts, configure via the account pool. |
| GITHUB_TOKEN | Yes | GitHub PAT with repo scope and merge permissions. |
| SUPABASE_URL | Yes | Your Supabase project URL. |
| SUPABASE_KEY | Yes | Supabase service role key (for server-side access). |
| LOG_LEVEL | No | DEBUG, INFO, WARNING, ERROR. Defaults to INFO. |

## Roadmap

### Phase 1 — Foundation
- [ ] Supabase schema design and migration scripts
- [ ] Pydantic models for Jules API types (Session, Activity, Plan, Source, Artifact)
- [ ] Pydantic models for workflow types (WorkflowTask, AgentResult, Dependency)
- [ ] Pydantic models for GitHub types (PullRequest, CheckRun, MergeResult)
- [ ] Application config via pydantic-settings
- [ ] Async Jules API client (full coverage: sessions CRUD, sendMessage, approvePlan, activities, sources)
- [ ] Async GitHub API client (PRs: get, list, merge; checks: list status)
- [ ] Supabase client wrapper (CRUD for all tables, Realtime subscriptions)

### Phase 2 — Multi-Account and Context
- [ ] Account pool with smart dispatching (repo access, capacity, load balancing)
- [ ] Account failover logic
- [ ] Context store: write session state, read context, query history
- [ ] Inter-agent messaging via Supabase (publish/subscribe pattern)
- [ ] Agent dependency resolution (wait for another agent's result)

### Phase 3 — Workflow Engine
- [ ] Workflow tree definition and validation
- [ ] DAG execution engine (parallel children, sequential phases)
- [ ] Context propagation from parent to child and child to parent
- [ ] Workflow state persistence and recovery (resume after crash)

### Phase 4 — Auto-Merge and Tracking
- [ ] PR monitoring (poll for CI status)
- [ ] Auto-merge with configurable strategy (squash, merge, rebase)
- [ ] Configurable merge gates (require CI green, optional reviewer approval, delay)
- [ ] Real-time agent tracker via Supabase Realtime
- [ ] Live status dashboard data (agent states, session progress, PR pipeline)

### Phase 5 — MCP Server
- [ ] MCP server exposing session management tools
- [ ] MCP tools for workflow creation and monitoring
- [ ] MCP tools for account pool management
- [ ] MCP tools for context store queries

### Phase 6 — Hardening
- [ ] Comprehensive test suite (unit + integration with mocked APIs)
- [ ] API key encryption at rest in Supabase
- [ ] Rate limit detection and backoff per account
- [ ] Graceful shutdown and cleanup of active sessions
- [ ] CLI with all operations (create workflow, list agents, check status, force merge)

## License

MIT
