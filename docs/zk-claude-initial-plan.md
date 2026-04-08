# ZK Personal Knowledge Management Setup — Design Plan

## Context

Personal knowledge management setup designed for **longevity** (years of use, minimal changes). It is not a single app but a coordinated multi-tool system:

- **NeoVim** — primary desktop editor
- **GitHub** — cloud storage, version control, access control
- **GitHub web (browser)** — mobile access to notes (read + quick drafts, no app needed)
- **Custom Python CLI (`zeke`)** — note creation, linking, search (the "shaping" layer)

The Python CLI is the piece to design and build. It must treat **Markdown files as the source of truth** — portable and readable regardless of whether the app exists. This means:
- The CLI reads files fresh on every command; no persistent database or index
- All state lives inside the `.md` files themselves (frontmatter + Markdown links)
- Any tool (NeoVim, a browser, a future replacement) always sees the same state
- Search shells out to ripgrep — no cache needed

---

## Architecture

```
zeke CLI                ← creates/manages notes, maintains link graph
       ↓
Plain Markdown files    ← single flat directory, YAML frontmatter
       ↓
GitHub repo             ← sync, version control
       ↑
GitHub web (mobile)     ← reads/edits files directly via browser
NeoVim (desktop)        ← edits files directly, calls CLI via shell
```

The CLI is **stateless** — no daemon, no running process, no sync step. Every command starts fresh, reads what it needs, exits.

The CLI **does not open an editor**. `zeke new` and `zeke open` print the resolved file path. The caller (user, shell, future NeoVim integration) decides what to do with it. Editor integration is a separate project.

**Output format:** All list-style commands (`zeke list`, `zeke search`, `zeke backlinks`, `zeke orphans`, `zeke broken`) print **one absolute path per line**. This makes them composable with shell tools and NeoVim integration:
```bash
nvim $(zeke open a1b2c3)
zeke search "graph theory" | xargs nvim
zeke backlinks a1b2c3 | fzf
```

Note: `zeke open a1b2c3` resolves `a1b2c3` against filenames of the form `a1b2c3--{slug}.md`.

---

## Note Schema

### Filename Convention
`{id}--{slug}.md`  
Example: `a1b2c3--zettelkasten-principles.md`

Double hyphen (`--`) is the block separator between ID and slug. This keeps blocks unambiguous and leaves room for future extensions (e.g. `{id}--{type}--{slug}`).

The ID is embedded in the filename, making note identity stable across renames. `zeke rename` rewrites all Markdown link paths automatically — manual file renames without the CLI will leave dangling links (detectable via `zeke broken`).

### Slug Generation
Slugs are derived from titles using the following rules, in order:
1. Lowercase
2. Transliterate accented characters to ASCII equivalents via NFD decomposition (`unicodedata` stdlib — no extra dependencies): `é` → `e`, `ü` → `u`, `ñ` → `n`
3. Replace any character that is not alphanumeric or a hyphen with a hyphen
4. Collapse consecutive hyphens into one
5. Strip leading and trailing hyphens

```python
import unicodedata, re

def slugify(title: str) -> str:
    text = unicodedata.normalize('NFD', title.lower()).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9-]+', '-', text)
    return re.sub(r'-+', '-', text).strip('-')
```

Examples: `"Graph Theory"` → `graph-theory`, `"Résumé"` → `resume`, `"Self-Referential"` → `self-referential`, `"A/B Testing"` → `a-b-testing`

Characters with no ASCII decomposition (e.g. `ø`, `ß`) are dropped silently. Acceptable for a personal English-language tool.

Slugs are guaranteed to never contain consecutive hyphens (`--`) because step 4 collapses them. This keeps `--` unambiguous as a filename block separator.

### YAML Frontmatter (all notes)
```yaml
---
id: a1b2c3
type: note            # journal | note | <user-defined>
title: Zettelkasten Principles
tags: [knowledge-management, note-taking]
created: 2026-04-03
---
```

Fields removed from earlier drafts:
- `short-name` — redundant with the filename slug; keeping them in sync adds complexity for no gain
- `modified` — NeoVim edits bypass the CLI so this field would be stale; git already tracks modification time authoritatively

### Note Types (flat pool — type is a tag, not a folder)
All notes live in the same directory. `type` field in frontmatter distinguishes them.

**Built-in types:**

| Type | Primary key | Notes |
|------|-------------|-------|
| `journal` | date (in title) | Reserved label used by `zeke journal` shortcut |
| `note` | title | General purpose — main ZK workhorse |

