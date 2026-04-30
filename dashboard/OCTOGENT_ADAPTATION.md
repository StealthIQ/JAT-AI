# Octogent → JAT-AI UI Adaptation Plan

UI from [Octogent](https://github.com/hesamsheikh/octogent) by Hesam Sheikh (MIT License).

## Approach

Keep Octogent's UI exactly as-is. Change NOTHING in the frontend components. Only change the mock API server to return our Supabase data in the exact shapes Octogent's frontend expects.

## Concept Mapping (data only, UI stays the same)

| Octogent Concept | JAT-AI Data Source | Notes |
|---|---|---|
| Terminal | agent_tasks row | Each task = one "terminal" card |
| Tentacle | workflow | Each workflow = one tentacle pod |
| Tentacle todo items | agent_tasks in workflow | Tasks within a workflow = todo items |
| Agent state (live/idle/exited) | Task status (running/completed/failed) | Map status strings |
| Conversation session | Jules session | Group activities by session_id |
| Conversation turn | session_activity | Each activity = one turn |
| Monitor feed | Supabase Realtime stream | Live activity inserts |
| Claude usage | Jules account pool stats | Daily used / daily limit |
| GitHub summary | GitHub API via our client | Repo stats |
| Prompts | Workflow JSON templates | Files in examples/ |
| UI state | Local storage | Persisted in browser |

## What Changes

ONLY the mock API server (api-mock.mjs). It translates our Supabase data into Octogent's expected response shapes.

## What Does NOT Change

- All React components
- All hooks
- All styles/CSS
- All core domain types
- The canvas graph (d3-force)
- The tentacle pods
- The terminal cards
- The sidebar
- The status strip
- The telemetry tape
- The octopus glyph
- Everything visual

## Mock API — Implementation Status

| Endpoint | Octogent Shape | JAT-AI Source | Status |
|---|---|---|---|
| GET /api/terminal-snapshots | {terminals: TerminalSnapshot[]} | agent_tasks → mapped | DONE |
| GET /api/terminals | TerminalSnapshot[] | agent_tasks → mapped | DONE |
| GET /api/deck/tentacles | DeckTentacleSummary[] | workflows → mapped | DONE |
| GET /api/conversations | {sessions: ConversationSessionSummary[]} | session_activities grouped | DONE |
| GET /api/ui-state | UiState | Static defaults | DONE |
| GET /api/setup | WorkspaceSetupSnapshot | Static (no setup) | DONE |
| GET /api/claude/usage | ClaudeUsageSnapshot | Static | TODO — wire to account pool |
| GET /api/prompts | {prompts: PromptLibraryEntry[]} | Static empty | TODO — wire to examples/*.json |
| GET /api/code-intel/events | {events: []} | Static empty | DONE (view shows empty) |
| GET /api/monitor/feed | MonitorFeedSnapshot | Static empty | TODO — wire to Realtime |
| GET /api/monitor/config | MonitorConfigSnapshot | Static | DONE |
| GET /api/analytics/usage-heatmap | {days: []} | Static empty | TODO — wire to daily usage |
| GET /api/github/summary | null | TODO — wire to GitHub API | TODO |
| GET /api/codex/usage | null | Static | DONE |
| GET /api/deck/skills | [] | Static | DONE |
| POST /api/terminals | Create terminal | TODO — create Jules session | TODO |
| WS /api/terminal-events/ws | Terminal events | TODO — Supabase Realtime | TODO |

## Execution Order

1. Get mock API running (kill port 8787, start api-mock.mjs)
2. Fix any remaining response shape crashes
3. Wire /api/claude/usage to Jules account pool stats
4. Wire /api/prompts to workflow templates from examples/
5. Wire /api/github/summary to our GitHub client
6. Wire /api/analytics/usage-heatmap to daily task counts
7. Wire POST /api/terminals to create Jules sessions
8. Wire WebSocket for live terminal events via Supabase Realtime
9. Wire /api/monitor/feed to Supabase activity stream
