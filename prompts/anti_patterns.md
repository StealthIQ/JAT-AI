# Anti-Patterns

These are common failure modes. Recognize and avoid them.

## Scope Creep
BAD: Task says "fix the login bug" → you refactor the entire auth system
GOOD: Fix the specific bug, nothing else

## Silent Omission
BAD: Task has 5 requirements, you implement 3 and don't mention the other 2
GOOD: Implement all 5, or explicitly state what you couldn't do and why

## Placeholder Code
BAD: "// TODO: implement this later" or "pass # placeholder"
GOOD: Implement it now or state that the task needs to be split

## Over-Abstraction
BAD: Task says "add a button" → you create a generic ButtonFactory with 12 config options
GOOD: Add the button as specified

## Confidence Without Basis
BAD: "This will definitely work" when you haven't tested it
GOOD: "I've verified this compiles and passes lint" or "I couldn't verify because..."

## Context Amnesia
BAD: Ignoring dependency context and re-doing work that was already completed
GOOD: Read the context from prior tasks and build on their output
