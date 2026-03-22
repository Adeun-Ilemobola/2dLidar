"""Main application window. ui/main_window.py"""
from collections.abc import Callable
from typing import Literal
import queue
import customtkinter as ctk
import tkinter as tk

from embedded.worker import HardwareWorker
from shared.config import SystemConfig, scanRange
from shared.protocol import (
    CalibrationResult,
    MinMaxResult,
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
)

from ui.components.AngleStatusPanel import AngleStatusPanel
from ui.components.motor_panel import MotorPanel
from ui.components.ramge_pane import RangePane
from ui.components.SmartCanvas import SmartCanvas


class MainWindow(ctk.CTk):
    def __init__(self, title: str = "Pi Control Panel", size: tuple[int, int] = (1000, 900)):
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
        }

        # Root container
        self.root_frame = ctk.CTkFrame(self, fg_color=self.ui_colors["surface"])
        self.root_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open MotorConfig", command=self.open_motor_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
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
        self.motor_card.grid_columnconfigure(0, weight=1)
        self.motor_card.grid_columnconfigure(1, weight=1)

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
        self.scan_card = ctk.CTkFrame(
            self.root_frame,
            fg_color=self.ui_colors["card"],
            border_width=1,
            border_color=self.ui_colors["border"],
            corner_radius=14,
        )
        self.scan_card.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        self.scan_card.grid_columnconfigure(0, weight=1)

        self.scan_toggle = ctk.CTkButton(
            self.scan_card,
            text="Start Scan",
            height=40,
            corner_radius=12,
            command=self.run_scan,
        )
        self.reset_toggle = ctk.CTkButton(
            self.scan_card,
            text="Reset",
            height=40,
            corner_radius=12,
            command=self.reset,
        )
        self.Calibration_toggle = ctk.CTkButton(
            self.scan_card,
            text="Start Calibration",
            height=40,
            corner_radius=12,
            command=lambda: self.send_cmd(startCalibration()),
        )

        self.scan_toggle.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        self.reset_toggle.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.Calibration_toggle.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

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

    def clear_canvas(self) -> None:
        self.smart_canvas.clear()

    def enable_widget(self, on: bool) -> None:
        state = "normal" if on else "disabled"
        self.motorX.setDisable(state)
        self.motorY.setDisable(state)
        self.s_range.setDisable(state)


    def set_scan_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        fg = "#1f6aa5" if enabled else "#D21010"
        self.scan_toggle.configure(state=state, fg_color=fg)
        self.reset_toggle.configure(state=state, fg_color=fg)
        self.Calibration_toggle.configure(state=state, fg_color=fg)

    def disable_scan_controls(self, on: bool) -> None:
        self.set_scan_controls_enabled(on)

    def run_scan(self) -> None:
        if self.scan_in_progress:
            self.scan_in_progress = False
            self.send_cmd(StopScan())
            self.scan_toggle.configure(text="Start Scan")
            self.enable_widget(True)
        else:
            self.send_cmd(StartScan())
            self.scan_in_progress = True
            self.scan_toggle.configure(text="Stop Scan")
            self.enable_widget(False)

    def reset(self) -> None:
        self.scan_in_progress = False
        self.send_cmd(StopScan())
        self.scan_toggle.configure(text="Start Scan")
        self.enable_widget(True)

    def send_cmd(self, cmd: Command) -> None:
        # Update local UI state for certain commands,
        # but still always forward the command to the worker.
        match cmd:
            case continuous_mode(continuous_mode=a):
                self.is_continuous_mode = a
                self.set_scan_controls_enabled(not a)

            case findMinMax(axis=_, action=mode):
                if mode == "start":
                    self.set_scan_controls_enabled(False)
                    self.enable_widget(False)
                elif mode == "stop":
                    self.set_scan_controls_enabled(True)
                    self.enable_widget(True)

            case _:
                pass

        self.cmd_q.put(cmd)

    def open_motor_config(self) -> None:
        if self._motor_config_win is not None:
            try:
                if self._motor_config_win.winfo_exists():
                    self._motor_config_win.deiconify()
                    self._motor_config_win.lift()
                    self._motor_config_win.focus()
                    return
            except Exception:
                self._motor_config_win = None

        self._motor_config_win = MotorConfigPanel(self, send_cmd=self.send_cmd)
        self._motor_config_win.lift()
        self._motor_config_win.focus()

    def _forward_minmax_to_config_window(self, ev: MinMaxResult) -> None:
        if self._motor_config_win is None:
            return

        try:
            if self._motor_config_win.winfo_exists():
                self._motor_config_win.update_result(ev)
            else:
                self._motor_config_win = None
        except Exception:
            self._motor_config_win = None

    def poll_events(self) -> None:
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
                    self.smart_canvas.Update_point_grid(ev.points)

                case MinMaxResult():
                    print(
                        f"MinMaxResult: max_angle={ev.max_angle}, "
                        f"min_angle={ev.min_angle}, distant={ev.distant}, status={ev.status}"
                    )

                    if str(ev.status).lower() == "done":
                        self.set_scan_controls_enabled(True)
                        self.enable_widget(True)

                    self._forward_minmax_to_config_window(ev)

                case CalibrationResult():
                    if ev.success:
                        print("Calibration successful!")
                        self.set_scan_controls_enabled(True)
                        self.enable_widget(True)
                        self.scan_toggle.configure(text="Start Scan")
                        self.reset_toggle.configure(text="Reset")
                    else:
                        print(f"Calibration failed: {ev.message}")
                        self.set_scan_controls_enabled(False)
                        self.enable_widget(False)

                case _:
                    pass

        self.after(self.system_config.tick_ms, self.poll_events)

    def on_close(self) -> None:
        try:
            self.worker.shutdown()
        except Exception:
            pass
        self.destroy()