The special behavior of `journal` (date format, human-readable title, YYYY-MM-DD enforcement) lives entirely in the `zeke journal` command, not the type itself. `zeke new --type journal --title <any>` is allowed and creates a note with `type: journal` without any date restriction.

**User-defined types** are declared in `config.toml`:
```toml
[notes]
types = ["contact", "literature", "project"]
```
- Behave identically to `note` — no special logic
- Valid as filter values in `zeke list --type <type>`
- `note` and `journal` are reserved names — defining them in config is a startup error
- `types` is optional; defaults to `[]`

**Duplicate detection in `zeke new`:** slug-only match, regardless of type. If any existing note has the same slug, its path is printed and no new file is created.

**Type validation in `zeke new`:** `--type` is validated at runtime against built-ins + config types. Invalid type → exit 1 with error listing all valid types.

### ID Format and Generation
Short random alphanumeric hash, **6 characters**, lowercase.  
Example: `a1b2c3`, `ker6z4`, `xm9p2q`

ID generation is **dedicated functionality** used by both note creation and image attachment:
```python
import random, string

def generate_id(length=6):
    chars = string.ascii_lowercase + string.digits
    while True:
        new_id = ''.join(random.choices(chars, k=length))
        if not id_exists(new_id):   # check notes/ and assets/
            return new_id
```

Collision check is mandatory — the generated ID must not already exist before writing any file.

Note and image IDs are generated from the same pool but **do not technically need to be unique across both spaces** — note links `[Title](a1b2c3--slug.md)` resolve against `.md` files in `notes/`, while image references `![](assets/a1b2c3--screenshot.png)` are direct file paths. The two spaces never intersect at runtime. Scanning both directories during generation is a stylistic/organizational choice, not a technical requirement.

### Link Format
All links are equal — no special "up/down" link types. Directionality is expressed only by placement convention (e.g. parent links at top, child links at bottom), not by syntax.

Links use standard Markdown syntax with a relative path matching the literal filename:

```
[Zettelkasten Principles](a1b2c3--zettelkasten-principles.md)
```

The path in `(...)` is the literal filename — no resolution logic needed in the parser. The `--` separator in the filename keeps IDs and slugs unambiguous.

CLI commands (`zeke open`, `zeke backlinks`, `zeke rename`, etc.) accept an `id-or-slug` argument for resolution against filenames. The link format itself always uses the full filename as the path.

Links are inserted **manually** by the user while editing in NeoVim (e.g. via a fuzzy picker over note titles that inserts the formatted link). The CLI does not auto-insert links into note bodies.

**GitHub web:** Standard Markdown links render as native clickable `<a>` tags — fully navigable on mobile without any special tooling.

---

## Directory Structure

```
notes/
  a1b2c3--zettelkasten-principles.md   # type: note
  b4c5d6--graph-theory.md              # type: note
  c7d8e9--john-doe.md                  # type: contact (user-defined)
  d1e2f3--2026-04-03.md               # type: journal
  assets/
    x9k2m3--screenshot.png              # {image-ID}--{original_name}
    p4q5r6--diagram.png
```

Single flat directory. No subfolders per type — consistent with the flat ZK graph model.

**Note discovery scope:** all commands scan `notes_dir/*.md` — top-level only, no recursion. `assets/` and any other subdirectories are fully ignored by all commands.

---

## Images

Images (e.g. Windows Snipping Tool screenshots) are stored in `notes/assets/` and committed to GitHub.

**Workflow:**
1. User takes screenshot → saved to an intermediate location (e.g. `/tmp/screenshot.png`)
2. `zeke attach /tmp/screenshot.png` — CLI generates a unique `image-ID` and copies the file to `notes/assets/{image-ID}--{original_name}`. The original filename (including extension) is preserved; any image format is supported.
3. CLI prints the path (`assets/x9k2m3--screenshot.png`) — user pastes `![](assets/x9k2m3--screenshot.png)` into the note manually

**Key decisions:**
- Images have their own unique `image-ID` (same generation logic as note IDs) — decoupled from note IDs because one image can be referenced by multiple notes
- The CLI appends nothing to the note body — insertion point is the user's responsibility
- GitHub web renders relative-path images correctly when committed to the repo
- **If the repo grows heavy** (>200MB): migrate to external object storage (Cloudflare R2, free tier 10GB) — reference by URL instead. Files remain the truth; only the image location changes.

---

## Python CLI App

### Tech Stack
- `typer` — CLI framework (clean, type-annotated, auto-generates help)
- `python-frontmatter` — YAML frontmatter parsing/writing
- `pathlib` — file operations
- `rich` — terminal output formatting
- `ripgrep` (via `subprocess`) — full-text search

### Core Commands

