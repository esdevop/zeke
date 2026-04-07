---
name: add-tests
description: Generate pytest tests for code added or changed in the current branch that lacks test coverage. Reads existing tests for conventions before writing new ones.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash(git diff*)
  - Bash(git log*)
  - Bash(git rev-parse*)
  - Bash(uv run pytest*)
---

# /add-tests — Add Missing Tests

Generate pytest tests for uncovered code in the current branch.

## Process

1. **Find changed code** — get the diff of new/modified Python files in the current branch vs main:
   ```
   git diff main...HEAD -- 'zeke/*.py'
   ```

2. **Find existing tests** — read `tests/` to understand naming conventions, fixture patterns, and how the project stubs out filesystem and config. Match those patterns exactly.

3. **Identify gaps** — for each added/modified function or class, check whether a corresponding test already exists. Only write tests for uncovered cases.

4. **Write tests** — add to the appropriate existing test file (e.g. changes to `zeke/notes.py` → `tests/test_notes.py`). Create the file if it does not exist.

## Conventions for this project

- Tests use `tmp_path` (pytest built-in) to create throwaway note directories — never touch `~/notes` or any real notes dir
- Config is injected directly (no `~/.config/zeke/config.toml` on disk during tests)
- Each test is self-contained; no shared mutable state between tests
- Test function names: `test_<command>_<scenario>` (e.g. `test_new_duplicate_slug`, `test_journal_invalid_date`)
- Use `subprocess` or Typer's `CliRunner` to test CLI commands end-to-end where practical

## Output

Write the tests directly to the appropriate file(s), then report what was added:
```
Added 4 tests to tests/test_notes.py
  - test_new_empty_slug_error
  - test_new_duplicate_slug_returns_existing_path
  - test_new_invalid_type_exits_1
  - test_new_creates_correct_frontmatter
```

Run `uv run pytest <file>` after writing to confirm the new tests are collected (not necessarily passing if the implementation is not yet complete).
