from __future__ import annotations

import traceback
import uuid

from .storage import cache_root


def write_diagnostic(error: BaseException) -> str:
    identifier = uuid.uuid4().hex[:12]
    directory = cache_root() / "diagnostics"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{identifier}.log"
    path.write_text("".join(traceback.format_exception(error)), encoding="utf-8")
    return identifier
