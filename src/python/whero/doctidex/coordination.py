"""Command-level coordination for RuntimeStore recovery and GitCache access."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Self

from whero.doctidex.git_cache import GitCache, GitCacheWriteTransaction
from whero.doctidex.repair import repair_core
from whero.doctidex.store.files import FileLock, StoreFailure
from whero.doctidex.store.runtime import RepairRequired, RuntimeStore

_MAX_REPAIR_ATTEMPTS = 3


class StoreCoordinator(AbstractContextManager["StoreCoordinator"]):
    """Keep one CLI command serialized while coordinating RuntimeStore repair."""

    def __init__(self, store: RuntimeStore, cache: GitCache) -> None:
        self.store = store
        self.cache = cache
        self._command_lock = FileLock(store.workspace_path / ".command.lock", store="runtime")

    def __enter__(self) -> Self:
        self._command_lock.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self._command_lock.release()
        return False

    def run[T](self, operation: Callable[[], T]) -> T:
        """Run a RuntimeStore operation, repairing residual journals between retries."""

        attempts = 0
        while True:
            try:
                return operation()
            except RepairRequired as signal:
                if attempts >= _MAX_REPAIR_ATTEMPTS:
                    raise _retry_exhausted(self.store, attempts, signal.transaction_ids) from signal
                attempts += 1
                self.repair()

    def with_repository[T](self, git_url: str, operation: Callable[[Path], T]) -> T:
        """Run cache-backed work with a cache transaction covering all external actions.

        A published cache hit starts in ReadOnly mode. If the RuntimeStore operation reports
        repair while that transaction is active, the ReadOnly transaction is exited first and a
        Write transaction performs repair before the operation is retried. A cache miss starts in
        Write mode and can reuse that same transaction for repair.
        """

        repair_attempts = 0
        with self.cache.read_only_transaction() as transaction:
            repository = transaction.find(git_url)
            if repository is not None:
                try:
                    return operation(repository)
                except RepairRequired:
                    repair_attempts = 1

        with self.cache.write_transaction() as transaction:
            repository = transaction.load(git_url)
            if repair_attempts:
                repair_core(self.store, transaction)
            return self._run_with_cache_transaction(
                transaction,
                lambda: operation(repository),
                repair_attempts=repair_attempts,
            )

    def repair(self) -> None:
        """Run explicit maintenance in a fresh GitCache Write transaction."""

        with self.cache.write_transaction() as transaction:
            repair_core(self.store, transaction)

    def _run_with_cache_transaction[T](
        self,
        transaction: GitCacheWriteTransaction,
        operation: Callable[[], T],
        *,
        repair_attempts: int = 0,
    ) -> T:
        attempts = repair_attempts
        while True:
            try:
                return operation()
            except RepairRequired as signal:
                if attempts >= _MAX_REPAIR_ATTEMPTS:
                    raise _retry_exhausted(self.store, attempts, signal.transaction_ids) from signal
                attempts += 1
                repair_core(self.store, transaction)


def _retry_exhausted(store: RuntimeStore, attempts: int, transaction_ids: tuple[str, ...]) -> StoreFailure:
    return StoreFailure(
        store="runtime",
        phase="recovery-repair",
        state_path=store.transactions_path,
        details={"attempts": attempts, "transaction-ids": list(transaction_ids)},
    )


__all__ = ["StoreCoordinator"]
