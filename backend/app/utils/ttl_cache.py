import time
from typing import Generic, Hashable, TypeVar

KT = TypeVar("KT", bound=Hashable)
VT = TypeVar("VT")

_SENTINEL = object()


class TTLCache(Generic[KT, VT]):
    """In-process TTL cache. Thread-safety relies on the Python GIL for dict ops."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        # key -> (value, expires_at_monotonic)
        self._store: dict[KT, tuple[VT, float]] = {}

    def get(self, key: KT) -> tuple[bool, VT | None]:
        """Return (hit, value). hit=False on miss or expiry."""
        entry = self._store.get(key, _SENTINEL)  # type: ignore[arg-type]
        if entry is _SENTINEL:
            return False, None
        value, expires_at = entry  # type: ignore[misc]
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return False, None
        return True, value

    def put(self, key: KT, value: VT) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate(self, key: KT) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
