"""Main application window. Ui/main_window.py """
# import queue
import random
import queue
import customtkinter as ctk

from embedded.worker import HardwareWorker
from shared.config import SystemConfig, scanRange, scanRange
from shared.protocol import MotorState, Log, ScanProgress , Command , StopScan , StartScan , PointState, continuous_mode, getRange , ScanAreaGrid

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
        self.SystemConfig = SystemConfig()

        #State verbals
        self.scan_progress = False
        self.step = 2
        self.scanRangeMas = scanRange()
        # Layout containers
        self.root_frame = ctk.CTkFrame(self)
        self.root_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Root grid sizing: 3 top columns + canvas row
        self.root_frame.grid_rowconfigure(0, weight=0)
        self.root_frame.grid_rowconfigure(1, weight=1)

        self.root_frame.grid_columnconfigure(0, weight=3)  # left panel bigger
        self.root_frame.grid_columnconfigure(1, weight=1)  # middle
        self.root_frame.grid_columnconfigure(2, weight=1)  # right

        # ----------------------------
        # LEFT PANEL: motors + config
        # ----------------------------
        self.top_row = ctk.CTkFrame(self.root_frame)
        self.top_row.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.top_row.grid_columnconfigure(0, weight=1)
        self.top_row.grid_columnconfigure(1, weight=1)

        # scan config ON TOP (row 0)
        self.scan_config = ctk.CTkFrame(self.top_row)
        self.scan_config.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))

        self.step_entry = TextBox(
            parent=self.scan_config,
            width=150,
            height=40,
            label="Step Size (deg):",
            placeholder="2",
            set_callback=self.update_step_size
        )
        self.step_entry.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        # motors BELOW (row 1)
        self.motorX = MotorPanel(self.top_row, axis="x", send_cmd=self.send_cmd , range_min_max = self.scanRangeMas.range_X_max)
        self.motorX.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))

        self.motorY = MotorPanel(self.top_row, axis="y", send_cmd=self.send_cmd , range_min_max = self.scanRangeMas.range_Y_Max)
        self.motorY.grid(row=1, column=1, sticky="nsew", padx=8, pady=(4, 8))

   

        # ----------------------------
        # MIDDLE PANEL:  the scan controls
        # ----------------------------
        self.middle_panel = ctk.CTkFrame(self.root_frame)
        self.middle_panel.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.middle_panel.grid_columnconfigure(0, weight=1)

        self.scan_toggle = ctk.CTkButton(self.middle_panel, text="Start scan", command=self.run_scam)
        self.reset_toggle = ctk.CTkButton(self.middle_panel, text="Rest", command=self.reset)

        self.scan_toggle.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.reset_toggle.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 8))


        # ----------------------------
        # RIGHT PANEL: the range finder
        # ----------------------------
        self.right_panel = ctk.CTkFrame(self.root_frame)
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)
        self.right_panel.grid_columnconfigure(0, weight=1)

        self.s_range = RangePane(self.right_panel, send_cmd=self.send_cmd, width=400, height=150)
        self.s_range.grid(row=0, column=0, sticky="ew", padx=8, pady=8)


        # ----------------------------
        # Smart Canvas :  the scan area display
        # ----------------------------
        dummy_point_states = [
            [PointState(x=j, y=i, distant=-1) for j in range(40)]
            for i in range(40)
        ]
        self.smart_canvas = SmartCanvas(
            self.root_frame,
            width=size[0] ,
            height=size[1] - 200,
            point_states=dummy_point_states,
            bg="White"
        )
        self.smart_canvas.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=8, pady=8)


        # Start polling events
        self.after(self.SystemConfig.tick_ms, self.poll_events)

        # Proper close handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def run_scam(self):
        if self.scan_progress:
            self.scan_progress = False
            self.send_cmd(StopScan())
            self.scan_toggle.configure(text="Start Scan")
            self.enable_widget(True)
        else:
            self.send_cmd(StartScan())
            self.scan_progress = True
            self.scan_toggle.configure(text="Stop Scan")
            self.enable_widget(False)
    def reset(self) -> None:
        self.scan_progress = False
        self.send_cmd(StopScan())
    def enable_widget(self, on:bool):
        state = "normal" if on else "disabled"
        self.motorX.setDisable(state)
        self.motorY.setDisable(state)
        self.s_range.setDisable(state)
        self.step_entry.setDisable(state)
    def disable_scan_controls(self, on:bool):
        state = "normal" if on else "disabled"
        self.scan_toggle.configure(state=state  , fg_color="#1f6aa5" if on else "#D21010")
        self.reset_toggle.configure(state=state , fg_color="#1f6aa5" if on else "#D21010")

    
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
        if isinstance(cmd, continuous_mode):
            self.disable_scan_controls(not cmd.continuous_mode)
            
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

            if isinstance(ev, Log):
                print(ev.message)

            if isinstance(ev, PointState):
                print(f"PointState: x={ev.x}, y={ev.y}, distant={ev.distant}")
                pass
            if isinstance(ev, ScanProgress):
                print(f"""
                    Scan Progress: ({ev.current / ev.total * 100:.2f}%)
                    current time = {ev.current}
                    total time   = {ev.total}
                    mode start   = {ev.start}
                    """)
               
                if ev.start:
                    self.enable_widget(False)
                else :
                    self.enable_widget(True)
                    self.scan_toggle.configure(text="Start Scan")
                pass
            if isinstance(ev, getRange):
                self.s_range.update_range(ev.distance)
                print(f"Range distance: {ev.distance} mm")
            if isinstance(ev, ScanAreaGrid):
                self.smart_canvas.update_point_states(ev.points)
           
                

        # Schedule next poll
        self.after(self.SystemConfig.tick_ms, self.poll_events)

    def on_close(self):
        try:
            self.worker.shutdown()
            pass
        except Exception:
            pass
        self.destroy()
