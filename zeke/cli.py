"""Zeke CLI — stateless personal knowledge management."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Annotated, Optional

import frontmatter
import typer

from zeke.config import Config, load_config
from zeke.links import (
    count_tags,
    extract_tags,
    find_backlinks,
    find_broken_links,
    find_broken_notes,
    find_orphans,
    rewrite_links,
)
from zeke.notes import _find_by_slug, create_journal, create_note, resolve, slugify
from zeke.notes import attach as _attach
from zeke.search import search as _search

app = typer.Typer(help="Stateless CLI for personal knowledge management.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg() -> Config:
    """Load config, exiting 1 on reserved-type errors."""
    try:
        return load_config()
    except ValueError as e:
        typer.echo(f"Config error: {e}", err=True)
        raise typer.Exit(1) from None


def _check_dir(cfg: Config) -> None:
    """Exit 1 if the notes directory does not exist."""
    if not cfg.notes_dir.exists():
        typer.echo(
            f"Notes directory {cfg.notes_dir} does not exist. "
            "Create it or set dir in ~/.config/zeke/config.toml.",
            err=True,
        )
        raise typer.Exit(1) from None


def _valid_types(cfg: Config) -> list[str]:
    """Return all valid note types: built-ins plus user-defined."""
    return ["note", "journal"] + cfg.types


def _validate_type(type_: str, cfg: Config) -> None:
    """Exit 1 if type_ is not a valid note type."""
    valid = _valid_types(cfg)
    if type_ not in valid:
        typer.echo(f"Invalid type {type_!r}. Valid types: {', '.join(valid)}", err=True)
        raise typer.Exit(1) from None


def _resolve_one(query: str, cfg: Config) -> Path:
    """Resolve query to exactly one note path, or exit 1."""
    matches = resolve(query, cfg.notes_dir)
    if not matches:
        typer.echo(f'No note found matching "{query}"', err=True)
        raise typer.Exit(1) from None
    if len(matches) > 1:
        typer.echo("Multiple matches:", err=True)
        for p in matches:
            typer.echo(str(p), err=True)
        raise typer.Exit(1) from None
    return matches[0]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def new(
    title: Annotated[str, typer.Option("--title", help="Note title")],
    type_: Annotated[str, typer.Option("--type", help="Note type")] = "note",
) -> None:
    """Create a new note and print its path."""
    cfg = _cfg()
    _check_dir(cfg)
    _validate_type(type_, cfg)
    try:
        path = create_note(title, type_, cfg)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None
    typer.echo(str(path))


@app.command()
def open(query: Annotated[str, typer.Argument(help="Note ID or slug")]) -> None:
    """Resolve a note by ID or slug and print its path."""
    cfg = _cfg()
    _check_dir(cfg)
    path = _resolve_one(query, cfg)
    typer.echo(str(path))


@app.command()
def journal(
    date: Annotated[Optional[str], typer.Argument(help="Date in YYYY-MM-DD format")] = None,
) -> None:
    """Create or open a journal note for the given date (default: today)."""
    cfg = _cfg()
    _check_dir(cfg)
    date_str = date or datetime.date.today().isoformat()
    try:
        path = create_journal(date_str, cfg)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None
    typer.echo(str(path))


@app.command("list")
def list_(
    type_: Annotated[Optional[str], typer.Option("--type", help="Filter by note type")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag")] = None,
) -> None:
    """List notes, optionally filtered by type and/or tag."""
    cfg = _cfg()
    _check_dir(cfg)
    if type_ is not None:
        _validate_type(type_, cfg)
    for p in sorted(cfg.notes_dir.glob("*.md")):
        if type_ is None and tag is None:
            typer.echo(str(p))
            continue
        post = frontmatter.load(p)
        if type_ is not None and post.get("type") != type_:
            continue
        if tag is not None:
            note_tags = post.get("tags") or []
            if tag not in note_tags:
                continue
        typer.echo(str(p))


@app.command()
def search(query: Annotated[str, typer.Argument(help="Search query")]) -> None:
    """Full-text search notes via ripgrep."""
    cfg = _cfg()
    _check_dir(cfg)
    for p in _search(query, cfg.notes_dir):
        typer.echo(str(p))


@app.command()
def backlinks(query: Annotated[str, typer.Argument(help="Note ID or slug")]) -> None:
    """List notes that link to the given note."""
    cfg = _cfg()
    _check_dir(cfg)
    target = _resolve_one(query, cfg)
    for p in find_backlinks(target, cfg.notes_dir):
        typer.echo(str(p))


@app.command()
def orphans() -> None:
    """List notes with no incoming or outgoing links."""
    cfg = _cfg()
    _check_dir(cfg)
    for p in find_orphans(cfg.notes_dir):
        typer.echo(str(p))


@app.command()
def broken(
    query: Annotated[Optional[str], typer.Argument(help="Note ID or slug")] = None,
) -> None:
    """List notes with broken links, or broken links inside a specific note."""
    cfg = _cfg()
    _check_dir(cfg)
    if query is None:
        for p in find_broken_notes(cfg.notes_dir):
            typer.echo(str(p))
    else:
        note = _resolve_one(query, cfg)
        for ref in find_broken_links(note, cfg.notes_dir):
            typer.echo(ref)


@app.command()
def rename(
    query: Annotated[str, typer.Argument(help="Note ID or slug to rename")],
    new_title: Annotated[str, typer.Argument(help="New title")],
) -> None:
    """Rename a note and update all Markdown links across the notes directory."""
    cfg = _cfg()
    _check_dir(cfg)

    note = _resolve_one(query, cfg)

    new_slug = slugify(new_title)
    if not new_slug:
        typer.echo(f"Title {new_title!r} produces an empty slug", err=True)
        raise typer.Exit(1) from None

    # Extract current ID from stem (format: {id}--{slug})
    stem = note.stem
    if "--" not in stem:
        typer.echo(f"Cannot rename {note.name}: unexpected filename format", err=True)
        raise typer.Exit(1) from None
    note_id = stem.split("--", 1)[0]

    new_filename = f"{note_id}--{new_slug}.md"

    # Collision check — any other note already has this slug
    collision = _find_by_slug(new_slug, cfg.notes_dir)
    if collision is not None and collision != note:
        typer.echo(
            f"A note with slug {new_slug!r} already exists: {collision}", err=True
        )
        raise typer.Exit(1) from None

    old_name = note.name
    new_path = cfg.notes_dir / new_filename

    # Update frontmatter title before renaming so we read from the current path
    post = frontmatter.load(note)
    post["title"] = new_title
    note.write_text(frontmatter.dumps(post), encoding="utf-8")

    # Rename file
    note.rename(new_path)

    # Rewrite Markdown link paths across all notes
    rewrite_links(old_name, new_filename, cfg.notes_dir)

    typer.echo(str(new_path))


@app.command()
def tags(
    count: Annotated[bool, typer.Option("--count", help="Show usage count")] = False,
) -> None:
    """List all tags across notes, optionally with usage counts."""
    cfg = _cfg()
    _check_dir(cfg)
    if count:
        for tag, n in count_tags(cfg.notes_dir):
            typer.echo(f"{tag} {n}")
    else:
        for tag in extract_tags(cfg.notes_dir):
            typer.echo(tag)


@app.command()
def attach(
    image: Annotated[str, typer.Argument(help="Path to the image file")],
) -> None:
    """Copy an image to notes/assets/ and print its relative path."""
    cfg = _cfg()
    _check_dir(cfg)
    image_path = Path(image)
    if not image_path.exists():
        typer.echo(f"File not found: {image_path}", err=True)
        raise typer.Exit(1) from None
    relative = _attach(image_path, cfg.notes_dir, cfg.id_length)
    typer.echo(relative)
