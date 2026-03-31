# embedded/worker.py
from __future__ import annotations
import queue
import threading
from typing import Optional

from shared.config import SystemConfig , scanRange
from shared.protocol import Command, Event, Log
from embedded.system import System

# embedded/worker.py

class HardwareWorker(threading.Thread):
    def __init__(self, cmd_q, event_q, scanRange_mas, SystemConfig_mas):
        super().__init__(daemon=True)
        self.cmd_q = cmd_q
        self.event_q = event_q
        self.stop_event = threading.Event()
        self.SystemConfig = SystemConfig_mas
        self.scanRange = scanRange_mas
        self.error_state = False # Track if we crashed

    def run(self) -> None:
        try:
            self.system = System(event_q=self.event_q, scanRange_mas=self.scanRange)
            self.event_q.put(Log("Hardware worker started."))

            while not self.stop_event.is_set():
                try:
                    # Use a shorter timeout for responsiveness to shutdown
                    cmd = self.cmd_q.get(timeout=0.01) 
                    self.system.handle(cmd)
                except queue.Empty:
                    pass

                self.system.tick()
        except Exception as e:
            self.error_state = True
            self.event_q.put(Log(f"CRITICAL: Worker crashed: {e}"))
        finally:
            self.event_q.put(Log("Worker thread exiting."))

    def shutdown(self) -> None:
        self.stop_event.set()