from __future__ import annotations

import re
from pathlib import Path

# Matches standard Markdown links whose target ends in .md, e.g. [Title](a1b2c3--slug.md)
MDLINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")


def parse_links(content: str) -> list[str]:
    """Return .md filenames referenced in Markdown links within content."""
    return [m.group(2) for m in MDLINK_RE.finditer(content)]


def find_backlinks(target_path: Path, notes_dir: Path) -> list[Path]:
    """Return paths of notes that contain a Markdown link to target_path."""
    target_name = target_path.name
    return [
        p
        for p in sorted(notes_dir.glob("*.md"))
        if target_name in parse_links(p.read_text(encoding="utf-8"))
    ]


def find_orphans(notes_dir: Path) -> list[Path]:
    """Return notes with no outgoing or incoming Markdown links."""
    all_notes = sorted(notes_dir.glob("*.md"))
    linked_names: set[str] = set()
    has_outgoing: set[Path] = set()
    for note in all_notes:
        refs = parse_links(note.read_text(encoding="utf-8"))
        if refs:
            has_outgoing.add(note)
            linked_names.update(refs)
    linked_paths = {notes_dir / name for name in linked_names}
    return [n for n in all_notes if n not in has_outgoing and n not in linked_paths]


def find_broken_notes(notes_dir: Path) -> list[Path]:
    """Return notes that contain at least one broken Markdown link."""
    result = []
    for note in sorted(notes_dir.glob("*.md")):
        refs = parse_links(note.read_text(encoding="utf-8"))
        if any(not (notes_dir / ref).exists() for ref in refs):
            result.append(note)
    return result


def find_broken_links(note_path: Path, notes_dir: Path) -> list[str]:
    """Return broken link paths (filenames) inside a specific note."""
    return [
        ref
        for ref in parse_links(note_path.read_text(encoding="utf-8"))
        if not (notes_dir / ref).exists()
    ]


def rewrite_links(old_name: str, new_name: str, notes_dir: Path) -> None:
    """Rewrite Markdown link paths from old_name to new_name across all notes.

    Only the path inside (...) is rewritten; display text [Title] is left untouched.
    """
    pattern = re.compile(r"(?<=\()" + re.escape(old_name) + r"(?=\))")
    for note in notes_dir.glob("*.md"):
        text = note.read_text(encoding="utf-8")
        updated = pattern.sub(new_name, text)
        if updated != text:
            note.write_text(updated, encoding="utf-8")


def extract_tags(notes_dir: Path) -> list[str]:
    """Return all unique tags across all notes, sorted alphabetically."""
    import frontmatter  # python-frontmatter

    tags: set[str] = set()
    for note in notes_dir.glob("*.md"):
        post = frontmatter.load(note)
        note_tags = post.get("tags") or []
        tags.update(note_tags)
    return sorted(tags)


def count_tags(notes_dir: Path) -> list[tuple[str, int]]:
    """Return (tag, count) pairs sorted by count descending, then alphabetically."""
    import frontmatter  # python-frontmatter

    counts: dict[str, int] = {}
    for note in notes_dir.glob("*.md"):
        post = frontmatter.load(note)
        for tag in post.get("tags") or []:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
