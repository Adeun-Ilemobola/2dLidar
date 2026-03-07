# shared/time.py
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Timer:
    duration_s: Optional[float] = None     # None = run forever
    tick_s: float = 0.020                  # your system tick (20ms)

    running: bool = False
    elapsed_s: float = 0.0
    _next_tick: float = 0.0

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        now = time.perf_counter()
        self._next_tick = now + self.tick_s

    def stop(self) -> None:
        self.running = False

    def reset(self) -> None:
        self.elapsed_s = 0.0
        self.running = False
        self._next_tick = 0.0

    def tick(self) -> None:
        if not self.running:
            return

        now = time.perf_counter()

        # Catch up if we missed ticks (e.g., long command handling)
        while now >= self._next_tick and self.running:
            self.elapsed_s += self.tick_s
            self._next_tick += self.tick_s

            if self.duration_s is not None and self.elapsed_s >= self.duration_s:
                self.running = False
                break

    def done(self) -> bool:
        self.tick()  # Ensure we update elapsed time before checking
        return (self.duration_s is not None) and (not self.running) and (self.elapsed_s >= self.duration_s)
