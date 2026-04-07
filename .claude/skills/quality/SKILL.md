---
name: quality
description: Audit Python code for quality gaps — missing type hints, docstrings, validation, error handling, and design issues. Run on the current branch diff by default, or the whole codebase if asked.
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff*)
  - Bash(git log*)
  - Bash(git rev-parse*)
---

# /quality — Code Quality Audit

Audit Python code for quality gaps and report findings with file:line references.

## What to check

- **Type hints** — all function parameters and return types annotated; no `Any` unless justified
- **Docstrings** — public functions and classes have a one-line docstring minimum
- **Input validation** — user-facing inputs (CLI args, config values, file paths) validated before use
- **Error handling** — failure modes have clear error messages to stderr and exit 1; no bare `except`
- **Design issues** — functions doing too many things, magic values, inconsistent naming, missing guard clauses

## Scope

If $ARGUMENTS contains `all`, scan the entire `zeke/` package.

Otherwise, default to the current branch diff:
```
git diff main...HEAD -- '*.py'
```
If not on a branch off main, fall back to `git diff HEAD -- '*.py'`.

## Output format

Group findings by file. For each issue:
```
zeke/notes.py:42  [type-hint]  Return type missing on `create_note`
zeke/config.py:15 [validation] `id_length` not checked for positive int
```

Severity levels (prefix each line):
- `[type-hint]` `[docstring]` `[validation]` `[error-handling]` `[design]`

End with a one-line summary: `N issues found across M files.`

If no issues found, say so clearly.
