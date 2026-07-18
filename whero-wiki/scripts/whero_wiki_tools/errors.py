"""Tool-level errors with messages suitable for agent diagnostics."""


class WheroToolError(ValueError):
    """Raised when a Whero Wiki contract cannot be satisfied safely."""

