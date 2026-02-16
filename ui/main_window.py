"""Main application window. Ui/main_window.py """
# import queue
from collections.abc import Callable
from typing import  Literal

from curses.panel import panel
import random
import queue
import customtkinter as ctk
import tkinter as tk


from embedded.worker import HardwareWorker
from shared.config import SystemConfig, scanRange, scanRange
from shared.protocol import MinMaxResult, MotorState, Log, ScanProgress , Command , StopScan , StartScan , PointState, continuous_mode, findMinMax, getRange , ScanAreaGrid ,Event

from ui.components.AngleStatusPanel import AngleStatusPanel
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


        
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open MotorConfig", command=self.open_motor_config)

       
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="Config", menu=file_menu)
        self.config(menu=menubar)


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
        self.motorX = MotorPanel(self.top_row, axis="x", send_cmd=self.send_cmd , range_min_max = self.scanRangeMas.range_X_max )
        self.motorX.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))

        self.motorY = MotorPanel(self.top_row, axis="y", send_cmd=self.send_cmd , range_min_max = self.scanRangeMas.range_Y_Max , offset_min_max=self.scanRangeMas.Y_Min_Max)
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


        self._motor_config_win = None  # will hold the motor config window if it's open


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
        if isinstance(cmd, findMinMax) and cmd.action == "start":
            self.disable_scan_controls(True)
            self.enable_widget(False)
        if isinstance(cmd, findMinMax) and cmd.action == "stop":
            self.disable_scan_controls(False)
            self.enable_widget(True)

        self.cmd_q.put(cmd)
    def open_motor_config(self):
         print("Opening motor config window...")
         if self._motor_config_win and self._motor_config_win.winfo_exists():
             print("Motor config window already open, focusing...")
             self._motor_config_win.focus()
             return

         self._motor_config_win = MotorConfigPanel(self, send_cmd=self.send_cmd)
         self._motor_config_win.focus()

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
            if isinstance(ev, MinMaxResult):
                if self._motor_config_win:
                    self._motor_config_win.Update(ev)
         

        # Schedule next poll
        self.after(self.SystemConfig.tick_ms, self.poll_events)

    def on_close(self):
        try:
            self.worker.shutdown()
        except Exception:
            pass
        self.destroy()


# ----------



class MotorConfigPanel(ctk.CTkToplevel):
    def __init__(self, master,  send_cmd:Callable[[Command], None] , **kwargs):
        super().__init__(master, **kwargs)

       

        self.app = master
        self.send_cmd = send_cmd

        self.title("Motor Configuration")
        self.geometry("850x450")

        # Layout
        self.grid_columnconfigure(0, weight=1)

        self.panelX = AngleStatusPanel(self, command=self.sendMode, Axis="x")
        self.panelX.grid(row=0, column=0, padx=12, pady=12, sticky="ew")

        self.panelY = AngleStatusPanel(self, command=self.sendMode, Axis="y")
        self.panelY.grid(row=1, column=0, padx=12, pady=12, sticky="ew")
        # Close handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Optional: keep on top of the main window
        self.transient(master)
        self.grab_set()
    def sendMode(self, a:Literal["x", "y"] , mode:Literal["stop", "start"]):
        self.send_cmd(findMinMax(axis=a, action=mode))
        if a == "x":
            self.panelY.dis("disabled" if mode == "start" else "normal")
        if a == "y":
            self.panelX.dis("disabled" if mode == "start" else "normal")
        
    def Update(self , ev:MinMaxResult):
            print(f"MinMaxResult: max_angle={ev.max_angle}, min_angle={ev.min_angle},  distant={ev.distant}")
            if ev.axis == "x":
                self.panelX.set_maximum_angle(ev.max_angle)
                self.panelX.set_minimum_angle(ev.min_angle)
                self.panelX.set_range_cm(ev.distant)
                self.panelX.set_status(ev.status)
            if ev.axis == "y":
                self.panelY.set_maximum_angle(ev.max_angle)
                self.panelY.set_minimum_angle(ev.min_angle)
                self.panelY.set_range_cm(ev.distant)
                self.panelY.set_status(ev.status)
            

    def on_close(self):
        print("Closing MotorConfigPanel")
        self.destroy()
