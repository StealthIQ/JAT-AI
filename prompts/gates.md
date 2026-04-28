# Quality Gates

You MUST follow these gates during execution. Violations cause task failure.

## Pre-flight
Before starting work, verify:
- The branch exists and is checked out
- You understand the full scope of the task
- You have access to all files mentioned in the task

## Completion
Before marking work as done:
- All changes compile without errors
- Lint passes with zero new warnings
- If tests exist, they pass
- No unrelated files were modified
- Commit message follows: feat|fix|refactor(scope): description

## Scope
- Implement EXACTLY what was asked. No more, no less.
- Do NOT add features, abstractions, or "nice to haves" beyond the task.
- Do NOT simplify or reduce scope. If the task says "implement X with Y", deliver X with Y.
- If the task is too large for one session, say so explicitly instead of delivering partial work.

## Failure Reporting
If you cannot complete the task:
- State what blocked you (missing dependency, ambiguous requirement, access issue)
- State what you DID complete
- Do NOT silently skip parts of the task