```bash
zeke new --title "Graph Theory"
# --type defaults to "note" if omitted
# --type validated against built-ins (note, journal) + config types; invalid → exit 1
# Title slugified; empty slug → exit 1 with error
# If a note with the same slug already exists: print its path, do not create
# Generates ID, creates b4c5d6--graph-theory.md with frontmatter, prints full path

zeke open <id-or-slug>
# Resolves note by partial ID or slug match
# Prints full path → caller opens it
# 0 matches: error to stderr ("No note found matching <query>"), exit 1
# Multiple matches: error + list all candidates (one per line) to stderr, exit 1

zeke journal [YYYY-MM-DD]
# Shortcut for zeke new --type journal --title <date>
# Defaults to today if no date given
# Only accepted format: YYYY-MM-DD — any other string or format exits 1 with error to stderr
# Invalid calendar values (e.g. 2026-13-01) also exit 1
# If that date's journal already exists, prints its path instead of creating
# Frontmatter title: human-readable format ("April 5, 2026")
# Slug and filename use the date string as-is (2026-04-05)

zeke list [--type TYPE] [--tag <tag>]
# Lists matching notes — one absolute path per line
# No flags: lists all notes
# --type validated at runtime; invalid type → exit 1 listing valid types

zeke search <query>
# Full-text search via ripgrep — one absolute path per line (filenames only)
# Restricted to top-level .md files: rg -l --glob '*.md' --max-depth 1 <query> <notes_dir>

zeke backlinks <id-or-slug>
# Notes that link to this note — one absolute path per line

zeke orphans
# Notes with no incoming or outgoing links — one absolute path per line

zeke broken
# Lists all notes containing at least one broken Markdown link — one absolute path per line

zeke broken <id-or-slug>
# Lists broken link paths inside a specific note — one filename per line (e.g. a1b2c3--missing.md)
# Empty output (exit 0) if all links in that note are valid

# Broken links are preserved by design: they signal "something used to be here"
# Deletion is a manual file operation; these commands provide cleanup visibility

zeke rename <id-or-slug> <new-title>
# First argument uses the same partial-match resolution as `zeke open`
# (0 matches → exit 1; multiple matches → exit 1 + list candidates)
# Second argument is always the new title as a string; slug is always derived via slugify()
# Example: zeke rename a1b2c3--graph-theory "Graph Theory Advanced"
# 1. Normalize input → title = "Graph Theory Advanced", slug = graph-theory-advanced
# 1a. Empty slug → exit 1 with error
# 2. Check no other note has slug graph-theory-advanced → if collision, exit 1 with conflicting path
# 3. New filename: a1b2c3--graph-theory-advanced.md  (ID unchanged)
# 4. Update title: field in the note's own frontmatter → "Graph Theory Advanced"
# 5. Rename file
# 6. Rewrite (a1b2c3--graph-theory.md) → (a1b2c3--graph-theory-advanced.md) in Markdown links
#    across all notes; display text [Title] is left untouched (user-controlled)
# Uses lookbehind/lookahead on parentheses — no false positives on plain body text

zeke tags
# Lists all unique tags across all notes — one per line, alphabetical order
# Composable: zeke tags | fzf, zeke list --tag $(zeke tags | fzf)

zeke tags --count
# Lists unique tags with usage count: <tag> <count>, sorted by count descending

zeke attach <image-path>
# Generate image-ID, copy to assets/{image-ID}--{original_name}
# Print path only: assets/{image-ID}--{original_name}
# User wraps it in ![]() manually when pasting into a note
# assets/ directory is auto-created silently on first use if it does not exist
```

`zeke links` (outgoing links) is not implemented — outgoing links are visible by reading the file; the useful direction is backlinks.

`zeke rm` is not implemented — deletion is a manual file operation (`rm notes/a1b2c3--slug.md`). Broken links left behind are intentional; use `zeke broken` to find them.

### Config File (`~/.config/zeke/config.toml`)
Global config, looked up from a fixed path regardless of CWD.

```toml
[notes]
dir = "/path/to/notes"                    # default: ~/notes
id_length = 6                             # default: 6
types = ["contact", "literature"]         # default: [] (optional)
```

- Missing config file is silently ignored — defaults apply
- Defaults: `dir = ~/notes`, `id_length = 6`, `types = []`
- If `types` contains `"note"` or `"journal"` → startup config error (reserved names)
- If the resolved `dir` does not exist, every command fails immediately with:  
  `Notes directory <dir> does not exist. Create it or set dir in ~/.config/zeke/config.toml.`

No `editor` field — the CLI does not open an editor.

---

## Mobile Access (GitHub Web)

