"""ID generation for notes and image assets."""

from __future__ import annotations

import random
import string
from pathlib import Path


def _id_exists(candidate: str, notes_dir: Path) -> bool:
    """Return True if candidate ID is already used in notes/ or assets/."""
    prefix = candidate + "--"
    for p in notes_dir.glob("*.md"):
        stem = p.stem
        if stem == candidate or stem.startswith(prefix):
            return True
    assets_dir = notes_dir / "assets"
    if assets_dir.is_dir():
        for p in assets_dir.iterdir():
            stem = p.stem
            if stem == candidate or stem.startswith(prefix):
                return True
    return False


def generate_id(length: int, notes_dir: Path) -> str:
    """Generate a unique random lowercase-alphanumeric ID of the given length.

    Scans notes_dir/*.md and notes_dir/assets/* to avoid collisions.
    """
    chars = string.ascii_lowercase + string.digits
    while True:
        candidate = "".join(random.choices(chars, k=length))
        if not _id_exists(candidate, notes_dir):
            return candidate
