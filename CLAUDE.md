# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`zeke` — a stateless Python CLI for personal knowledge management. Notes are plain Markdown files with YAML frontmatter; the CLI is the only layer that manages IDs, links, and search. No database, no daemon.

Design plan: `docs/zk-claude-initial-plan.md`

## Tech Stack

- **Python ≥ 3.12**, managed with **uv**
- **typer** — CLI framework
- **python-frontmatter** — YAML frontmatter parsing/writing
- **rich** — terminal output
- **tomllib** — config parsing (stdlib, no extra dep)
- **ripgrep (`rg`)** — full-text search via subprocess; must be installed on the system (`apt install ripgrep` / `brew install ripgrep`). If `rg` is not found, `zeke search` should exit 1 with a clear error.
- **pytest** — testing

## Development Commands

```bash
uv sync                   # install dependencies (including dev)
uv run zeke --help        # verify CLI is wired up
uv run pytest             # run all tests
uv run pytest tests/test_notes.py::test_new_note   # run a single test
uv run ruff check .       # lint
uv run ruff check --fix . # lint + auto-fix
uv run ruff format .      # format
uv run mypy zeke/         # type check
```

## Git Hooks

Install the pre-push doc-check hook (one-time setup):

```bash
ln -s ../../.claude/hooks/pre-push .git/hooks/pre-push
```

The hook warns (but never blocks) if Python files changed without a corresponding CLAUDE.md update. Skip with `git push --no-verify`.

## Package Structure

| File | Responsibility |
|------|---------------|
| `zeke/cli.py` | Typer app, all command definitions |
| `zeke/config.py` | Load `~/.config/zeke/config.toml`; exports `Config` dataclass and `DEFAULT_CONFIG` string |
| `examples/config.toml` | Commented example config for repo reference (mirrors `DEFAULT_CONFIG`) |
| `zeke/ids.py` | `generate_id()` with collision check across notes/ and assets/ |
| `zeke/notes.py` | Note creation, frontmatter schema, `zeke attach` |
| `zeke/links.py` | Markdown link parsing, backlinks, orphans, broken links, rename, tags |
| `zeke/search.py` | Full-text search via `rg` subprocess |

## Architecture

**Stateless.** Every command reads files fresh and exits. No index, no cache.

**Output contract.** All list-style commands (`list`, `search`, `backlinks`, `orphans`, `broken` without args) print **one absolute path per line** to stdout. This enables shell composition (`zeke search "foo" | xargs nvim`, `zeke backlinks id | fzf`). Errors go to stderr; exit 1 on failure.

**No editor.** `zeke new`, `zeke open`, and `zeke journal` print the resolved file path and exit. The caller decides what to do with it.

**Scan scope.** All commands scan `notes_dir/*.md` — top-level only, no recursion. `assets/` and any subdirectory are ignored.

**Config path.** Always `~/.config/zeke/config.toml`, regardless of CWD. Missing file → silently use defaults. Non-existent `notes_dir` → hard error on every command.

## Note Schema

**Filename:** `{id}--{slug}.md` — double hyphen is the block separator.

**ID:** 6-char random lowercase alphanumeric (e.g. `a1b2c3`). Generated with collision check; `ids.py` scans both `notes/` and `assets/`.

**Slug:** derived from title via `slugify()` in `notes.py`. Slugs are guaranteed to never contain `--` (consecutive hyphens are collapsed), keeping the separator unambiguous.

**Frontmatter fields:** `id`, `type`, `title`, `tags`, `created`. No `modified` (git is authoritative), no `short-name`.

## Key Behavioural Rules

**Type validation** (`zeke new`, `zeke list`): valid types are `note`, `journal`, plus whatever is in `config.types`. `note` and `journal` in `config.types` → startup config error. Invalid type arg → exit 1 listing all valid types.

**Duplicate detection** (`zeke new`): slug-only match, type-agnostic. If any existing note has the same slug, print its path and exit without creating.

**`zeke journal`** only accepts `YYYY-MM-DD`. Any other format or invalid calendar value → exit 1. Human-readable title in frontmatter ("5 April 2026"); filename/slug use the date string as-is.

**Link format:** `[Title](a1b2c3--slug.md)` — standard Markdown links with a relative path matching the literal filename. CLI commands (`zeke open`, `zeke backlinks`, etc.) still accept an `id-or-slug` argument for resolution; the link format itself uses the full filename.

**`zeke rename`** flow: resolve note → derive new slug → check no slug collision → rename file → update `title:` frontmatter → rewrite `(a1b2c3--old-slug.md)` link paths across all notes. Display text `[Title]` is not auto-updated (user-controlled).

**`zeke open` / first arg of `zeke rename`**: 0 matches → exit 1 with message to stderr; multiple matches → exit 1 + list all candidates to stderr.

**`zeke broken` (no args):** lists notes containing at least one broken Markdown link — one path per line. **`zeke broken <id-or-slug>`:** lists the broken link paths (e.g. `a1b2c3--missing.md`) inside that specific note, one per line; exit 0 with empty output if all links valid.

**`zeke attach`:** copies image to `notes/assets/{image-ID}--{original_name}`. Prints relative path (`assets/…`). Auto-creates `assets/` if missing. Does not modify any note body.

**`zeke config init`:** writes `DEFAULT_CONFIG` from `zeke/config.py` to `~/.config/zeke/config.toml`. Creates parent directory if needed. Exits 1 if the file already exists (no silent overwrites). Does not call `load_config()` — safe to run before any config exists.
