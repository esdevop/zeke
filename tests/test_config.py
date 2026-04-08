from pathlib import Path

import pytest

import zeke.config as config_mod
from zeke.config import Config, load_config


def _write_toml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_defaults_when_config_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config_mod, "_CONFIG_PATH", tmp_path / "nonexistent.toml")
    cfg = load_config()
    assert cfg.id_length == 6
    assert cfg.types == []
    assert cfg.notes_dir == (Path.home() / "notes").resolve()


def test_reads_notes_dir(monkeypatch, tmp_path):
    toml_path = tmp_path / "config.toml"
    _write_toml(toml_path, f'[notes]\ndir = "{tmp_path}"\n')
    monkeypatch.setattr(config_mod, "_CONFIG_PATH", toml_path)
    cfg = load_config()
    assert cfg.notes_dir == tmp_path.resolve()


def test_reads_id_length(monkeypatch, tmp_path):
    toml_path = tmp_path / "config.toml"
    _write_toml(toml_path, "[notes]\nid_length = 8\n")
    monkeypatch.setattr(config_mod, "_CONFIG_PATH", toml_path)
    cfg = load_config()
    assert cfg.id_length == 8


def test_reads_user_types(monkeypatch, tmp_path):
    toml_path = tmp_path / "config.toml"
    _write_toml(toml_path, '[notes]\ntypes = ["contact", "book"]\n')
    monkeypatch.setattr(config_mod, "_CONFIG_PATH", toml_path)
    cfg = load_config()
    assert cfg.types == ["contact", "book"]


def test_reserved_type_note_raises(monkeypatch, tmp_path):
    toml_path = tmp_path / "config.toml"
    _write_toml(toml_path, '[notes]\ntypes = ["note"]\n')
    monkeypatch.setattr(config_mod, "_CONFIG_PATH", toml_path)
    with pytest.raises(ValueError, match="note"):
        load_config()


def test_reserved_type_journal_raises(monkeypatch, tmp_path):
    toml_path = tmp_path / "config.toml"
    _write_toml(toml_path, '[notes]\ntypes = ["journal"]\n')
    monkeypatch.setattr(config_mod, "_CONFIG_PATH", toml_path)
    with pytest.raises(ValueError, match="journal"):
        load_config()


def test_config_dataclass_fields():
    cfg = Config(notes_dir=Path("/tmp/notes"), id_length=4, types=["contact"])
    assert cfg.notes_dir == Path("/tmp/notes")
    assert cfg.id_length == 4
    assert cfg.types == ["contact"]
