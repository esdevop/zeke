from pathlib import Path

import frontmatter as fm

from zeke.links import (
    count_tags,
    extract_tags,
    find_backlinks,
    find_broken_links,
    find_broken_notes,
    find_orphans,
    parse_links,
    rewrite_links,
)

# ---------------------------------------------------------------------------
# parse_links
# ---------------------------------------------------------------------------


def test_parse_links_basic():
    content = "See [Graph Theory](a1b2c3--graph-theory.md) for details."
    assert parse_links(content) == ["a1b2c3--graph-theory.md"]


def test_parse_links_multiple():
    content = "[A](a1b2c3--a.md) and [B](b4c5d6--b.md)"
    assert parse_links(content) == ["a1b2c3--a.md", "b4c5d6--b.md"]


def test_parse_links_ignores_non_md():
    content = "[Image](assets/x9k2m3--photo.png) and [Web](https://example.com)"
    assert parse_links(content) == []


def test_parse_links_empty_content():
    assert parse_links("No links here.") == []


def test_parse_links_ignores_bare_md_url():
    # Without [...] prefix it's not a Markdown link
    assert parse_links("just a1b2c3--note.md in text") == []


# ---------------------------------------------------------------------------
# find_backlinks
# ---------------------------------------------------------------------------


def _write_note(notes_dir: Path, name: str, content: str = "") -> Path:
    p = notes_dir / name
    p.write_text(content)
    return p


def test_find_backlinks_returns_linking_note(notes_dir):
    target = _write_note(notes_dir, "a1b2c3--target.md")
    linker = _write_note(notes_dir, "b4c5d6--linker.md", "[Target](a1b2c3--target.md)")
    _write_note(notes_dir, "c7d8e9--unrelated.md", "no links here")

    result = find_backlinks(target, notes_dir)
    assert result == [linker]


def test_find_backlinks_empty_when_none_link(notes_dir):
    target = _write_note(notes_dir, "a1b2c3--target.md")
    _write_note(notes_dir, "b4c5d6--other.md", "nothing")
    assert find_backlinks(target, notes_dir) == []


def test_find_backlinks_excludes_self(notes_dir):
    # A note linking to itself still shows up (technically valid)
    note = _write_note(notes_dir, "a1b2c3--self.md", "[Self](a1b2c3--self.md)")
    assert note in find_backlinks(note, notes_dir)


# ---------------------------------------------------------------------------
# find_orphans
# ---------------------------------------------------------------------------


def test_find_orphans_all_orphans(notes_dir):
    a = _write_note(notes_dir, "a1b2c3--note-a.md", "no links")
    b = _write_note(notes_dir, "b4c5d6--note-b.md", "no links")
    orphans = find_orphans(notes_dir)
    assert set(orphans) == {a, b}


def test_find_orphans_linked_notes_excluded(notes_dir):
    a = _write_note(notes_dir, "a1b2c3--note-a.md", "[B](b4c5d6--note-b.md)")
    b = _write_note(notes_dir, "b4c5d6--note-b.md", "no outgoing links")
    orphans = find_orphans(notes_dir)
    # a has outgoing, b has incoming → neither is an orphan
    assert a not in orphans
    assert b not in orphans


def test_find_orphans_empty_dir(notes_dir):
    assert find_orphans(notes_dir) == []


# ---------------------------------------------------------------------------
# find_broken_notes / find_broken_links
# ---------------------------------------------------------------------------


def test_find_broken_notes_detects_missing_target(notes_dir):
    note = _write_note(notes_dir, "a1b2c3--linker.md", "[Gone](zzz999--gone.md)")
    result = find_broken_notes(notes_dir)
    assert note in result


def test_find_broken_notes_excludes_valid_links(notes_dir):
    _write_note(notes_dir, "a1b2c3--target.md")
    linker = _write_note(notes_dir, "b4c5d6--linker.md", "[Target](a1b2c3--target.md)")
    assert linker not in find_broken_notes(notes_dir)


def test_find_broken_notes_empty_when_all_valid(notes_dir):
    _write_note(notes_dir, "a1b2c3--target.md")
    _write_note(notes_dir, "b4c5d6--linker.md", "[T](a1b2c3--target.md)")
    assert find_broken_notes(notes_dir) == []


