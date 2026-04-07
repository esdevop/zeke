# Python Development

Use `uv` for all Python package and environment operations.

| Instead of | Use |
|------------|-----|
| `pip install` | `uv add` |
| `pip install -e ".[dev]"` | `uv sync` |
| `python script.py` | `uv run script.py` |
| `pytest` | `uv run pytest` |
| `python -m module` | `uv run python -m module` |

Never call `pip` directly. Never activate a virtualenv manually — `uv run` handles it.
