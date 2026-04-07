"""Shared pytest fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def notes_dir(tmp_path: Path) -> Path:
    """Temporary notes directory — never touches ~/notes."""
    d = tmp_path / "notes"
    d.mkdir()
    return d
