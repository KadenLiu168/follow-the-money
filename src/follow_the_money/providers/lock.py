"""Exclusive full-run output-root collection lock.

Design section 2:

- V1 uses one exclusive Feed collection lock rooted in the explicit output
  root, acquired before reading latest or capturing a cutoff and held through
  provider collection and Feed publication.
- Cooperating CLI processes that share a provider/rate scope must share that
  output root; cross-root concurrent use of the same scope is unsupported.
- Lock waiting uses the same injected monotonic deadline, occupies no
  provider-request concurrency slot, and fails typed
  ``collection_lock_timeout`` with no provider call or artifact if the
  deadline cannot admit acquisition.
"""

from __future__ import annotations

import errno
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Self

LOCK_FILENAME = ".collection.lock"


class CollectionLockError(ValueError):
    """Collection lock acquisition failed (typed at the orchestration boundary)."""


class CollectionLock:
    """Cross-process exclusive lock on the output root (fcntl.flock)."""

    def __init__(
        self,
        output_root: Path,
        *,
        timeout_seconds: float = 60.0,
        monotonic_now: Callable[[], float] | None = None,
    ) -> None:
        self._path = Path(output_root) / LOCK_FILENAME
        self._timeout = timeout_seconds
        self._now = monotonic_now or time.monotonic
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def acquire(self) -> Self:
        """Acquire the exclusive lock, failing typed on deadline expiry."""
        if self._fd is not None:
            return self
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o600)
        deadline = self._now() + self._timeout
        while True:
            try:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if self._now() >= deadline:
                    os.close(fd)
                    raise CollectionLockError("collection_lock_timeout") from None
                time.sleep(0.05)
            except OSError as exc:
                os.close(fd)
                if exc.errno == errno.ENOTSUP:
                    raise CollectionLockError("collection lock primitive unavailable") from exc
                raise CollectionLockError(f"collection lock failed: {exc}") from exc
        self._fd = fd
        return self

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            import fcntl

            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> Self:
        return self.acquire()

    def __exit__(self, *exc: object) -> None:
        self.release()
