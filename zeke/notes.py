"""Note creation, slug generation, and image attachment."""

from __future__ import annotations

import datetime
import re
import shutil
import unicodedata
from pathlib import Path

import frontmatter

from zeke.config import Config
from zeke.ids import generate_id


def slugify(title: str) -> str:
    """Derive a URL-safe slug from a title.

    Steps: NFD-decompose → ASCII-encode → replace non-alnum/hyphen → collapse
    consecutive hyphens → strip leading/trailing hyphens.
    """
    text = unicodedata.normalize("NFD", title.lower()).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def resolve(query: str, notes_dir: Path) -> list[Path]:
    """Return notes matching query by ID prefix, exact stem, or slug substring.

    A note matches when any of the following hold for its stem:
    - ``stem == query`` — exact full stem (e.g. ``a1b2c3--graph-theory``)
    - ``stem.startswith(query + "--")`` — ID prefix (e.g. ``a1b2c3``)
    - ``"--" in stem`` and ``query`` appears in the slug portion of the stem

    A ``.md`` suffix in query is stripped before matching, so passing the
    full filename (e.g. ``a1b2c3--graph-theory.md``) works too.
    """
    if query.endswith(".md"):
        query = query[:-3]
    results = []
    for p in sorted(notes_dir.glob("*.md")):
        stem = p.stem
        if stem == query or stem.startswith(query + "--"):
            results.append(p)
        elif "--" in stem and query in stem.split("--", 1)[1]:
            results.append(p)
    return results


def _slug_of(stem: str) -> str:
    """Extract the slug portion of a note stem (everything after first --)."""
    if "--" in stem:
        return stem.split("--", 1)[1]
    return stem


def _find_by_slug(slug: str, notes_dir: Path) -> Path | None:
    """Return the first note whose slug matches exactly, or None."""
    for p in notes_dir.glob("*.md"):
        if _slug_of(p.stem) == slug:
            return p
    return None


def create_note(title: str, type_: str, cfg: Config) -> Path:
    """Create a new note and return its path.

    If a note with the same slug already exists, return its path without
    creating a new file (duplicate detection is slug-only, type-agnostic).

    Raises:
        ValueError: If the derived slug is empty.
    """
    slug = slugify(title)
    if not slug:
        raise ValueError(f"Title {title!r} produces an empty slug")

    existing = _find_by_slug(slug, cfg.notes_dir)
    if existing is not None:
        return existing

    note_id = generate_id(cfg.id_length, cfg.notes_dir)
    filename = f"{note_id}--{slug}.md"
    path = cfg.notes_dir / filename

    post = frontmatter.Post(
        content=f"# {title}",
        id=note_id,
        type=type_,
        title=title,
        tags=[],
        created=datetime.date.today().isoformat(),
    )
    path.write_text(frontmatter.dumps(post) + "\n\n", encoding="utf-8")
    return path


def create_journal(date_str: str, cfg: Config) -> Path:
    """Create (or return existing) journal note for the given YYYY-MM-DD date.

    Raises:
        ValueError: If date_str is not a valid YYYY-MM-DD date.
    """
    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError as e:
        raise ValueError(f"{date_str!r} is not a valid YYYY-MM-DD date") from e

    slug = date_str  # slug = "2026-04-05" as-is
    existing = _find_by_slug(slug, cfg.notes_dir)
    if existing is not None:
        return existing

    title = f"{d.day} {d.strftime('%B %Y')}"  # e.g. "5 April 2026"

    note_id = generate_id(cfg.id_length, cfg.notes_dir)
    filename = f"{note_id}--{slug}.md"
    path = cfg.notes_dir / filename

    post = frontmatter.Post(
        content=f"# {title}",
        id=note_id,
        type="journal",
        title=title,
        tags=[],
        created=date_str,
    )
    path.write_text(frontmatter.dumps(post) + "\n\n", encoding="utf-8")
    return path


def attach(image_path: Path, notes_dir: Path, id_length: int) -> str:
    """Copy an image into notes/assets/ and return its relative path.

    Auto-creates the assets/ directory if it does not exist.

    Returns:
        Relative path string of the form ``assets/{id}--{original_name}``.
    """
    assets_dir = notes_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    image_id = generate_id(id_length, notes_dir)
    dest_name = f"{image_id}--{image_path.name}"
    shutil.copy2(image_path, assets_dir / dest_name)
    return f"assets/{dest_name}"
