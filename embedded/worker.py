# embedded/worker.py
from __future__ import annotations
import queue
import threading
from typing import Optional

from shared.config import SystemConfig
from shared.protocol import Command, Event, Log
from embedded.system import System

class HardwareWorker(threading.Thread):
    def __init__(self, cmd_q: "queue.Queue[Command]", event_q: "queue.Queue[Event]"):
        super().__init__(daemon=True)
        self.cmd_q = cmd_q
        self.event_q = event_q
        self.stop_event = threading.Event()
        self.SystemConfig = SystemConfig()

        self.system: Optional[System] = None

    def run(self) -> None:
        try:
            # Create ALL hardware stuff here (on the worker thread)
            self.system = System(event_q=self.event_q)

            self.event_q.put(Log("Hardware worker started."))

            while not self.stop_event.is_set():
                # 1)  (non-blocking)
                try:
                    cmd = self.cmd_q.get(timeout=self.SystemConfig.tick_ms / 1000  )  # 20ms tick
                    self.system.handle(cmd)
                except queue.Empty:
                    pass

                # 2) let the system do ongoing work (scan stepping, etc.)
                self.system.tick()

        except Exception as e:
            self.event_q.put(Log(f"Worker crashed: {e!r}"))

    def shutdown(self) -> None:
        self.stop_event.set()
