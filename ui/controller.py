# ui/controller.py
# This file is the bridge between Qt (UI thread) and embedded System (worker thread).
# It also converts embedded events into Qt signals so widgets can update safely.

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot, QThread

from embedded.bus import EventBus
from embedded.system import System
from shared.protocol import Command, Event


class SystemWorker(QObject):
    """
    Lives in a background thread.
    Owns the embedded System.
    """
    event_received = Signal(object)  # emits Event objects to UI
    log = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        # Create embedded stuff inside the worker (so it stays on this thread)
        self.bus = EventBus()
        self.system = System(self.bus)

        # When embedded publishes an event, we forward it via Qt signal
        self.bus.subscribe(self._on_event)

    def _on_event(self, event: Event) -> None:
        # This is called in the worker thread.
        # Emitting a signal is safe: Qt will deliver it to UI thread.
        self.event_received.emit(event)


    @Slot()
    def configure(self) -> None:
        self.log.emit("Configuring system...")
        self.system.configure_all()
        self.log.emit("System configured.")

    @Slot(object)
    def handle_command(self, cmd: Command) -> None:
        # This slot receives commands from UI.
        self.system.handle(cmd)


class Controller(QObject):
    """
    Lives in UI thread.
    Owns the worker thread and exposes simple methods/signals for UI widgets.
    """
    event_received = Signal(object)  # forward Event objects
    log = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        self.thread = QThread()
        self.worker = SystemWorker()
        self.worker.moveToThread(self.thread)

        # Forward worker signals to UI
        self.worker.event_received.connect(self.event_received)
        self.worker.log.connect(self.log)

        self.thread.start()

        # Optionally configure system at startup
        # (queued call—runs in worker thread)
        self.worker.configure()

    def send(self, cmd: Command) -> None:
        """
        UI calls this to send commands.
        We call the worker slot. Qt queues it to the worker thread safely.
        """
        self.worker.handle_command(cmd)

    def shutdown(self) -> None:
        """Clean shutdown (important!)."""
        self.thread.quit()
        self.thread.wait()
