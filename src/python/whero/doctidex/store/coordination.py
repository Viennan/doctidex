"""Workflow-facing protocol for RuntimeStore recovery coordination."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class WorkflowCoordinator(Protocol):
    """Coordinate retryable RuntimeStore operations and cache-backed work."""

    def run[T](self, operation: Callable[[], T]) -> T:
        """Run one operation, repairing residual RuntimeStore journals when needed."""

    def with_repository[T](self, git_url: str, operation: Callable[[Path], T]) -> T:
        """Run cache-backed work in the transaction selected for one Git URL."""


__all__ = ["WorkflowCoordinator"]
