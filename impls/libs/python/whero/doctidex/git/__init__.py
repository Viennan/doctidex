"""Git-backed doctidex implementation variant."""

from .external import ExternalService
from .worktrees import CacheService, WorktreeService

__all__ = ["CacheService", "ExternalService", "WorktreeService"]
