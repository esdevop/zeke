"""Config loading for zeke."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG: str = """\
# zeke configuration
# Place this file at: ~/.config/zeke/config.toml

[notes]
# Directory where your notes are stored (default: ~/notes)
dir = "~/notes"

# Length of generated note IDs (default: 6)
id_length = 6

# Custom note types in addition to the built-in "note" and "journal"
# types = ["book", "person", "contact"]
"""

_CONFIG_PATH = Path.home() / ".config" / "zeke" / "config.toml"
_RESERVED_TYPES = {"note", "journal"}


@dataclass
class Config:
    """Resolved zeke configuration."""

    notes_dir: Path
    id_length: int = 6
    types: list[str] = field(default_factory=list)


def load_config() -> Config:
    """Load config from ~/.config/zeke/config.toml; missing file uses defaults.

    Raises:
        ValueError: If config.toml defines a reserved type name.
    """
    raw: dict[str, object] = {}
    if _CONFIG_PATH.exists():
        with _CONFIG_PATH.open("rb") as f:
            raw = tomllib.load(f)

    notes_section = raw.get("notes", {})
    assert isinstance(notes_section, dict)

    dir_raw = notes_section.get("dir", str(Path.home() / "notes"))
    notes_dir = Path(str(dir_raw)).expanduser().resolve()

    id_length = int(notes_section.get("id_length", 6))

    types_raw = notes_section.get("types", [])
    assert isinstance(types_raw, list)
    types = [str(t) for t in types_raw]

    reserved = _RESERVED_TYPES & set(types)
    if reserved:
        names = ", ".join(f"'{t}'" for t in sorted(reserved))
        raise ValueError(f"Reserved type(s) {names} must not appear in config types")

    return Config(notes_dir=notes_dir, id_length=id_length, types=types)
