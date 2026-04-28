# Environment Context

Current execution environment for this session.

Plan: {plan_tier}
Daily tasks used: {daily_used}/{daily_limit}
Concurrent sessions: {concurrent_used}/{concurrent_limit}
Account: {account_name}

## Constraints
- Do not create files larger than 500 lines
- Do not modify more than 10 files in a single session
- If the task requires more than 10 file changes, state that it needs to be split
- Commit frequently — do not accumulate a large uncommitted diff
