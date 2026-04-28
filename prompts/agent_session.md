# Agent Session Prompt

You are Agent {agent_index} of {total_agents} working on this repository simultaneously. Each agent works on its own branch and owns specific files.

## Your Assignment

**Title:** {title}
**Branch:** {branch_name}
**Files you own:** {files_scope}

## Task

{description}

## Acceptance Criteria

{acceptance_criteria}

## Parallel Work Rules

- Other agents are working on this repo at the same time on different branches
- ONLY modify files in your assigned scope
- Do NOT touch files outside your scope — another agent owns them
- If you need a function/type from another agent's scope, import it but do not modify it
- Write modular code with clean interfaces at scope boundaries
- All your work goes on branch: {branch_name}

## Quality Standards

- No emojis in code, comments, or commit messages
- Run lint and build before committing
- Write tests for new functionality
- Use existing patterns from the codebase — do not introduce new frameworks
- Commit messages: imperative mood, under 72 chars, no prefixes like "feat:" or "fix:"
- If you encounter errors, web search for solutions before guessing

## Completion

When done:
1. Ensure all tests pass
2. Ensure lint is clean
3. Create a pull request from {branch_name} to main
4. PR title should match your task title
5. PR description should list what was changed and how to verify
