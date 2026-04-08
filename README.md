# zeke

A stateless CLI for personal knowledge management. Notes are plain Markdown files with YAML frontmatter stored in a flat directory. No database, no sync daemon — every command reads what it needs and exits.

## System requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)
- [ripgrep](https://github.com/BurntSushi/ripgrep) (`apt install ripgrep` / `brew install ripgrep`)

## Installation

```bash
git clone <repo>
cd zeke
uv sync
```

The `zeke` command is available via `uv run zeke` or after activating the virtualenv.

## Configuration

Optional config file at `~/.config/zeke/config.toml`:

```toml
[notes]
dir = "/path/to/notes"       # default: ~/notes
id_length = 6                # default: 6
types = ["contact", "book"]  # user-defined note types (optional)
```

Missing config is silently ignored and defaults apply.

## Usage

```bash
zeke new --title "Graph Theory"          # create a note
zeke new --title "Graph Theory" --type contact
zeke open a1b2c3                         # print path of note by ID or slug
zeke journal                             # today's journal note
zeke journal 2026-04-07                  # specific date

zeke list                                # all notes (one absolute path per line)
zeke list --type note
zeke list --tag knowledge-management

zeke search "zettelkasten"               # full-text search via ripgrep
zeke backlinks a1b2c3                    # notes that link to this note
zeke orphans                             # notes with no incoming or outgoing links
zeke broken                              # notes containing broken links
zeke broken a1b2c3                       # broken links inside a specific note

zeke rename a1b2c3 "New Title"           # rename note and update all links
zeke tags                                # all tags, alphabetical
zeke tags --count                        # tags with usage count

zeke attach /tmp/screenshot.png          # copy image to notes/assets/, print path
```

All list-style commands print one absolute path per line — composable with shell tools:

```bash
zeke search "graph theory" | xargs nvim
zeke backlinks a1b2c3 | fzf
nvim $(zeke open a1b2c3)
```

## Note format

Filename: `{id}--{slug}.md` (e.g. `a1b2c3--graph-theory.md`)

```markdown
---
id: a1b2c3
type: note
title: Graph Theory
tags: [mathematics, cs]
created: 2026-04-07
---

Note body. Links use standard Markdown: [Another Note](b4c5d6--another-note.md)
```

## Development

```bash
uv sync
uv run pytest
ln -s ../../.claude/hooks/pre-push .git/hooks/pre-push  # optional doc-check hook
```
