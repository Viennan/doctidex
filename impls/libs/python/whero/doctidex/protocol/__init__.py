"""Implementation-neutral doctidex parsing and validation."""

from .document import DoctidexDocument, MarkdownLink, markdown_links
from .root import RootContext, discover_roots, select_root
from .validation import validate_protocol

__all__ = [
    "DoctidexDocument",
    "MarkdownLink",
    "RootContext",
    "discover_roots",
    "markdown_links",
    "select_root",
    "validate_protocol",
]
