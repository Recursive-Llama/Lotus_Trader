from __future__ import annotations

from typing import Callable, Dict, List


_subscribers: Dict[str, List[Callable[[dict], None]]] = {}


def subscribe(event_type: str, handler: Callable[[dict], None]) -> None:
    _subscribers.setdefault(event_type, []).append(handler)


def emit(event_type: str, payload: dict) -> None:
    for h in _subscribers.get(event_type, []):
        try:
            h(payload)
        except Exception:
            # Best-effort
            pass