class MotorConfigPanel(ctk.CTkToplevel):
    def __init__(self, master: MainWindow, send_cmd: Callable[[Command], None], **kwargs):
        super().__init__(master, **kwargs)

        self.app = master
        self.send_cmd = send_cmd

        self.title("Motor Configuration")
        self.geometry("850x450")
        self.grid_columnconfigure(0, weight=1)

        self.panelX = AngleStatusPanel(self, command=self.send_mode, Axis="x")
        self.panelX.grid(row=0, column=0, padx=12, pady=12, sticky="ew")

        self.panelY = AngleStatusPanel(self, command=self.send_mode, Axis="y")
        self.panelY.grid(row=1, column=0, padx=12, pady=12, sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.transient(master)
        self.grab_set()

    def send_mode(self, axis: Literal["x", "y"], mode: Literal["stop", "start"]) -> None:
        self.send_cmd(findMinMax(axis=axis, action=mode))

        if axis == "x":
            self.panelY.dis("disabled" if mode == "start" else "normal")
        elif axis == "y":
            self.panelX.dis("disabled" if mode == "start" else "normal")

    def update_result(self, ev: MinMaxResult) -> None:
        print(
            f"MinMaxResult: max_angle={ev.max_angle}, "
            f"min_angle={ev.min_angle}, distant={ev.distant}, status={ev.status}"
        )

        if ev.axis == "x":
            self.panelX.set_maximum_angle(ev.max_angle)
            self.panelX.set_minimum_angle(ev.min_angle)
            self.panelX.set_range_cm(ev.distant)
            self.panelX.set_status(ev.status)

        elif ev.axis == "y":
            self.panelY.set_maximum_angle(ev.max_angle)
            self.panelY.set_minimum_angle(ev.min_angle)
            self.panelY.set_range_cm(ev.distant)
            self.panelY.set_status(ev.status)

        if str(ev.status).lower() == "done":
            self.panelX.dis("normal")
            self.panelY.dis("normal")

    def on_close(self) -> None:
        self.app._motor_config_win = None
        self.destroy()