def test_find_broken_links_returns_missing_filenames(notes_dir):
    note = _write_note(notes_dir, "a1b2c3--linker.md", "[Gone](zzz999--gone.md)")
    broken = find_broken_links(note, notes_dir)
    assert broken == ["zzz999--gone.md"]


def test_find_broken_links_empty_when_all_valid(notes_dir):
    _write_note(notes_dir, "a1b2c3--target.md")
    note = _write_note(notes_dir, "b4c5d6--linker.md", "[T](a1b2c3--target.md)")
    assert find_broken_links(note, notes_dir) == []


def test_find_broken_links_mixed(notes_dir):
    _write_note(notes_dir, "a1b2c3--real.md")
    note = _write_note(
        notes_dir,
        "b4c5d6--linker.md",
        "[Real](a1b2c3--real.md) [Gone](zzz999--gone.md)",
    )
    broken = find_broken_links(note, notes_dir)
    assert broken == ["zzz999--gone.md"]


# ---------------------------------------------------------------------------
# rewrite_links
# ---------------------------------------------------------------------------


def test_rewrite_links_updates_path(notes_dir):
    note = _write_note(notes_dir, "b4c5d6--linker.md", "[Old](a1b2c3--old-slug.md)")
    rewrite_links("a1b2c3--old-slug.md", "a1b2c3--new-slug.md", notes_dir)
    assert "[Old](a1b2c3--new-slug.md)" in note.read_text()


def test_rewrite_links_preserves_display_text(notes_dir):
    note = _write_note(notes_dir, "b4c5d6--linker.md", "[My Title](a1b2c3--old.md)")
    rewrite_links("a1b2c3--old.md", "a1b2c3--new.md", notes_dir)
    assert "[My Title]" in note.read_text()


def test_rewrite_links_only_affects_target(notes_dir):
    a = _write_note(notes_dir, "aaa111--a.md", "[X](target.md)")
    b = _write_note(notes_dir, "bbb222--b.md", "[Y](other.md)")
    rewrite_links("target.md", "renamed.md", notes_dir)
    assert "renamed.md" in a.read_text()
    assert "other.md" in b.read_text()  # untouched


def test_rewrite_links_no_match_is_noop(notes_dir):
    content = "[X](a1b2c3--unchanged.md)"
    note = _write_note(notes_dir, "b4c5d6--note.md", content)
    rewrite_links("nonexistent.md", "new.md", notes_dir)
    assert note.read_text() == content


# ---------------------------------------------------------------------------
# extract_tags / count_tags
# ---------------------------------------------------------------------------


def _write_fm_note(notes_dir: Path, name: str, tags: list[str]) -> None:
    post = fm.Post(
        content="", title="Test", tags=tags, id="aaa111", type="note", created="2026-01-01"
    )
    (notes_dir / name).write_text(fm.dumps(post))


def test_extract_tags_sorted(notes_dir):
    _write_fm_note(notes_dir, "a.md", ["zettelkasten", "math"])
    _write_fm_note(notes_dir, "b.md", ["math", "cs"])
    tags = extract_tags(notes_dir)
    assert tags == sorted(tags)
    assert set(tags) == {"zettelkasten", "math", "cs"}


def test_extract_tags_deduplicates(notes_dir):
    _write_fm_note(notes_dir, "a.md", ["math"])
    _write_fm_note(notes_dir, "b.md", ["math"])
    assert extract_tags(notes_dir) == ["math"]


def test_extract_tags_empty(notes_dir):
    assert extract_tags(notes_dir) == []


def test_count_tags_sorted_by_count_descending(notes_dir):
    _write_fm_note(notes_dir, "a.md", ["math", "cs"])
    _write_fm_note(notes_dir, "b.md", ["math"])
    _write_fm_note(notes_dir, "c.md", ["math"])
    counts = dict(count_tags(notes_dir))
    assert counts["math"] == 3
    assert counts["cs"] == 1
    pairs = count_tags(notes_dir)
    assert pairs[0][0] == "math"  # highest count first


def test_count_tags_alpha_tiebreak(notes_dir):
    _write_fm_note(notes_dir, "a.md", ["beta", "alpha"])
    _write_fm_note(notes_dir, "b.md", ["beta", "alpha"])
    pairs = count_tags(notes_dir)
    # Both have count 2; alpha < beta alphabetically
    assert pairs[0][0] == "alpha"
    assert pairs[1][0] == "beta"
