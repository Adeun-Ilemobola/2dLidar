# embedded/bus.py
# Very small "event bus" so embedded modules can publish events,
# and UI can subscribe to them (through the Qt controller).

from __future__ import annotations
from typing import Callable, List
from shared.protocol import Event


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[Callable[[Event], None]] = []

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        """Register a callback to receive events."""
        self._subscribers.append(callback)

    def publish(self, event: Event) -> None:
        """Send an event to all subscribers."""
        for cb in self._subscribers:
            cb(event)