- Notes render as standard Markdown in the browser
- Markdown links `[Title](id--slug.md)` render as native clickable `<a>` tags — fully navigable
- Images with relative paths render correctly when committed
- Sufficient for reading and quick edits; full authoring stays on desktop

No GitJournal-specific constraints apply.

---

## NeoVim Integration (deferred — Phase 2)

Initial integration: call `zeke` commands from NeoVim terminal split, capture printed path with `:read !zeke new ...` or similar.

Future: thin Lua plugin that calls the CLI and opens returned paths directly in NeoVim buffers — avoids the nested NeoVim problem entirely.

---

## Files to Create

| File | Purpose |
|------|---------|
| `zeke/cli.py` | Entry point, CLI command definitions (typer) |
| `zeke/notes.py` | Note creation, frontmatter schema, image attachment |
| `zeke/ids.py` | ID generation for notes and images (with collision check) |
| `zeke/links.py` | Markdown link parsing, backlink/orphan/broken detection, rename, tags |
| `zeke/search.py` | Full-text search via ripgrep |
| `zeke/config.py` | Config loading from `~/.config/zeke/config.toml` |
| `pyproject.toml` | Package definition, `zeke` as installable CLI command |

---

## Verification

1. `zeke new --title "Test Note"` → prints path with `type: note` (default); correct frontmatter (no `short-name`, no `modified`)
2. `zeke new --type note --title "Test Note"` → same result (explicit default)
3. `zeke new --title "!!!"` → exits 1, empty slug error
4. `zeke new --title "Test Note"` again → prints existing note path, no new file created (slug dedup)
5. `zeke new --type note --title "Test Note!"` → same slug `test-note` → prints existing note path
6. `zeke new --type journal --title "Test Note"` → same slug as existing note → prints existing note path (type ignored in dedup)
7. `zeke new --type foo` where `foo` not in config → exits 1, lists valid types
8. Config with `types = ["note"]` → startup config error (reserved name)
9. `zeke open a1b2c3` → resolves and prints correct path
10. `zeke open nonexistent` → exits 1, error on stderr: `No note found matching "nonexistent"`
11. `zeke open graph` with multiple matches → exits 1, lists all candidates on stderr
12. `zeke journal` → creates today's journal note or prints existing one; frontmatter title is human-readable ("April 5, 2026")
13. `zeke journal 2026-04-03` → creates or opens journal for that specific date
14. `zeke journal "Graph Theory"` → exits 1, error on stderr (not a valid date)
15. `zeke journal 2026-13-01` → exits 1, error on stderr (invalid calendar value)
16. `zeke list` → lists all notes, one absolute path per line
17. `zeke list --type note` → filtered list
18. `zeke list --type contact` (with `types = ["contact"]` in config) → filtered list
19. `zeke list --type foo` (not configured) → exits 1, lists valid types
20. Open note on GitHub web → renders correctly, title/tags visible; Markdown links are native clickable links
21. Add `[Test Note](a1b2c3--test-note.md)` in a note → `zeke backlinks a1b2c3` returns the source note (one path per line)
22. `zeke search "test"` → returns matching top-level .md notes only (one absolute path per line)
23. `zeke orphans` → new unlinked note appears
24. Delete a note manually → `zeke broken` lists the note(s) containing a Markdown link to the deleted file
25. `zeke broken <id>` → lists only the broken link paths inside that specific note (e.g. `a1b2c3--deleted.md`); empty output + exit 0 if all links valid
26. `zeke rename a1b2c3--test-note "Test Note Advanced"` → filename becomes `a1b2c3--test-note-advanced.md`, frontmatter `title:` updated to "Test Note Advanced", `(a1b2c3--test-note.md)` rewritten to `(a1b2c3--test-note-advanced.md)` across all notes
27. `zeke rename a1b2c3--test-note "!!!"` → exits 1, empty slug error
28. `zeke rename a1b2c3--test-note "Existing Note"` where slug `existing-note` already belongs to another note → exits 1 with conflicting path
29. `zeke tags` → lists all unique tags, one per line, alphabetical order
30. `zeke tags --count` → lists tags with counts, sorted descending
31. `zeke attach /tmp/screenshot.png` → image copied to `assets/{image-ID}--screenshot.png`, path printed (`assets/{image-ID}--screenshot.png`); `assets/` auto-created if missing
32. Commit assets/ to GitHub → image renders on GitHub web
33. Run `zeke` with no `~/.config/zeke/config.toml` → defaults apply (`~/notes`, id_length 6, no custom types)
34. Run `zeke` with `dir` pointing to non-existent directory → clear error message
