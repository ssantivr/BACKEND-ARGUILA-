import time
from threading import Lock

from app.data_structures import Queue

MAX_FAILED_ATTEMPTS = 5
WINDOW_SECONDS = 60.0
MAX_TRACKED_KEYS = 10000


def now() -> float:
    return time.monotonic()


class LoginLimiter:
    def __init__(
        self,
        max_attempts: int = MAX_FAILED_ATTEMPTS,
        window_seconds: float = WINDOW_SECONDS,
        max_keys: int = MAX_TRACKED_KEYS,
    ) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._max_keys = max_keys
        self._failures: dict[str, Queue[float]] = {}
        self._lock = Lock()

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            failures = self._drop_expired(key)
            return failures is not None and failures.is_full()

    def record_failure(self, key: str) -> None:
        with self._lock:
            failures = self._drop_expired(key)

            if failures is None:
                if len(self._failures) >= self._max_keys:
                    self._purge_expired()

                if len(self._failures) >= self._max_keys:
                    return

                failures = Queue(capacity=self._max_attempts)
                self._failures[key] = failures

            if not failures.is_full():
                failures.enqueue(now())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()

    def _purge_expired(self) -> None:
        for key in list(self._failures):
            self._drop_expired(key)

    def _drop_expired(self, key: str) -> Queue[float] | None:
        failures = self._failures.get(key)

        if failures is None:
            return None

        limit = now() - self._window_seconds

        while not failures.is_empty() and failures.peek() <= limit:
            failures.dequeue()

        if failures.is_empty():
            del self._failures[key]
            return None

        return failures


login_limiter = LoginLimiter()
