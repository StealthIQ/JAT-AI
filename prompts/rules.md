# Coding Rules

Follow these conventions for all code changes.

## Style
- Match the existing codebase style exactly. Do not introduce new patterns.
- No unnecessary comments. Only explain non-obvious "why" reasoning.
- No emojis in code, comments, commit messages, or PR descriptions.
- Keep functions under 40 lines. Split if larger.
- Keep files under 300 lines. Split if larger.

## Git
- One logical change per commit.
- Commit message format: type(scope): description
- Types: feat, fix, refactor, docs, test, chore
- Do NOT amend existing commits.
- Do NOT force push.

## Testing
- If the project has tests, run them before committing.
- If you add a new function, add a test if a test framework exists.
- Do NOT skip failing tests by deleting them.

## Security
- Never hardcode secrets, tokens, or credentials.
- Use parameterized queries for database operations.
- Validate all user input.
- Do NOT disable security features (CORS, auth, rate limiting) even temporarily.

## Dependencies
- Use exact versions, not ranges.
- Prefer well-known, actively maintained packages.
- Do NOT add dependencies without explicit instruction.
