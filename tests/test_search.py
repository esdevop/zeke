import shutil
from pathlib import Path
from unittest.mock import patch

import frontmatter
import pytest

from zeke.search import search


def _make_note(notes_dir: Path, name: str, body: str) -> Path:
    post = frontmatter.Post(
        content=body, id="aaa111", type="note", title="T", tags=[], created="2026-01-01"
    )
    p = notes_dir / name
    p.write_text(frontmatter.dumps(post))
    return p


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_search_returns_matching_note(notes_dir):
    note = _make_note(notes_dir, "a1b2c3--zettelkasten.md", "zettelkasten principles")
    _make_note(notes_dir, "b4c5d6--other.md", "something else")
    results = search("zettelkasten", notes_dir)
    assert note in results
    assert all(r.parent == notes_dir for r in results)


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_search_no_match_returns_empty(notes_dir):
    _make_note(notes_dir, "a1b2c3--note.md", "graph theory")
    assert search("zettelkasten", notes_dir) == []


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_search_ignores_assets_subdir(notes_dir):
    assets = notes_dir / "assets"
    assets.mkdir()
    (assets / "x9k2m3--screenshot.md").write_text("zettelkasten hidden")
    _make_note(notes_dir, "a1b2c3--note.md", "something else")
    results = search("zettelkasten", notes_dir)
    assert not any("assets" in str(r) for r in results)


def test_search_exits_when_rg_missing(notes_dir):
    with patch("zeke.search.shutil.which", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            search("anything", notes_dir)
    assert exc_info.value.code == 1
