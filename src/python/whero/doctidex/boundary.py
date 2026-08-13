"""Boundary-set command workflows."""

from __future__ import annotations

from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import BoundaryPoint
from whero.doctidex.model_view import RuntimeModelView, RuntimeWriteModelView
from whero.doctidex.paths import normalize_repo_path
from whero.doctidex.store.runtime import RuntimeStore


def add(store: RuntimeStore, paths: list[str]) -> None:
    with store.write_transaction() as transaction:
        view = RuntimeWriteModelView(transaction)
        normalized = [normalize_repo_path(path, parameter="--path") for path in paths]
        view.upsert_custom_boundary_points(BoundaryPoint(type="custom", path=path) for path in normalized)


def remove(store: RuntimeStore, paths: list[str]) -> None:
    with store.write_transaction() as transaction:
        view = RuntimeWriteModelView(transaction)
        normalized = [normalize_repo_path(path, parameter="--path") for path in paths]
        for path in normalized:
            if view.custom_boundary_point(path) is None:
                derived = view.boundary_point(path)
                if derived is not None:
                    raise CommandFailure(
                        code="boundary-point.remove.prohibited",
                        summary="A derived boundary point cannot be removed by boundary-set.",
                        subject={"kind": "boundary-point", "path": path},
                        details={"boundary-type": derived.type, "managed-by": derived.type},
                    )
        view.remove_custom_boundary_points(normalized)


def parse(store: RuntimeStore, paths: list[str]) -> list[dict[str, object]]:
    with store.read_only_transaction() as transaction:
        view = RuntimeModelView(transaction)
        normalized = [normalize_repo_path(path, parameter="--path") for path in paths]
        results: list[dict[str, object]] = []
        for path, point in zip(normalized, view.first_boundaries(normalized), strict=True):
            result: dict[str, object] = {"path": path, "has-boundary": point is not None}
            if point is not None:
                result.update({"boundary-point": point.path, "boundary-type": point.type})
            results.append(result)
        return results
