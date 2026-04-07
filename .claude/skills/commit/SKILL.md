---
name: commit
description: Generate a Conventional Commits message from staged or unstaged changes and commit. Enforces type, optional scope from zeke modules, and a concise subject line.
user-invocable: true
allowed-tools:
  - Bash(git diff*)
  - Bash(git status*)
  - Bash(git add*)
  - Bash(git commit*)
  - Bash(git log*)
---

# /commit — Conventional Commits message generator

Generate and apply a Conventional Commits message for staged or uncommitted changes.

## Format

```
<type>(<scope>): <subject>

[optional body]
```

**Types:**
- `feat` — new user-facing feature or command
- `fix` — bug fix
- `refactor` — code change with no behaviour change
- `test` — adding or updating tests
- `chore` — tooling, deps, config, CI
- `docs` — documentation only

**Scopes** (optional, use when change is isolated to one module):
- `cli`, `config`, `ids`, `notes`, `links`, `search`

**Subject rules:**
- Lowercase, imperative mood ("add", not "adds" or "added")
- No trailing period
- 72 characters max

**Body** (optional): include when the diff contains non-obvious decisions or behaviour changes. Wrap at 72 characters.

## Process

1. Run `git status` and `git diff` (staged + unstaged) to understand what changed.
2. If nothing is staged, stage all modified tracked files with `git add -u` — but ask first if there are untracked files that might need including.
3. Draft the commit message following the format above.
4. Show the message to the user for confirmation before committing.
5. On confirmation, run `git commit -m "<message>"`.

## Examples

```
feat(notes): add duplicate slug detection in zeke new
fix(links): resolve wikilink matching for short IDs
chore: add ruff and mypy to dev dependencies
test(config): add cases for reserved type names
docs: update CLAUDE.md with ruff commands
refactor(ids): extract collision check into separate function
```
