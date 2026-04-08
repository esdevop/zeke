import datetime
from pathlib import Path

import frontmatter
import pytest
from typer.testing import CliRunner

from zeke.cli import app
from zeke.config import Config

runner = CliRunner()


@pytest.fixture
def cfg(notes_dir: Path) -> Config:
    return Config(notes_dir=notes_dir)


@pytest.fixture(autouse=False)
def mock_config(monkeypatch, cfg: Config):
    monkeypatch.setattr("zeke.cli.load_config", lambda: cfg)
    return cfg


def _invoke(args: list[str]) -> object:
    return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# zeke new
# ---------------------------------------------------------------------------


def test_new_creates_note(mock_config, notes_dir):
    result = runner.invoke(app, ["new", "--title", "Graph Theory"])
    assert result.exit_code == 0
    paths = list(notes_dir.glob("*.md"))
    assert len(paths) == 1
    assert "graph-theory" in paths[0].stem


def test_new_prints_absolute_path(mock_config, notes_dir):
    result = runner.invoke(app, ["new", "--title", "Graph Theory"])
    assert result.exit_code == 0
    printed = result.output.strip()
    assert Path(printed).is_absolute()
    assert Path(printed).exists()


def test_new_correct_frontmatter(mock_config, notes_dir):
    runner.invoke(app, ["new", "--title", "Graph Theory"])
    note = next(notes_dir.glob("*.md"))
    post = frontmatter.load(note)
    assert post["title"] == "Graph Theory"
    assert post["type"] == "note"
    assert post["tags"] == []
    assert "id" in post.metadata


def test_new_custom_type(mock_config, notes_dir):
    result = runner.invoke(app, ["new", "--title", "John Doe", "--type", "journal"])
    assert result.exit_code == 0
    note = next(notes_dir.glob("*.md"))
    assert frontmatter.load(note)["type"] == "journal"


def test_new_duplicate_slug_prints_existing(mock_config, notes_dir):
    r1 = runner.invoke(app, ["new", "--title", "Graph Theory"])
    r2 = runner.invoke(app, ["new", "--title", "Graph Theory"])
    assert r1.exit_code == 0
    assert r2.exit_code == 0
    assert r1.output.strip() == r2.output.strip()
    assert len(list(notes_dir.glob("*.md"))) == 1


def test_new_empty_slug_exits_1(mock_config):
    result = runner.invoke(app, ["new", "--title", "!!!"])
    assert result.exit_code == 1


def test_new_invalid_type_exits_1(mock_config):
    result = runner.invoke(app, ["new", "--title", "Foo", "--type", "bogus"])
    assert result.exit_code == 1
    assert "bogus" in result.output or "bogus" in (result.stderr or "")


# ---------------------------------------------------------------------------
# zeke open
# ---------------------------------------------------------------------------


def test_open_found(mock_config, notes_dir):
    p = notes_dir / "a1b2c3--graph-theory.md"
    p.write_text("")
    result = runner.invoke(app, ["open", "a1b2c3"])
    assert result.exit_code == 0
    assert result.output.strip() == str(p)


def test_open_not_found_exits_1(mock_config):
    result = runner.invoke(app, ["open", "nonexistent"])
    assert result.exit_code == 1


