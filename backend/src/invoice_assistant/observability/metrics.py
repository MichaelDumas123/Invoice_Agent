"""Small PII-safe process metrics for the development API."""

from collections import Counter
from collections.abc import Mapping
from threading import Lock


class Metrics:
    """In-memory counters only; production must export via an approved metrics backend."""

    def __init__(self) -> None:
        self._values: Counter[tuple[str, tuple[tuple[str, str], ...]]] = Counter()
        self._lock = Lock()

    def increment(self, name: str, labels: Mapping[str, str] | None = None) -> None:
        safe_labels = tuple(sorted((key, value) for key, value in (labels or {}).items() if key in {"route", "method", "status", "result", "provider"}))
        with self._lock:
            self._values[(name, safe_labels)] += 1

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return [{"name": name, "labels": dict(labels), "value": value} for (name, labels), value in self._values.items()]


metrics = Metrics()
