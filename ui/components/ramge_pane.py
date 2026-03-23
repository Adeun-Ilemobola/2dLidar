import customtkinter as ctk
from typing_extensions import Literal

from shared.protocol import Axis, callRange, continuous_mode, getRange  # use


class RangePane(ctk.CTkFrame):
    def __init__(self, parent, send_cmd, *, width=360, height=120):
        super().__init__(parent, width=width, height=height)

        # =========================
        # State (logic unchanged)
        # =========================
        self.send_cmd = send_cmd
        self.Disable = False
        self.Continuous_ranging = False  # fixed naming/typo so it actually works

        self.range_value = ctk.StringVar(value="N/A")

        # =========================
        # Component-local styling (no global theme changes)
        # =========================
        colors = {
            "surface": ("#F2F3F5", "#14161A"),
            "card": ("#FFFFFF", "#1C1F24"),
            "border": ("#D7DADF", "#2A2F37"),
            "text": ("#111318", "#E9EDF2"),
            "mutedText": ("#5A6472", "#AAB3BF"),
            "accent": ("#1F6AA5", "#1F6AA5"),
            "accentHover": ("#195A8D", "#195A8D"),
            "danger": ("#D21010", "#D21010"),
            "dangerHover": ("#B10D0D", "#B10D0D"),
            "readout": ("#F7F8FA", "#171A20"),
            "disabledFill": ("#E6E9EE", "#20242B"),
            "disabledText": ("#9AA3AF", "#6B7280"),
        }

        fonts = {
            "title": ctk.CTkFont(size=16, weight="bold"),
            "subtle": ctk.CTkFont(size=12, weight="normal"),
            "value": ctk.CTkFont(size=22, weight="bold"),
            "button": ctk.CTkFont(size=13, weight="bold"),
        }

        # Outer container appearance
        self.configure(
            fg_color=colors["surface"],
            corner_radius=16,
            border_width=1,
            border_color=colors["border"],
        )

        # =========================
        # Layout grid
        # =========================
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # =========================
        # Header row
        # =========================
        headerRow = ctk.CTkFrame(self, fg_color="transparent")
        headerRow.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        headerRow.grid_columnconfigure(0, weight=1)
        headerRow.grid_columnconfigure(1, weight=0)

        # Title
        self.title = ctk.CTkLabel(
            headerRow,
            text="Range Sensor",
            font=fonts["title"],
            text_color=colors["text"],
            anchor="w",
        )
        self.title.grid(row=0, column=0, sticky="w")

        # Mode badge (UI-only indicator)
        self.mode_badge = ctk.CTkLabel(
            headerRow,
            text="IDLE",
            font=fonts["subtle"],
            text_color=colors["mutedText"],
            anchor="e",
        )
        self.mode_badge.grid(row=0, column=1, sticky="e")

        # =========================
        # Readout block
        # =========================
        readoutCard = ctk.CTkFrame(
            self,
            fg_color=colors["readout"],
            corner_radius=12,
            border_width=1,
            border_color=colors["border"],
        )
        readoutCard.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        readoutCard.grid_columnconfigure(0, weight=1)

        readoutLabel = ctk.CTkLabel(
            readoutCard,
            text="Current distance",
            font=fonts["subtle"],
            text_color=colors["mutedText"],
            anchor="w",
        )
        readoutLabel.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

        self.range_label = ctk.CTkLabel(
            readoutCard,
            textvariable=self.range_value,
            font=fonts["value"],
            text_color=colors["text"],
            anchor="w",
        )
        self.range_label.grid(row=1, column=0, sticky="w", padx=10, pady=(2, 8))

        # =========================
        # Controls row
        # =========================
        controlsRow = ctk.CTkFrame(self, fg_color="transparent")
        controlsRow.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        controlsRow.grid_columnconfigure(0, weight=1)
        controlsRow.grid_columnconfigure(1, weight=1)

        # Primary action: single read
        self.refresh_button = ctk.CTkButton(
            controlsRow,
            text="Get Range",
            command=self.on_refresh_button,
            height=36,
            corner_radius=10,
            font=fonts["button"],
            fg_color=colors["accent"],
            hover_color=colors["accentHover"],
            text_color="white",
        )
        self.refresh_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        # Toggle action: continuous mode
        self.ranging_button = ctk.CTkButton(
            controlsRow,
            text="Start Continuous",
            command=self.on_range_event,
            height=36,
            corner_radius=10,
            font=fonts["button"],
            fg_color=colors["card"],            # secondary look by default
            hover_color=colors["readout"],
            text_color=colors["text"],
            border_width=1,
            border_color=colors["border"],
        )
        self.ranging_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.pack_propagate(False)  # respect fixed size

        # Store colors for reuse in state updates
        self.colors = colors

        # Initial UI state
        self.updateContinuousVisuals()

    # ---------- UI -> commands ----------
    def on_refresh_button(self):
        if self.Disable or self.Continuous_ranging:
            return
        self.send_cmd(callRange())
        print("Range request sent.")

    # ---------- Events (embedded -> UI) ----------
    def on_range_event(self):
        if self.Disable:
            return

        if self.Continuous_ranging:
            # Stop continuous mode
            self.Continuous_ranging = False
            self.send_cmd(continuous_mode(continuous_mode=False))

            # Restore single-shot button
            self.refresh_button.configure(state="normal")

        else:
            # Start continuous mode
            self.Continuous_ranging = True
            self.send_cmd(continuous_mode(continuous_mode=True))

            # Disable single-shot button while continuous
            self.refresh_button.configure(state="disabled")

        # UI-only state refresh
        self.updateContinuousVisuals()

    def updateContinuousVisuals(self):
        """UI-only: adjust button styles + badge based on Continuous_ranging state."""
        if self.Continuous_ranging:
            self.mode_badge.configure(text="CONTINUOUS")

            # Toggle button becomes "active/danger stop"
            self.ranging_button.configure(
                text="Stop Continuous",
                fg_color=self.colors["danger"],
                hover_color=self.colors["dangerHover"],
                text_color="white",
                border_width=0,
            )

            # Refresh button looks disabled (not error)
            self.refresh_button.configure(
                fg_color=self.colors["disabledFill"],
                hover_color=self.colors["disabledFill"],
                text_color=self.colors["disabledText"],
            )
        else:
            self.mode_badge.configure(text="IDLE")

            self.ranging_button.configure(
                text="Start Continuous",
                fg_color=self.colors["card"],
                hover_color=self.colors["readout"],
                text_color=self.colors["text"],
                border_width=1,
                border_color=self.colors["border"],
            )

            self.refresh_button.configure(
                fg_color=self.colors["accent"],
                hover_color=self.colors["accentHover"],
                text_color="white",
            )

    def update_range(self, distance: float):
        self.range_value.set(f"{distance:.2f} cm")

   
            
    def Disable_Range():
        self.refresh_button.configure(state="disabled")
        self.ranging_button.configure(state="disabled")

            # UI-only: muted disabled appearance
        self.refresh_button.configure(
                fg_color=self.colors["disabledFill"],
                hover_color=self.colors["disabledFill"],
                text_color=self.colors["disabledText"],
            )
        self.ranging_button.configure(
                fg_color=self.colors["disabledFill"],
                hover_color=self.colors["disabledFill"],
                text_color=self.colors["disabledText"],
                border_width=0,
            )
        self.mode_badge.configure(text="DISABLED")
    
    
    def Enable_Range():
        self.refresh_button.configure(state="normal")
        self.ranging_button.configure(state="normal")

            # Restore based on current continuous state
        self.updateContinuousVisuals()
        