"""Main application window. ui/main_window.py"""
from collections.abc import Callable
from typing import Literal
import queue
import customtkinter as ctk
import tkinter as tk

from embedded.worker import HardwareWorker
from shared.config import SystemConfig, scanRange
from shared.protocol import (
    Axis,
    CalibrationResult,
    MotorState,
    Log,
    ScanProgress,
    Command,
    StopScan,
    StartScan,
    PointState,
    continuous_mode,
    findMinMax,
    getRange,
    ScanAreaGrid,
    startCalibration,
    sendMinMaxResult
)

from ui.components.AngleStatusPanel import AngleStatusPanel
from ui.components.motor_panel import MotorPanel
from ui.components.ramge_pane import RangePane
from ui.components.SmartCanvas import SmartCanvas


class MainWindow(ctk.CTk):
    def __init__(self, title: str = "Pi Control Panel", size: tuple[int, int] = (1200, 1550)):
        super().__init__()
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")

        # Queues
        self.cmd_q: queue.Queue[Command] = queue.Queue()
        self.event_q: queue.Queue = queue.Queue()

        # Shared config/state
        self.system_config = SystemConfig()
        self.scan_range = scanRange()

        # Worker thread
        self.worker = HardwareWorker(
            self.cmd_q,
            self.event_q,
            scanRange_mas=self.scan_range,
            SystemConfig_mas=self.system_config,
        )
        self.worker.start()

        # State
        self.scan_in_progress = False
        self.is_continuous_mode = False
        self._motor_config_win: "MotorConfigPanel | None" = None
        self.selected_motor: Literal["x", "y"] | None = None
        self.manual_control_step= 1.0

        # UI theme
        self.ui_colors = {
            "surface": ("#F2F3F5", "#0F1115"),
            "card": ("#FFFFFF", "#171A20"),
            "border": ("#D7DADF", "#2A2F37"),
        }
        self.panel_colors = {
            "surface": ("#F2F3F5", "#14161A"),
            "card": ("#FFFFFF", "#1C1F24"),
            "border": ("#D7DADF", "#2A2F37"),
            "text": ("#111318", "#E9EDF2"),
            "mutedText": ("#5A6472", "#AAB3BF"),
            "accent": ("#1F6AA5", "#1F6AA5"),
            "accentHover": ("#195A8D", "#195A8D"),
            "disabledFill": ("#E6E9EE", "#20242B"),
            "disabledText": ("#9AA3AF", "#6B7280"),
        }

        self.fonts = {
            "title": ctk.CTkFont(size=16, weight="bold"),
            "small": ctk.CTkFont(size=12, weight="normal"),
            "metricLabel": ctk.CTkFont(size=12, weight="bold"),
            "metricValue": ctk.CTkFont(size=18, weight="bold"),
            "button": ctk.CTkFont(size=13, weight="bold"),
            "middle": ctk.CTkFont(size=14, weight="bold"),
            "large": ctk.CTkFont(size=16, weight="bold"),
        }

        # Root container
        self.root_frame = ctk.CTkFrame(self, fg_color=self.ui_colors["surface"])
        self.root_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open MotorConfig", command=lambda: print("TODO: Open MotorConfig window"))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        file_menu.add_command( label="restart Worker", command=self.restart_worker)
        menubar.add_cascade(label="Config", menu=file_menu)
        self.config(menu=menubar)

        # Root grid
        self.root_frame.grid_rowconfigure(0, weight=0)
        self.root_frame.grid_rowconfigure(1, weight=1)
        self.root_frame.grid_rowconfigure(2, weight=0)

        self.root_frame.grid_columnconfigure(0, weight=3)
        self.root_frame.grid_columnconfigure(1, weight=1)
        self.root_frame.grid_columnconfigure(2, weight=2)

        # Motors card
        self.motor_card = ctk.CTkFrame(
            self.root_frame,
            fg_color=self.ui_colors["card"],
            border_width=1,
            border_color=self.ui_colors["border"],
            corner_radius=14,
        )
        self.motor_card.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self.motor_card.grid_rowconfigure(0, weight=1)
        self.motor_card.grid_columnconfigure(0, weight=1)
        self.motor_card.grid_columnconfigure(1, weight=1)

     # Manual Control Frame (clean redesign)
        self.ManualControlFrame = ctk.CTkFrame(
            self.motor_card,
            fg_color=self.panel_colors["surface"],
            border_width=1,
            border_color=self.panel_colors["border"],
            corner_radius=12,
        )
        self.ManualControlFrame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        self.ManualControlFrame.grid_columnconfigure(0, weight=1)
        self.ManualControlFrame.grid_columnconfigure(1, weight=0)

        # LEFT SIDE (text/info)
        self.ManualControlTextFrame = ctk.CTkFrame(self.ManualControlFrame, fg_color="transparent")
        self.ManualControlTextFrame.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)

        self.ManualControlLabel = ctk.CTkLabel(
            self.ManualControlTextFrame,
            text="Manual Control",
            font=self.fonts["title"],
            text_color=self.panel_colors["text"],
        )
        self.ManualControlLabel.grid(row=0, column=0, sticky="w")

        self.ManualControlInfoLabel = ctk.CTkLabel(
            self.ManualControlTextFrame,
            text="Press X or Y to select motor. Press Esc to exit.",
            font=self.fonts["small"],
            text_color=self.panel_colors["mutedText"],
            wraplength=360,
            justify="left",
        )
        self.ManualControlInfoLabel.grid(row=1, column=0, sticky="w", pady=(4, 10))

        # status row
        self.ManualControlStatusFrame = ctk.CTkFrame(self.ManualControlTextFrame, fg_color="transparent")
        self.ManualControlStatusFrame.grid(row=2, column=0, sticky="w")

        self.ManualControlAxisLabel = ctk.CTkLabel(
            self.ManualControlStatusFrame,
            text="Axis: None",
            font=self.fonts["large"],
            text_color=self.panel_colors["text"],
        )
        self.ManualControlAxisLabel.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.ManualControlStepLabel = ctk.CTkLabel(
            self.ManualControlStatusFrame,
            text="Step: 1.0°",
            font=self.fonts["large"],
            text_color=self.panel_colors["text"],
        )
        self.ManualControlStepLabel.grid(row=0, column=1, sticky="w")

        # RIGHT SIDE (input)
        self.ManualControlInputFrame = ctk.CTkFrame(self.ManualControlFrame, fg_color="transparent")
        self.ManualControlInputFrame.grid(row=0, column=1, sticky="e", padx=(8, 12), pady=12)

        self.ManualControlInputStep = ctk.CTkEntry(
            self.ManualControlInputFrame,
            width=120,
            placeholder_text="Step (°)",
            font=self.fonts["large"],
            fg_color=self.panel_colors["card"],
            border_color=self.panel_colors["border"],
            text_color=self.panel_colors["text"],
        )
        self.ManualControlInputStep.grid(row=0, column=0, padx=(0, 6))
        self.ManualControlInputStep.delete(0, "end")
        self.ManualControlInputStep.insert(0, str(self.manual_control_step))  # default value

        self.ManualControlInputStep.bind(
        "<Return>",
        lambda event: self.on_step_enter(event),
    )

        self.ManualControlInputStep.bind("<FocusIn>", lambda event: self.ManualControlInputStep.delete("0", "end"))
        self.ManualControlInputStep.bind("<FocusOut>", lambda event: self.ManualControlInputStep.insert("0", str(self.manual_control_step)))
        self.bind("<Key>", self.handle_keypress)




        self.motorX = MotorPanel(
            self.motor_card,
            axis="x",
            send_cmd=self.send_cmd,
            range_min_max=(
                self.scan_range.Axis_X["defaultScanRange"]["min"],
                self.scan_range.Axis_X["defaultScanRange"]["max"],
            ),
            offset_min_max=(
                self.scan_range.Axis_X["uiLimit"]["min"],
                self.scan_range.Axis_X["uiLimit"]["max"],
            ),
        )
        self.motorX.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.motorY = MotorPanel(
            self.motor_card,
            axis="y",
            send_cmd=self.send_cmd,
            range_min_max=(
                self.scan_range.Axis_Y["defaultScanRange"]["min"],
                self.scan_range.Axis_Y["defaultScanRange"]["max"],
            ),
            offset_min_max=(
                self.scan_range.Axis_Y["uiLimit"]["min"],
                self.scan_range.Axis_Y["uiLimit"]["max"],
            ),
        )
        self.motorY.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        # Scan controls card
        # Scan controls card
        self.scan_card = ctk.CTkFrame(
            self.root_frame,
            fg_color=self.ui_colors["card"],
            border_width=1,
            border_color=self.ui_colors["border"],
            corner_radius=14,
    )
        self.scan_card.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        # 2-column layout inside scan_card
        self.scan_card.grid_columnconfigure(0, weight=1)   # scan range side
        self.scan_card.grid_rowconfigure(0, weight=0)   # buttons side
        self.scan_card.grid_rowconfigure(1, weight=0)

        # ----------------------------
        # Bottom SIDE: Scan range panel
        # ----------------------------
        self.scan_range_panel = ctk.CTkFrame(
            self.scan_card,
            fg_color="transparent",
        )
        self.scan_range_panel.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 8))
        self.scan_range_panel.grid_columnconfigure(0, weight=1)

        self.scan_range_title = ctk.CTkLabel(
            self.scan_range_panel,
            text="Scan Range",
            font=self.fonts["title"],
            text_color=self.panel_colors["text"],
            anchor="w",
        )
        self.scan_range_title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        # inner box for range values
        self.scan_range_box = ctk.CTkFrame(
            self.scan_range_panel,
            fg_color=self.panel_colors["surface"],
            border_width=1,
            border_color=self.panel_colors["border"],
            corner_radius=12,
        )
        self.scan_range_box.grid(row=1, column=0, sticky="ew")
        self.scan_range_box.grid_columnconfigure(0, weight=1)

        # X row
        self.scan_x_frame = ctk.CTkFrame(self.scan_range_box, fg_color="transparent")
        self.scan_x_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        self.scan_x_frame.grid_columnconfigure(1, weight=1)

        self.scan_x_label = ctk.CTkLabel(
            self.scan_x_frame,
            text="X",
            width=24,
            font=self.fonts["button"],
            text_color=self.panel_colors["text"],
            anchor="w",
        )
        self.scan_x_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.scan_x_value = ctk.CTkLabel(
            self.scan_x_frame,
            text=f'{self.scan_range.Axis_X["uiLimit"]["min"]} - {self.scan_range.Axis_X["uiLimit"]["max"]}',
            fg_color=self.panel_colors["card"],
            corner_radius=10,
            height=34,
            anchor="w",
            padx=12,
            font=self.fonts["small"],
            text_color=self.panel_colors["text"],
        )
        self.scan_x_value.grid(row=0, column=1, sticky="ew")

        # Y row
        self.scan_y_frame = ctk.CTkFrame(self.scan_range_box, fg_color="transparent")
        self.scan_y_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.scan_y_frame.grid_columnconfigure(1, weight=1)

        self.scan_y_label = ctk.CTkLabel(
            self.scan_y_frame,
            text="Y",
            width=24,
            font=self.fonts["button"],
            text_color=self.panel_colors["text"],
            anchor="w",
        )
        self.scan_y_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.scan_y_value = ctk.CTkLabel(
            self.scan_y_frame,
            text=f'{self.scan_range.Axis_Y["uiLimit"]["min"]} - {self.scan_range.Axis_Y["uiLimit"]["max"]}',
            fg_color=self.panel_colors["card"],
            corner_radius=10,
            height=34,
            anchor="w",
            padx=12,
            font=self.fonts["small"],
            text_color=self.panel_colors["text"],
        )
        self.scan_y_value.grid(row=0, column=1, sticky="ew")

        # ----------------------------
        # top SIDE: Buttons panel
        # ----------------------------
        self.scan_button_panel = ctk.CTkFrame(
            self.scan_card,
            fg_color="transparent",
        )
        self.scan_button_panel.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        # make first 2 buttons side-by-side, last one full width
        self.scan_button_panel.grid_columnconfigure(0, weight=1)
        self.scan_button_panel.grid_columnconfigure(1, weight=1)

        self.scan_toggle = ctk.CTkButton(
                self.scan_button_panel,
                text="Start Scan",
                height=40,
                corner_radius=12,
                font=self.fonts["button"],
                command=self.run_scan,
        )
        self.scan_toggle.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))

        self.reset_toggle = ctk.CTkButton(
                self.scan_button_panel,
                text="Reset",
                height=40,
                corner_radius=12,
                font=self.fonts["button"],
                command=self.reset,
        )
        self.reset_toggle.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))

        self.calibration_toggle = ctk.CTkButton(
                self.scan_button_panel,
                text="Start Calibration",
                height=40,
                corner_radius=12,
                font=self.fonts["button"],
                command=lambda: self.send_cmd(startCalibration()),
        )
        self.calibration_toggle.grid(row=1, column=0, columnspan=2, sticky="ew")

            # Range card
        self.range_card = ctk.CTkFrame(
                self.root_frame,
                fg_color=self.ui_colors["card"],
                border_width=1,
                border_color=self.ui_colors["border"],
                corner_radius=14,
        )
        self.range_card.grid(row=0, column=2, sticky="ew", padx=8, pady=8)
        self.range_card.grid_columnconfigure(0, weight=1)

        self.s_range = RangePane(self.range_card, send_cmd=self.send_cmd, width=340, height=150)
        self.s_range.grid(row=0, column=0, sticky="ew", padx=12, pady=12)

            # Smart canvas
        dummy_point_states = [
                [PointState(x=j, y=i, distant=-1) for j in range(40)]
                for i in range(40)
            ]

        self.smart_canvas = SmartCanvas(
                self.root_frame,
                send_cmd=self.send_cmd,
                width=size[0],
                height=size[1] - 200,
                point_states=dummy_point_states,
                bg="white",
            )
        self.smart_canvas.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=8, pady=8)

        self.clear_btn = ctk.CTkButton(
                self.root_frame,
                text="Clear Canvas",
                height=36,
                corner_radius=10,
                font=self.fonts["button"],
                fg_color=self.panel_colors["accent"],
                hover_color=self.panel_colors["accentHover"],
                text_color="white",
                command=self.clear_canvas,
        )
        self.clear_btn.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))

            # Start polling events
        self.after(self.system_config.tick_ms, self.poll_events)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    def on_step_enter(self, event):
        self.update_step()
        self.focus_set()
    def handle_keypress(self, event):
        if event.keysym in ["x", "X"]:
            self.selected_motor = "x"
            self.ManualControlAxisLabel.configure(text="Selected Axis: X")
        elif event.keysym in ["y", "Y"]:
            self.selected_motor = "y"
            self.ManualControlAxisLabel.configure(text="Selected Axis: Y")
        elif event.keysym == "Escape":
            self.selected_motor = None
            self.ManualControlAxisLabel.configure(text="Selected Axis: None")
        elif event.keysym == "Up":
            self.increase_step()
        elif event.keysym == "Down":
            self.decrease_step()


    def update_step(self):
        step_str = self.ManualControlInputStep.get()
        try:
            step_val = float(step_str)
            self.manual_control_step = step_val
            self.ManualControlStepLabel.configure(text=f"Step: {step_val}°")
            self.ManualControlInputStep.delete(0, "end")
            self.ManualControlInputStep.insert(0, str(step_val))
        except ValueError:
            tk.messagebox.showerror("Invalid Input", "Please enter a valid number for the step.")

    def increase_step(self):
        if self.selected_motor is not None:
            if self.selected_motor == "x":
                self.motorX.increment(self.manual_control_step)
            else:
                self.motorY.increment(self.manual_control_step)
    def decrease_step(self):
        if self.selected_motor is not None:
            if self.selected_motor == "x":
                self.motorX.decrement(self.manual_control_step)
            else:
                self.motorY.decrement(self.manual_control_step)


    def Change_scan_RangeX(self, max , min) -> None:
        self.scan_x_value.configure(
            text=f'{min:.2f} -   {max:.2f}'
        )
    def Change_scan_RangeY(self, max , min) -> None:
        self.scan_y_value.configure(
            text=f'{min:.2f} -   {max:.2f}'
        )
    def clear_canvas(self) -> None:
        self.smart_canvas.clear()

    def enable_widget(self, on: bool) -> None:

        if on:
            self.scan_toggle.configure(state="normal", fg_color=self.panel_colors["accent"])
            self.reset_toggle.configure(state="normal", fg_color=self.panel_colors["accent"])
            self.calibration_toggle.configure(state="normal", fg_color=self.panel_colors["accent"])
            self.motorX.EnablePanel()
            self.motorY.EnablePanel()
            self.s_range.Enable_Range()
        else:
            self.scan_toggle.configure(state="disabled", fg_color=self.panel_colors["disabledFill"])
            self.reset_toggle.configure(state="disabled", fg_color=self.panel_colors["disabledFill"])
            self.calibration_toggle.configure(state="disabled", fg_color=self.panel_colors["disabledFill"])
            self.motorX.DisablePanel()
            self.motorY.DisablePanel()
            self.s_range.Disable_Range()
       
      
        
        
    # specific method to disable scan controls when scan starts or stops, can be called from worker or other places if needed
        
    def onScanStart(self ):
        self.motorX.DisablePanel()
        self.motorY.DisablePanel()
        self.s_range.Disable_Range()
        self.Disable_Calibration_Toggle()
    
    def onScanStop(self):
        self.motorX.EnablePanel()
        self.motorY.EnablePanel()
        self.s_range.Enable_Range()

        self.Enable_Calibration_Toggle()

    def Disable_scan_Toggle(self):
        self.scan_toggle.configure(state="disabled", fg_color="#D21010")
    
    def Enable_scan_Toggle(self):
        self.scan_toggle.configure(state="normal", fg_color="#1f6aa5")
    
    
    def Disable_reset_Toggle(self):
        self.reset_toggle.configure(state="disabled", fg_color="#D21010")
    
    def Enable_reset_Toggle(self):
        self.reset_toggle.configure(state="normal", fg_color="#1f6aa5")
    
    
    def Disable_Calibration_Toggle(self):
        self.calibration_toggle.configure(state="disabled", fg_color="#D21010")
        
    def Enable_Calibration_Toggle(self):
        self.calibration_toggle.configure(state="normal", fg_color="#1f6aa5")
    
    def onCalibrationStart(self):
        self.Disable_scan_Toggle()
        self.Disable_reset_Toggle()
        self.Disable_Calibration_Toggle()
        self.motorX.DisablePanel()
        self.motorY.DisablePanel()
        self.s_range.Disable_Range()

    def onCalibrationStop(self):
        self.Enable_scan_Toggle()
        self.Enable_reset_Toggle()
        self.Enable_Calibration_Toggle()
        self.motorX.EnablePanel()
        self.motorY.EnablePanel()
        self.s_range.Enable_Range()
  
    def run_scan(self) -> None:
        if self.scan_in_progress:
            self.scan_in_progress = False
            self.send_cmd(StopScan())
            self.scan_toggle.configure(text="Start Scan")
            self.onScanStop()
        else:
            self.send_cmd(StartScan())
            self.scan_in_progress = True
            self.scan_toggle.configure(text="Stop Scan")
            self.onScanStart()

    def reset(self) -> None:
        self.scan_in_progress = False
        self.send_cmd(StopScan())
        self.scan_toggle.configure(text="Start Scan")
        self.onScanStop()
        self.smart_canvas.clear()
        

    def send_cmd(self, cmd: Command) -> None:
        # Update local UI state for certain commands,
        # but still always forward the command to the worker.
        match cmd:
            case continuous_mode(continuous_mode=a):
                self.is_continuous_mode = a

            case findMinMax(axis=_, action=mode):
                if mode == "start":
                    self.onScanStop()
                elif mode == "stop":
                    self.onScanStart()

            case _:
                pass

        self.cmd_q.put(cmd)

    def restart_worker(self):
        """Kills existing worker (if any) and starts a fresh one."""
        self.send_cmd(StopScan()) 
        
        if hasattr(self, 'worker') and self.worker.is_alive():
            self.worker.shutdown()
            self.worker.join(timeout=1.0) # Wait for it to die
        
        # Clear the queues to prevent old commands from flooding the new system
        while not self.cmd_q.empty():
            try: self.cmd_q.get_nowait()
            except: break
            
        self.worker = HardwareWorker(
            self.cmd_q,
            self.event_q,
            scanRange_mas=self.scan_range,
            SystemConfig_mas=self.system_config,
        )
        self.worker.start()
        self.enable_widget(True) # Re-enable UI
        tk.messagebox.showinfo("System", "Hardware Worker Restarted.")

    def poll_events(self) -> None:
        if hasattr(self, 'worker') and not self.worker.is_alive() and not self.worker.stop_event.is_set():
             self.calibration_toggle.configure(text="HARDWARE DISCONNECTED", fg_color="red")
             return
        while True:
            try:
                ev = self.event_q.get_nowait()
            except queue.Empty:
                break

            match ev:
                case MotorState():
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

                case Log():
                    print(ev.message)

                case ScanProgress():
                    self.scan_in_progress = ev.start
                    if ev.start:
                        self.enable_widget(False)
                        self.scan_toggle.configure(text="Stop Scan")
                    else:
                        self.enable_widget(True)
                        self.scan_toggle.configure(text="Start Scan")

                case getRange():
                    self.s_range.update_range(ev.distance)

                case ScanAreaGrid():
                    print("Updating grid...")
                    print(
                        f"Received grid with {len(ev.points)} points. Sample point: {ev.points[len(ev.points)//2]}"
                    )
                    self.smart_canvas.Update_point_grid(ev.points)

                case sendMinMaxResult():
                    data = ev 
                    Ymin = data.Ymin
                    Ymax = data.Ymax
                    Xmin = data.Xmin
                    Xmax = data.Xmax
                                    
                    self.Change_scan_RangeX(Xmin, Xmax)
                    self.Change_scan_RangeY(Ymin, Ymax)
                    self.motorX.changLimit(min=Xmin, max=Xmax)
                    self.motorY.changLimit(min=Ymin, max=Ymax)

                    self.smart_canvas.update_grid_range((Xmin, Xmax), (Ymin, Ymax), 1)
                   

                case CalibrationResult():
                    match ev.status:
                        case "started":
                            print("UI: Locking for calibration...")
                            self.onCalibrationStart()
                            self.calibration_toggle.configure(text="Calibrating...", fg_color="#D21010")

                        case "finished":
                            print("UI: Calibration complete!")
                            self.onCalibrationStop() # Unlocks all buttons
                            self.calibration_toggle.configure(text="Start Calibration", fg_color="#1f6aa5")
                            # Optionally show a popup
                            tk.messagebox.showinfo("Success", ev.message)

                        case "failed":
                            print(f"UI: Calibration aborted: {ev.message}")
                            self.onCalibrationStop()
                            self.calibration_toggle.configure(text="Start Calibration", fg_color="#1f6aa5")

                        
                case _:
                    pass

        self.after(self.system_config.tick_ms, self.poll_events)

    def on_close(self) -> None:
        try:
            self.worker.shutdown()
        except Exception:
            pass
        self.destroy()


