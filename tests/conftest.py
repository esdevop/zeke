"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def notes_dir(tmp_path: Path) -> Path:
    """Temporary notes directory — never touches ~/notes."""
    d = tmp_path / "notes"
    d.mkdir()
    return d
