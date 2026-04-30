# Dead Code Audit — JAT-AI Dashboard

Generated: April 30, 2026

## Files Safe to Delete (~3,500 lines)

### Terminal/PTY System (not used — JAT-AI uses Jules API, not local PTY)
1. `src/components/Terminal.tsx` — xterm.js terminal emulator with WebSocket
2. `src/components/TerminalPromptPicker.tsx` — prompt injection into terminal sessions
3. `src/components/terminalReplay.ts` — replays terminal history
4. `src/components/terminalWheel.ts` — mouse wheel scrolling in terminal
5. `src/components/canvas/CanvasTerminalColumn.tsx` — renders terminal in canvas
6. `src/components/canvas/DeleteAllTerminalsDialog.tsx` — bulk delete terminals
7. `src/components/DeleteTentacleDialog.tsx` — delete terminal dialog
8. `src/components/TentacleGitActionsDialog.tsx` — git actions on terminals
9. `src/styles/terminal-and-status.css` — xterm.js terminal styles

### Terminal Hooks (only serve terminal functionality)
10. `src/app/hooks/useTerminalMutations.ts` — terminal CRUD operations
11. `src/app/hooks/useTerminalStateReconciliation.ts` — terminal state sync
12. `src/app/hooks/useTerminalCompletionNotification.ts` — sound on completion
13. `src/app/hooks/useInitialColumnsHydration.ts` — loads terminal columns

### Terminal Runtime
14. `src/app/terminalRuntimeStateStore.ts` — runtime state for local PTY
15. `src/app/notificationSounds.ts` — sound notifications
16. `src/runtime/HttpTerminalSnapshotReader.ts` — reads terminal snapshots

### Code Intel (not used in JAT-AI)
17. `src/components/CodeIntelPrimaryView.tsx` — code edit frequency view
18. `src/components/CodeIntelArcDiagram.tsx` — arc diagram visualization
19. `src/components/CodeIntelTreemap.tsx` — treemap visualization
20. `src/app/hooks/useCodeIntelRuntime.ts` — code intel data fetching
21. `src/app/codeIntelAggregation.ts` — code intel data aggregation

## Refactoring Needed (don't delete, but clean up)

### App.tsx
- Remove WebSocket connection at line 197 (buildTerminalEventsSocketUrl)
- Remove terminal-related hook calls
- Remove terminal state store usage

### runtimeEndpoints.ts
- Remove: buildTerminalEventsSocketUrl, buildTerminalSocketUrl
- Remove: buildTerminalSnapshotsUrl, buildTentacleRenameUrl
- Remove: all buildTentacleGit* functions (6 functions)
- Remove: buildDeckTodo* functions (5 functions)

### constants.ts
- Remove "Code Intel" from PRIMARY_NAV_ITEMS

### types.ts
- Remove: TerminalView, TerminalWorkspaceMode, TerminalAgentProvider
- Remove: TerminalRuntimeStateInfo, AgentRuntimeState

## Active Views (safe, no terminal dependency)
- Canvas ([1]) — uses graph nodes, not terminal columns
- Deck ([2]) — uses tentacle pods (repurposed as repos)
- Activity ([3]) — Supabase data
- Monitor ([5]) — Supabase data
- Conversations ([6]) — Supabase data
- Prompts ([7]) — Supabase data
- Settings ([8]) — config only
- APIs ([9]) — provider management
