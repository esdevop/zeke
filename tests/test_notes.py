import datetime

import frontmatter
import pytest

from zeke.config import Config
from zeke.notes import attach, create_journal, create_note, resolve, slugify

# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify_basic():
    assert slugify("Graph Theory") == "graph-theory"


def test_slugify_accented_chars():
    assert slugify("Résumé") == "resume"


def test_slugify_special_chars_become_hyphens():
    assert slugify("A/B Testing") == "a-b-testing"


def test_slugify_collapses_consecutive_hyphens():
    assert slugify("foo  bar") == "foo-bar"


def test_slugify_strips_leading_trailing_hyphens():
    assert slugify("!!! hello !!!") == "hello"


def test_slugify_all_special_returns_empty():
    assert slugify("!!!") == ""


def test_slugify_preserves_numbers():
    assert slugify("Chapter 1") == "chapter-1"


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------


def test_resolve_by_id_prefix(notes_dir):
    (notes_dir / "a1b2c3--graph-theory.md").write_text("")
    results = resolve("a1b2c3", notes_dir)
    assert len(results) == 1
    assert results[0].name == "a1b2c3--graph-theory.md"


def test_resolve_by_exact_stem(notes_dir):
    (notes_dir / "a1b2c3--graph-theory.md").write_text("")
    results = resolve("a1b2c3--graph-theory", notes_dir)
    assert len(results) == 1


def test_resolve_by_slug_substring(notes_dir):
    (notes_dir / "a1b2c3--graph-theory.md").write_text("")
    results = resolve("graph-theory", notes_dir)
    assert len(results) == 1


def test_resolve_slug_partial_match(notes_dir):
    (notes_dir / "a1b2c3--graph-theory.md").write_text("")
    (notes_dir / "b4c5d6--graph-algorithms.md").write_text("")
    results = resolve("graph", notes_dir)
    assert len(results) == 2


def test_resolve_no_match(notes_dir):
    assert resolve("nonexistent", notes_dir) == []


def test_resolve_ignores_assets(notes_dir):
    assets = notes_dir / "assets"
    assets.mkdir()
    (assets / "a1b2c3--screenshot.png").write_text("")
    assert resolve("a1b2c3", notes_dir) == []


# ---------------------------------------------------------------------------
# create_note
# ---------------------------------------------------------------------------


def test_create_note_creates_file(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_note("Graph Theory", "note", cfg)
    assert path.exists()
    assert path.suffix == ".md"
    assert "graph-theory" in path.stem


def test_create_note_frontmatter_fields(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_note("Graph Theory", "note", cfg)
    post = frontmatter.load(path)
    assert post["title"] == "Graph Theory"
    assert post["type"] == "note"
    assert "id" in post.metadata
    assert post["tags"] == []
    assert "created" in post.metadata


def test_create_note_created_date_is_today(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_note("Graph Theory", "note", cfg)
    post = frontmatter.load(path)
    assert post["created"] == datetime.date.today().isoformat()


def test_create_note_duplicate_returns_existing(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    p1 = create_note("Graph Theory", "note", cfg)
    p2 = create_note("Graph Theory", "note", cfg)
    assert p1 == p2
    assert len(list(notes_dir.glob("*.md"))) == 1


def test_create_note_duplicate_type_agnostic(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    p1 = create_note("Graph Theory", "note", cfg)
    p2 = create_note("Graph Theory!", "contact", cfg)  # same slug after slugify
    assert p1 == p2


def test_create_note_empty_slug_raises(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    with pytest.raises(ValueError, match="empty slug"):
        create_note("!!!", "note", cfg)


def test_create_note_custom_type(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_note("John Doe", "contact", cfg)
    post = frontmatter.load(path)
    assert post["type"] == "contact"


# ---------------------------------------------------------------------------
# create_journal
# ---------------------------------------------------------------------------


def test_create_journal_creates_file(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_journal("2026-04-05", cfg)
    assert path.exists()
    assert "2026-04-05" in path.stem


def test_create_journal_human_title(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_journal("2026-04-05", cfg)
    post = frontmatter.load(path)
    assert post["title"] == "5 April 2026"


def test_create_journal_type_is_journal(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_journal("2026-04-05", cfg)
    post = frontmatter.load(path)
    assert post["type"] == "journal"


def test_create_journal_created_field_is_date_str(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_journal("2026-04-05", cfg)
    post = frontmatter.load(path)
    assert post["created"] == "2026-04-05"


def test_create_journal_duplicate_returns_existing(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    p1 = create_journal("2026-04-05", cfg)
    p2 = create_journal("2026-04-05", cfg)
    assert p1 == p2
    assert len(list(notes_dir.glob("*.md"))) == 1


def test_create_journal_invalid_format_raises(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    with pytest.raises(ValueError, match="not a valid YYYY-MM-DD"):
        create_journal("April 5 2026", cfg)


def test_create_journal_invalid_calendar_raises(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    with pytest.raises(ValueError, match="not a valid YYYY-MM-DD"):
        create_journal("2026-13-01", cfg)


def test_create_journal_single_digit_day_title(notes_dir):
    cfg = Config(notes_dir=notes_dir)
    path = create_journal("2026-01-07", cfg)
    post = frontmatter.load(path)
    # Should be "7 January 2026", not "07 January 2026"
    assert post["title"] == "7 January 2026"


# ---------------------------------------------------------------------------
# attach
# ---------------------------------------------------------------------------


def test_attach_copies_file(notes_dir, tmp_path):
    img = tmp_path / "screenshot.png"
    img.write_bytes(b"\x89PNG")
    result = attach(img, notes_dir, id_length=6)
    dest = notes_dir / result
    assert dest.exists()
    assert dest.read_bytes() == b"\x89PNG"


def test_attach_returns_relative_path(notes_dir, tmp_path):
    img = tmp_path / "diagram.png"
    img.write_bytes(b"")
    result = attach(img, notes_dir, id_length=6)
    assert result.startswith("assets/")
    assert "diagram.png" in result


def test_attach_creates_assets_dir(notes_dir, tmp_path):
    assert not (notes_dir / "assets").exists()
    img = tmp_path / "photo.png"
    img.write_bytes(b"")
    attach(img, notes_dir, id_length=6)
    assert (notes_dir / "assets").is_dir()


def test_attach_preserves_original_name(notes_dir, tmp_path):
    img = tmp_path / "my-diagram.svg"
    img.write_text("<svg/>")
    result = attach(img, notes_dir, id_length=6)
    assert result.endswith("--my-diagram.svg")
