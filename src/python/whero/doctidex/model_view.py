"""Backward-compatible exports for work-model views and tree scans."""

from whero.doctidex.managed_symlinks import ManagedSymlink, scan_managed_symlinks
from whero.doctidex.markdown_links import (
    MarkdownLink,
    parse_inline_annotation,
    resolve_inline_annotation_boundary,
    resolve_local_link,
    scan_markdown_links,
)
from whero.doctidex.store.model_view import RuntimeModelView, RuntimeRepairModelView, RuntimeWriteModelView

__all__ = [
    "ManagedSymlink",
    "MarkdownLink",
    "RuntimeModelView",
    "RuntimeRepairModelView",
    "RuntimeWriteModelView",
    "parse_inline_annotation",
    "resolve_inline_annotation_boundary",
    "resolve_local_link",
    "scan_managed_symlinks",
    "scan_markdown_links",
]
