"""Main application window. Ui/main_window.py """
# import queue
import random
import queue
import customtkinter as ctk

from embedded.worker import HardwareWorker
from shared.protocol import MotorState, Log, ScanProgress , Command , StopScan , StartScan , PointState, getRange , ScanAreaGrid

from ui.components.motor_panel import MotorPanel
from ui.components.ramge_pane import RangePane
from ui.components.SmartCanvas import SmartCanvas
from ui.components.TextBox import TextBox




class MainWindow(ctk.CTk):
    def __init__(self, title="Pi Control Panel", size=(1000, 900)):
        super().__init__()
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")

        # Queues
        self.cmd_q: "queue.Queue" = queue.Queue()
        self.event_q: "queue.Queue" = queue.Queue()

        # Worker thread
        self.worker = HardwareWorker(self.cmd_q, self.event_q)
        self.worker.start()

        #State verbals
        self.scan_progress = False
        self.step = 2

        # Layout containers
        self.root_frame = ctk.CTkFrame(self)
        self.root_frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.top_row = ctk.CTkFrame(self.root_frame)
        self.top_row.grid(row=0, column=0, sticky="nsew")

        # Motor panels (pass send_cmd function)
        self.motorX = MotorPanel(self.top_row, axis="x", send_cmd=self.send_cmd)
        self.motorY = MotorPanel(self.top_row, axis="y", send_cmd=self.send_cmd)

        self.scan_cognfig = ctk.CTkFrame(self.top_row)

        self.step_entry = TextBox(self.scan_cognfig, width=150, height=40, label="Step Size (deg):", placeholder="2", set=self.update_step_size)

        self.motorX.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.motorY.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        self.step_entry.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.scan_cognfig.grid(row=1, column=2, sticky="nsew", padx=8, pady=8)
      
        self.configure_panel = ctk.CTkFrame(self.root_frame)
        self.configure_panel.grid(row=0, column=2, sticky="nsew" , padx=8)

        self.scan_toggle = ctk.CTkButton(self.configure_panel, text="Start scan", command=self.run_scam)
        self.reset_toggle = ctk.CTkButton(self.configure_panel, text="Rest", command=self.reset)

        self.s_range = RangePane(self.root_frame, send_cmd=self.send_cmd , width=400 , height=150)
        self.s_range.grid(row=0, column=3, sticky="ew", pady=8)
        self.scan_toggle.grid(row=0, column=0, padx=8, pady=8)
        self.reset_toggle.grid(row=1, column=0, padx=8, pady=8)

        # Smart Canvas
        # Dummy point states for testing
        dummy_point_states = [
           [PointState(x=j, y=i, distant=random.uniform(0, 400)) for j in range(40)]
           for i in range(40)
        ]
        self.smart_canvas = SmartCanvas(self.root_frame, width=400, height=400, point_states=dummy_point_states , bg="White")
        self.smart_canvas.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=8, pady=8)

        # Start polling events
        self.after(16,self.poll_events)

        # Proper close handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def run_scam(self):
        if self.scan_progress:
            self.scan_progress = False
            self.send_cmd(StopScan())
            self.scan_toggle.configure(text="Start Scan")
        else:
            self.send_cmd(StartScan())
            self.scan_progress = True
            self.scan_toggle.configure(text="Stop Scan")
    def reset(self) -> None:
        self.scan_progress = False
        self.send_cmd(StopScan())
    def enable_widget(on:bool):
        if on:
            pass
        else:
            pass
    
    def update_step_size(self , step_size: str):
        if not step_size:
            return
        try:
            step = float(step_size)
        except ValueError:
            print(f"Invalid step size: {step_size}")
            return
        self.step = step
        
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

            elif isinstance(ev, PointState):
                print(f"PointState: x={ev.x}, y={ev.y}, distant={ev.distant}")
                pass
            elif isinstance(ev, ScanProgress):
                print(f"Scan progress: {ev.current}/{ev.total}")
                pass
            elif isinstance(ev, getRange):
                self.s_range.update_range(ev.distance)
            elif isinstance(ev, ScanAreaGrid):
                self.smart_canvas.update_point_states(ev.point_states)
           
                

        # Schedule next poll
        self.after(16, self.poll_events)

    def on_close(self):
        try:
            self.worker.shutdown()
        except Exception:
            pass
        self.destroy()
