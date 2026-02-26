"""Main application window. ui/main_window.py"""
from collections.abc import Callable
from typing import Literal
import queue
import customtkinter as ctk
import tkinter as tk

from embedded.worker import HardwareWorker
from shared.config import SystemConfig, scanRange
from shared.protocol import (
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
)

from ui.components.AngleStatusPanel import AngleStatusPanel
from ui.components.motor_panel import MotorPanel
from ui.components.ramge_pane import RangePane
from ui.components.SmartCanvas import SmartCanvas


class MainWindow(ctk.CTk):
    def __init__(self, title: str = "Pi Control Panel", size=(1000, 900)):
        super().__init__()
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")

        # Queues
        self.cmd_q: "queue.Queue[Command]" = queue.Queue()
        self.event_q: "queue.Queue" = queue.Queue()

        self.SystemConfig = SystemConfig()
        self.scanRangeMas = scanRange()

        # # Worker thread
        self.worker = HardwareWorker(
            self.cmd_q,
            self.event_q,
            scanRange_mas=self.scanRangeMas,
            SystemConfig_mas=self.SystemConfig
        )
        self.worker.start()

        # State
        self.scan_progress = False
        self._motor_config_win: "MotorConfigPanel | None" = None

        # -------------------------
        # UI theme
        # -------------------------
        self.uiColors = {
            "surface": ("#F2F3F5", "#0F1115"),
            "card": ("#FFFFFF", "#171A20"),
            "border": ("#D7DADF", "#2A2F37"),
        }

        # Root container
        self.root_frame = ctk.CTkFrame(self, fg_color=self.uiColors["surface"])
        self.root_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open MotorConfig", command=self.open_motor_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="Config", menu=file_menu)
        self.config(menu=menubar)

        # -------------------------
        # Root grid: top row + canvas row
        # -------------------------
        self.root_frame.grid_rowconfigure(0, weight=0)  # top row stays compact
        self.root_frame.grid_rowconfigure(1, weight=1)  # canvas fills remaining space

        self.root_frame.grid_columnconfigure(0, weight=3)  # motors
        self.root_frame.grid_columnconfigure(1, weight=1)  # scan buttons
        self.root_frame.grid_columnconfigure(2, weight=2)  # range panel

        # ============================================================
        # TOP LEFT CARD: Motors
        # ============================================================
        self.motorCard = ctk.CTkFrame(
            self.root_frame,
            fg_color=self.uiColors["card"],
            border_width=1,
            border_color=self.uiColors["border"],
            corner_radius=14,
        )
        self.motorCard.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self.motorCard.grid_columnconfigure(0, weight=1)
        self.motorCard.grid_columnconfigure(1, weight=1)
        self.motorCard.grid_rowconfigure(0, weight=0)

        self.motorX = MotorPanel(
            self.motorCard,
            axis="x",
            send_cmd=self.send_cmd,
            range_min_max=self.scanRangeMas.range_X_max,
        )
        self.motorX.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.motorY = MotorPanel(
            self.motorCard,
            axis="y",
            send_cmd=self.send_cmd,
            range_min_max=self.scanRangeMas.range_Y_Max,
            offset_min_max=self.scanRangeMas.Y_Min_Max,
        )
        self.motorY.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        # ============================================================
        # TOP MIDDLE CARD: Scan controls
        # ============================================================
        self.scanCard = ctk.CTkFrame(
            self.root_frame,
            fg_color=self.uiColors["card"],
            border_width=1,
            border_color=self.uiColors["border"],
            corner_radius=14,
        )
        self.scanCard.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        self.scanCard.grid_columnconfigure(0, weight=1)

        self.scan_toggle = ctk.CTkButton(
            self.scanCard,
            text="Start Scan",
            height=40,
            corner_radius=12,
            command=self.run_scan,
        )

        self.reset_toggle = ctk.CTkButton(
            self.scanCard,
            text="Reset",
            height=40,
            corner_radius=12,
            command=self.reset,
        )

        self.scan_toggle.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        self.reset_toggle.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        # ============================================================
        # TOP RIGHT CARD: Range sensor
        # ============================================================
        self.rangeCard = ctk.CTkFrame(
            self.root_frame,
            fg_color=self.uiColors["card"],
            border_width=1,
            border_color=self.uiColors["border"],
            corner_radius=14,
        )
        self.rangeCard.grid(row=0, column=2, sticky="ew", padx=8, pady=8)
        self.rangeCard.grid_columnconfigure(0, weight=1)

        self.s_range = RangePane(self.rangeCard, send_cmd=self.send_cmd, width=340, height=150)
        self.s_range.grid(row=0, column=0, sticky="ew", padx=12, pady=12)

        # ============================================================
        # BOTTOM: Smart Canvas
        # ============================================================
        dummy_point_states = [[PointState(x=j, y=i, distant=-1) for j in range(40)] for i in range(40)]

        self.smart_canvas = SmartCanvas(
            self.root_frame,
            width=size[0],
            height=size[1] - 200,
            point_states=dummy_point_states,
            bg="White",
        )
        self.smart_canvas.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=8, pady=8)

        # Start polling events
        self.after(self.SystemConfig.tick_ms, self.poll_events)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # -------------------------
    # UI state helpers
    # -------------------------
    def enable_widget(self, on: bool) -> None:
        state = "normal" if on else "disabled"
        self.motorX.setDisable(state)
        self.motorY.setDisable(state)
        self.s_range.setDisable(state)

    def set_scan_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.scan_toggle.configure(state=state, fg_color="#1f6aa5" if enabled else "#D21010")
        self.reset_toggle.configure(state=state, fg_color="#1f6aa5" if enabled else "#D21010")

    # Backwards-compatible alias (if any other code still calls this)
    def disable_scan_controls(self, on: bool) -> None:
        self.set_scan_controls_enabled(on)

    # -------------------------
    # Commands
    # -------------------------
    def run_scan(self) -> None:
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
        self.scan_toggle.configure(text="Start Scan")
        self.enable_widget(True)

    def send_cmd(self, cmd: Command) -> None:
        # Continuous mode disables scan/reset while active
        if isinstance(cmd, continuous_mode):
            self.set_scan_controls_enabled(not cmd.continuous_mode)

        # Min/Max mode should disable scan/reset and manual motor/range controls
        if isinstance(cmd, findMinMax) and cmd.action == "start":
            self.set_scan_controls_enabled(False)
            self.enable_widget(False)

        if isinstance(cmd, findMinMax) and cmd.action == "stop":
            self.set_scan_controls_enabled(True)
            self.enable_widget(True)

        self.cmd_q.put(cmd)

    def open_motor_config(self) -> None:
        print("Opening motor config window...")

        if self._motor_config_win is not None:
            try:
                if self._motor_config_win.winfo_exists():
                    print("Motor config window already open, focusing...")
                    self._motor_config_win.deiconify()
                    self._motor_config_win.lift()
                    self._motor_config_win.focus()
                    return
            except Exception:
                self._motor_config_win = None

        self._motor_config_win = MotorConfigPanel(self, send_cmd=self.send_cmd)
        self._motor_config_win.lift()
        self._motor_config_win.focus()

    def poll_events(self) -> None:
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
                self.scan_progress = ev.start
                if ev.start:
                    self.enable_widget(False)
                    self.scan_toggle.configure(text="Stop Scan")
                else:
                    self.enable_widget(True)
                    self.scan_toggle.configure(text="Start Scan")

            elif isinstance(ev, getRange):
                self.s_range.update_range(ev.distance)

            elif isinstance(ev, ScanAreaGrid):
                self.smart_canvas.Update_point_grid(ev.points)

            elif isinstance(ev, MinMaxResult):
                # Auto-restore UI when backend reports completion
                if str(ev.status).lower() == "done":
                    self.set_scan_controls_enabled(True)
                    self.enable_widget(True)

                if self._motor_config_win is not None:
                    try:
                        if self._motor_config_win.winfo_exists():
                            self._motor_config_win.Update(ev)
                        else:
                            self._motor_config_win = None
                    except Exception:
                        self._motor_config_win = None

        self.after(self.SystemConfig.tick_ms, self.poll_events)

    def on_close(self) -> None:
        try:
            self.worker.shutdown()
            pass
        except Exception:
            pass
        self.destroy()


# ============================================================
# Motor Configuration Window
# ============================================================
class MotorConfigPanel(ctk.CTkToplevel):
    def __init__(self, master: MainWindow, send_cmd: Callable[[Command], None], **kwargs):
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

        # Keep on top of the main window / modal-ish
        self.transient(master)
        self.grab_set()

    def sendMode(self, a: Literal["x", "y"], mode: Literal["stop", "start"]) -> None:
        self.send_cmd(findMinMax(axis=a, action=mode))

        # Prevent both axes from running Min/Max at the same time from UI
        if a == "x":
            self.panelY.dis("disabled" if mode == "start" else "normal")
        elif a == "y":
            self.panelX.dis("disabled" if mode == "start" else "normal")

    def Update(self, ev: MinMaxResult) -> None:
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
        print("Closing MotorConfigPanel")
        self.app._motor_config_win = None
        self.destroy()