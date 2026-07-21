"""Error behavior shared by the View implementation."""

from typing import NoReturn


def fail(message: str) -> NoReturn:
    """Raise a CLI-style error with a stable exit status."""

    raise SystemExit(f"error: {message}")
