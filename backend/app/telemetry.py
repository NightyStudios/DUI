from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import perf_counter
from typing import Iterator
from contextlib import contextmanager


class Telemetry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._latency_totals_ms: dict[str, float] = defaultdict(float)

    @contextmanager
    def track(self, operation: str) -> Iterator[None]:
        start = perf_counter()
        ok = False
        try:
            yield
            ok = True
        finally:
            elapsed_ms = (perf_counter() - start) * 1000
            with self._lock:
                self._counters[f"{operation}.total"] += 1
                self._counters[f"{operation}.{'ok' if ok else 'error'}"] += 1
                self._latency_totals_ms[operation] += elapsed_ms

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            avg_latency_ms = {
                op: (self._latency_totals_ms[op] / self._counters.get(f"{op}.total", 1))
                for op in self._latency_totals_ms
            }
            return {
                "counters": dict(self._counters),
                "avg_latency_ms": avg_latency_ms,
            }


TELEMETRY = Telemetry()