def test_open_multiple_matches_exits_1(mock_config, notes_dir):
    (notes_dir / "a1b2c3--graph-theory.md").write_text("")
    (notes_dir / "b4c5d6--graph-algorithms.md").write_text("")
    result = runner.invoke(app, ["open", "graph"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# zeke journal
# ---------------------------------------------------------------------------


def test_journal_specific_date_creates_note(mock_config, notes_dir):
    result = runner.invoke(app, ["journal", "2026-04-05"])
    assert result.exit_code == 0
    paths = list(notes_dir.glob("*.md"))
    assert len(paths) == 1
    assert "2026-04-05" in paths[0].stem


def test_journal_human_title(mock_config, notes_dir):
    runner.invoke(app, ["journal", "2026-04-05"])
    note = next(notes_dir.glob("*.md"))
    assert frontmatter.load(note)["title"] == "5 April 2026"


def test_journal_defaults_to_today(mock_config, notes_dir):
    result = runner.invoke(app, ["journal"])
    assert result.exit_code == 0
    today = datetime.date.today().isoformat()
    assert any(today in p.stem for p in notes_dir.glob("*.md"))


def test_journal_invalid_date_exits_1(mock_config):
    result = runner.invoke(app, ["journal", "not-a-date"])
    assert result.exit_code == 1


def test_journal_invalid_calendar_exits_1(mock_config):
    result = runner.invoke(app, ["journal", "2026-13-01"])
    assert result.exit_code == 1


def test_journal_duplicate_returns_same_path(mock_config, notes_dir):
    r1 = runner.invoke(app, ["journal", "2026-04-05"])
    r2 = runner.invoke(app, ["journal", "2026-04-05"])
    assert r1.output.strip() == r2.output.strip()
    assert len(list(notes_dir.glob("*.md"))) == 1


# ---------------------------------------------------------------------------
# zeke list
# ---------------------------------------------------------------------------


def _make_fm_note(notes_dir: Path, name: str, type_: str, tags: list[str]) -> Path:
    post = frontmatter.Post(
        content="", id="x", type=type_, title="T", tags=tags, created="2026-01-01"
    )
    p = notes_dir / name
    p.write_text(frontmatter.dumps(post))
    return p


def test_list_all(mock_config, notes_dir):
    a = _make_fm_note(notes_dir, "a1b2c3--a.md", "note", [])
    b = _make_fm_note(notes_dir, "b4c5d6--b.md", "journal", [])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert str(a) in result.output
    assert str(b) in result.output


def test_list_filter_by_type(mock_config, notes_dir):
    _make_fm_note(notes_dir, "a1b2c3--a.md", "note", [])
    b = _make_fm_note(notes_dir, "b4c5d6--b.md", "journal", [])
    result = runner.invoke(app, ["list", "--type", "journal"])
    assert result.exit_code == 0
    assert str(b) in result.output
    assert "a1b2c3--a" not in result.output


def test_list_filter_by_tag(mock_config, notes_dir):
    a = _make_fm_note(notes_dir, "a1b2c3--a.md", "note", ["math"])
    _make_fm_note(notes_dir, "b4c5d6--b.md", "note", ["cs"])
    result = runner.invoke(app, ["list", "--tag", "math"])
    assert result.exit_code == 0
    assert str(a) in result.output
    assert "b4c5d6--b" not in result.output


def test_list_invalid_type_exits_1(mock_config):
    result = runner.invoke(app, ["list", "--type", "bogus"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# zeke backlinks
# ---------------------------------------------------------------------------


def test_backlinks_found(mock_config, notes_dir):
    target = notes_dir / "a1b2c3--target.md"
    target.write_text("")
    linker = notes_dir / "b4c5d6--linker.md"
    linker.write_text("[T](a1b2c3--target.md)")
    result = runner.invoke(app, ["backlinks", "a1b2c3"])
    assert result.exit_code == 0
    assert str(linker) in result.output


def test_backlinks_empty_output_when_none(mock_config, notes_dir):
    (notes_dir / "a1b2c3--target.md").write_text("")
    result = runner.invoke(app, ["backlinks", "a1b2c3"])
    assert result.exit_code == 0
    assert result.output.strip() == ""


# ---------------------------------------------------------------------------
# zeke orphans
# ---------------------------------------------------------------------------


def test_orphans_lists_unlinked_notes(mock_config, notes_dir):
    lone = notes_dir / "a1b2c3--lone.md"
    lone.write_text("")
    result = runner.invoke(app, ["orphans"])
    assert result.exit_code == 0
    assert str(lone) in result.output


def test_orphans_excludes_linked_notes(mock_config, notes_dir):
    a = notes_dir / "a1b2c3--a.md"
    b = notes_dir / "b4c5d6--b.md"
    a.write_text("[B](b4c5d6--b.md)")
    b.write_text("")
    result = runner.invoke(app, ["orphans"])
    assert result.exit_code == 0
    assert str(a) not in result.output
    assert str(b) not in result.output


# ---------------------------------------------------------------------------
# zeke broken
# ---------------------------------------------------------------------------


def test_broken_no_arg_lists_notes_with_broken_links(mock_config, notes_dir):
    bad = notes_dir / "a1b2c3--bad.md"
    bad.write_text("[Gone](zzz999--gone.md)")
    result = runner.invoke(app, ["broken"])
    assert result.exit_code == 0
    assert str(bad) in result.output


def test_broken_no_arg_excludes_valid(mock_config, notes_dir):
    (notes_dir / "a1b2c3--real.md").write_text("")
    good = notes_dir / "b4c5d6--linker.md"
    good.write_text("[Real](a1b2c3--real.md)")
    result = runner.invoke(app, ["broken"])
    assert result.exit_code == 0
    assert str(good) not in result.output


def test_broken_with_arg_lists_broken_filenames(mock_config, notes_dir):
    note = notes_dir / "a1b2c3--note.md"
    note.write_text("[Gone](zzz999--gone.md)")
    result = runner.invoke(app, ["broken", "a1b2c3"])
    assert result.exit_code == 0
    assert "zzz999--gone.md" in result.output


def test_broken_with_arg_empty_when_all_valid(mock_config, notes_dir):
    (notes_dir / "a1b2c3--target.md").write_text("")
    (notes_dir / "b4c5d6--linker.md").write_text("[T](a1b2c3--target.md)")
    result = runner.invoke(app, ["broken", "b4c5d6"])
    assert result.exit_code == 0
    assert result.output.strip() == ""


# ---------------------------------------------------------------------------
# zeke rename
# ---------------------------------------------------------------------------


def test_rename_renames_file(mock_config, notes_dir):
    (notes_dir / "a1b2c3--old-title.md").write_text(
        "---\nid: a1b2c3\ntitle: Old Title\ntype: note\ntags: []\ncreated: 2026-01-01\n---\n"
    )
    result = runner.invoke(app, ["rename", "a1b2c3", "New Title"])
    assert result.exit_code == 0
    assert (notes_dir / "a1b2c3--new-title.md").exists()
    assert not (notes_dir / "a1b2c3--old-title.md").exists()


def test_rename_updates_frontmatter_title(mock_config, notes_dir):
    (notes_dir / "a1b2c3--old-title.md").write_text(
        "---\nid: a1b2c3\ntitle: Old Title\ntype: note\ntags: []\ncreated: 2026-01-01\n---\n"
    )
    runner.invoke(app, ["rename", "a1b2c3", "New Title"])
    post = frontmatter.load(notes_dir / "a1b2c3--new-title.md")
    assert post["title"] == "New Title"


def test_rename_rewrites_links_in_other_notes(mock_config, notes_dir):
    (notes_dir / "a1b2c3--old-title.md").write_text(
        "---\nid: a1b2c3\ntitle: Old Title\ntype: note\ntags: []\ncreated: 2026-01-01\n---\n"
    )
    linker = notes_dir / "b4c5d6--linker.md"
    linker.write_text("[Old](a1b2c3--old-title.md)")
    runner.invoke(app, ["rename", "a1b2c3", "New Title"])
    assert "a1b2c3--new-title.md" in linker.read_text()


def test_rename_collision_exits_1(mock_config, notes_dir):
    (notes_dir / "a1b2c3--note-a.md").write_text(
        "---\nid: a1b2c3\ntitle: Note A\ntype: note\ntags: []\ncreated: 2026-01-01\n---\n"
    )
    (notes_dir / "b4c5d6--note-b.md").write_text("")
    result = runner.invoke(app, ["rename", "a1b2c3", "Note B"])
    assert result.exit_code == 1


def test_rename_empty_slug_exits_1(mock_config, notes_dir):
    (notes_dir / "a1b2c3--note.md").write_text(
        "---\nid: a1b2c3\ntitle: Note\ntype: note\ntags: []\ncreated: 2026-01-01\n---\n"
    )
    result = runner.invoke(app, ["rename", "a1b2c3", "!!!"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# zeke tags
# ---------------------------------------------------------------------------


def test_tags_lists_all_tags(mock_config, notes_dir):
    _make_fm_note(notes_dir, "a.md", "note", ["math", "cs"])
    _make_fm_note(notes_dir, "b.md", "note", ["math"])
    result = runner.invoke(app, ["tags"])
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert set(lines) == {"math", "cs"}
    assert lines == sorted(lines)


def test_tags_count_format(mock_config, notes_dir):
    _make_fm_note(notes_dir, "a.md", "note", ["math"])
    _make_fm_note(notes_dir, "b.md", "note", ["math"])
    _make_fm_note(notes_dir, "c.md", "note", ["cs"])
    result = runner.invoke(app, ["tags", "--count"])
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert lines[0] == "math 2"
    assert lines[1] == "cs 1"


# ---------------------------------------------------------------------------
# zeke attach
# ---------------------------------------------------------------------------


def test_attach_prints_relative_path(mock_config, notes_dir, tmp_path):
    img = tmp_path / "screenshot.png"
    img.write_bytes(b"\x89PNG")
    result = runner.invoke(app, ["attach", str(img)])
    assert result.exit_code == 0
    printed = result.output.strip()
    assert printed.startswith("assets/")
    assert "screenshot.png" in printed


def test_attach_copies_file_to_assets(mock_config, notes_dir, tmp_path):
    img = tmp_path / "diagram.png"
    img.write_bytes(b"PNG-DATA")
    runner.invoke(app, ["attach", str(img)])
    assets = list((notes_dir / "assets").iterdir())
    assert len(assets) == 1
    assert assets[0].read_bytes() == b"PNG-DATA"


def test_attach_missing_file_exits_1(mock_config):
    result = runner.invoke(app, ["attach", "/nonexistent/photo.png"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# config error handling
# ---------------------------------------------------------------------------


def test_config_error_exits_1(monkeypatch, notes_dir):
    def _raise() -> Config:
        raise ValueError("reserved")

    monkeypatch.setattr("zeke.cli.load_config", _raise)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1


def test_missing_notes_dir_exits_1(monkeypatch, tmp_path):
    cfg = Config(notes_dir=tmp_path / "nonexistent")
    monkeypatch.setattr("zeke.cli.load_config", lambda: cfg)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1
