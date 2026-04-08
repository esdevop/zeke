"""Full-text search via ripgrep."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def search(query: str, notes_dir: Path) -> list[Path]:
    """Search notes for query using ripgrep; return matching absolute paths.

    Only top-level .md files are searched (--max-depth 1).

    Raises:
        SystemExit: If ripgrep (rg) is not installed.
    """
    if shutil.which("rg") is None:
        print(
            "Error: ripgrep (rg) is not installed. "
            "Install it with: apt install ripgrep  or  brew install ripgrep",
            file=sys.stderr,
        )
        sys.exit(1)

    result = subprocess.run(
        ["rg", "-l", "--glob", "*.md", "--max-depth", "1", query, str(notes_dir)],
        capture_output=True,
        text=True,
    )
    if not result.stdout.strip():
        return []
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]
