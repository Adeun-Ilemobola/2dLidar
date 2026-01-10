import queue
import customtkinter as ctk

from embedded.worker import HardwareWorker
from shared.protocol import MotorState, Log, ScanProgress , Command

from ui.components.motor_panel import MotorPanel  # make sure this is the CTk version, not Qt QWidget version


class MainWindow(ctk.CTk):
    def __init__(self, title="Pi Control Panel", size=(1000, 700)):
        super().__init__()
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")

        # Queues
        self.cmd_q: "queue.Queue" = queue.Queue()
        self.event_q: "queue.Queue" = queue.Queue()

        # Worker thread
        self.worker = HardwareWorker(self.cmd_q, self.event_q)
        self.worker.start()

        # Layout containers
        self.root_frame = ctk.CTkFrame(self)
        self.root_frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.top_row = ctk.CTkFrame(self.root_frame)
        self.top_row.pack(fill="x", padx=8, pady=8)

        # Motor panels (pass send_cmd function)
        self.motorX = MotorPanel(self.top_row, axis="x", send_cmd=self.send_cmd)
        self.motorY = MotorPanel(self.top_row, axis="y", send_cmd=self.send_cmd)

        self.motorX.pack(side="left", padx=8, pady=8)
        self.motorY.pack(side="left", padx=8, pady=8)

        # Start polling events (CTk replacement for QTimer)
        self.after(16, self.poll_events)

        # Proper close handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def send_cmd(self, cmd:Command):
        self.cmd_q.put(cmd)

    def poll_events(self):
        while True:
            try:
                ev = self.event_q.get_nowait()
            except queue.Empty:
                break

            if isinstance(ev, MotorState):
                if ev.axis == "x":
                    self.motorX.apply_motor_state(
                        angle_deg=ev.angle_deg,
                        offset_deg=ev.offset_deg,
                        enabled=ev.enabled,
                    )
                elif ev.axis == "y":
                    self.motorY.apply_motor_state(
                        angle_deg=ev.angle_deg,
                        offset_deg=ev.offset_deg,
                        enabled=ev.enabled,
                    )

            elif isinstance(ev, Log):
                print(ev.message)

            elif isinstance(ev, ScanProgress):
                # update a progress bar later
                pass

        # Schedule next poll
        self.after(16, self.poll_events)

    def on_close(self):
        try:
            self.worker.shutdown()
        except Exception:
            pass
        self.destroy()
