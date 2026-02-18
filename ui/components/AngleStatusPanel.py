import tkinter as tk
import customtkinter as ctk
from typing import Callable, Literal

from shared.protocol import Command, findMinMax, Axis


class AngleStatusPanel(ctk.CTkFrame):
    """
    UI-only redesigned panel:
      - Min angle
      - Max angle
      - Range (cm)
      - Status + Start/Stop button

    Public variables (unchanged):
      - self.minimum_angle_var (tk.IntVar)
      - self.maximum_angle_var (tk.IntVar)
      - self.status_var        (tk.StringVar)
      - self.range_var         (tk.DoubleVar)
    """

    def __init__(
        self,
        master,
        command: Callable[[Axis, Literal["stop", "start"]], None],
        Axis: Axis,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        # =========================
        # Component-local styling (light/dark aware)
        # =========================
        panelColors = {
            # Main surface behind everything
            "surface": ("#F2F3F5", "#14161A"),
            # Raised card surfaces
            "card": ("#FFFFFF", "#1C1F24"),
            # Subtle border line
            "border": ("#D7DADF", "#2A2F37"),
            # Text colors
            "text": ("#111318", "#E9EDF2"),
            "mutedText": ("#5A6472", "#AAB3BF"),
            # Accent for action button (keeps your existing blue vibe)
            "accent": ("#1F6AA5", "#1F6AA5"),
            "accentHover": ("#195A8D", "#195A8D"),
            # Neutral button surface (for "secondary" look if you want later)
            "buttonSurface": ("#EEF1F4", "#252A32"),
        }

        statusStyles = {
            "Idle":        {"dot": "#8B95A3", "pill": ("#EEF1F4", "#252A32")},
            "Scanning":    {"dot": "#2D7DFF", "pill": ("#E9F1FF", "#1E2A3A")},
            "in progress": {"dot": "#F5A524", "pill": ("#FFF4E2", "#3A2A1B")},
            "Done":        {"dot": "#22C55E", "pill": ("#E8FAEF", "#1D3326")},
            "Error":       {"dot": "#EF4444", "pill": ("#FEECEC", "#3A1F1F")},
        }

        fonts = {
            # Labels
            "label": ctk.CTkFont(size=14, weight="normal"),
            "labelStrong": ctk.CTkFont(size=14, weight="bold"),
            # Big numeric values
            "value": ctk.CTkFont(size=64, weight="bold"),
            # Dash between values
            "dash": ctk.CTkFont(size=48, weight="bold"),
            # Status title/value
            "statusTitle": ctk.CTkFont(size=18, weight="bold"),
            "statusValue": ctk.CTkFont(size=16, weight="normal"),
            # Range line (kept readable)
            "range": ctk.CTkFont(size=13, weight="normal"),
            # Button
            "button": ctk.CTkFont(size=14, weight="bold"),
        }

        # Keep your original attributes (so nothing breaks if referenced elsewhere)
        self._panel_bg = panelColors["surface"][0]  # legacy, not used directly
        self._status_bg = "#4F4F4F"                 # legacy, not used directly

        self.mode: Literal["stop", "start"] = "stop"

        # Outer container appearance
        self.configure(
            fg_color=panelColors["surface"],
            corner_radius=16,
            border_width=1,
            border_color=panelColors["border"],
        )

        # =========================
        # Public state (unchanged)
        # =========================
        self.minimum_angle_var = tk.IntVar(value=180)
        self.maximum_angle_var = tk.IntVar(value=180)
        self.status_var = tk.StringVar(value="Idle")
        self.range_var = tk.DoubleVar(value=100.0)

        self.command = command
        self.Axis = Axis

        # =========================
        # Layout grid
        # =========================
        self.grid_columnconfigure(0, weight=1)  # left (angles)
        self.grid_columnconfigure(1, weight=0, minsize=210)  # right (status)
        self.grid_rowconfigure(0, weight=1)

        # =========================
        # Left card: Angles
        # =========================
        # Angle card container
        anglesCard = ctk.CTkFrame(
            self,
            fg_color=panelColors["card"],
            corner_radius=14,
            border_width=1,
            border_color=panelColors["border"],
        )
        anglesCard.grid(row=0, column=0, sticky="nsew", padx=(14, 10), pady=14)
        anglesCard.grid_columnconfigure(0, weight=1)
        anglesCard.grid_rowconfigure(0, weight=1)

        # Inner layout for Min - Max
        anglesRow = ctk.CTkFrame(anglesCard, fg_color="transparent")
        anglesRow.grid(row=0, column=0, sticky="nsew", padx=16, pady=14)
        anglesRow.grid_columnconfigure(0, weight=1)
        anglesRow.grid_columnconfigure(1, weight=0)
        anglesRow.grid_columnconfigure(2, weight=1)
        anglesRow.grid_rowconfigure(0, weight=1)

        # Min block
        minBlock = ctk.CTkFrame(anglesRow, fg_color="transparent")
        minBlock.grid(row=0, column=0, sticky="nsew")
        minBlock.grid_rowconfigure(1, weight=1)

        self._min_label = ctk.CTkLabel(
            minBlock,
            text="Min",
            font=fonts["labelStrong"],
            text_color=panelColors["mutedText"],
            anchor="w",
        )
        self._min_label.grid(row=0, column=0, sticky="w")

        self._min_value = ctk.CTkLabel(
            minBlock,
            textvariable=self.minimum_angle_var,
            font=fonts["value"],
            text_color=panelColors["text"],
            anchor="w",
        )
        self._min_value.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Dash separator
        self._dash_label = ctk.CTkLabel(
            anglesRow,
            text="—",
            font=fonts["dash"],
            text_color=panelColors["border"],
        )
        self._dash_label.grid(row=0, column=1, sticky="n", padx=18, pady=(26, 0))

        # Max block
        maxBlock = ctk.CTkFrame(anglesRow, fg_color="transparent")
        maxBlock.grid(row=0, column=2, sticky="nsew")
        maxBlock.grid_rowconfigure(1, weight=1)

        self._max_label = ctk.CTkLabel(
            maxBlock,
            text="Max",
            font=fonts["labelStrong"],
            text_color=panelColors["mutedText"],
            anchor="w",
        )
        self._max_label.grid(row=0, column=0, sticky="w")

        self._max_value = ctk.CTkLabel(
            maxBlock,
            textvariable=self.maximum_angle_var,
            font=fonts["value"],
            text_color=panelColors["text"],
            anchor="w",
        )
        self._max_value.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # =========================
        # Right card: Status + controls
        # =========================
        statusCard = ctk.CTkFrame(
            self,
            fg_color=panelColors["card"],
            corner_radius=14,
            border_width=1,
            border_color=panelColors["border"],
        )
        statusCard.grid(row=0, column=1, sticky="nsew", padx=(10, 14), pady=14)
        statusCard.grid_columnconfigure(0, weight=1)
        statusCard.grid_rowconfigure(3, weight=1)

        # Header: "Status" label
        # (keeps the right panel feeling intentional and readable)
        statusHeader = ctk.CTkLabel(
            statusCard,
            text="Status",
            font=fonts["statusTitle"],
            text_color=panelColors["text"],
            anchor="w",
        )
        statusHeader.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))

        # Status pill (dot + status text)
        # This improves glanceability vs big stacked labels.
        statusPill = ctk.CTkFrame(
            statusCard,
            fg_color=statusStyles.get(self.status_var.get(), statusStyles["Idle"])["pill"],
            corner_radius=999,
            border_width=1,
            border_color=panelColors["border"],
        )
        statusPill.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        statusPill.grid_columnconfigure(1, weight=1)

        statusDot = ctk.CTkLabel(
            statusPill,
            text="●",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=statusStyles.get(self.status_var.get(), statusStyles["Idle"])["dot"],
        )
        statusDot.grid(row=0, column=0, padx=(12, 8), pady=8, sticky="w")

        self.status_value = ctk.CTkLabel(
            statusPill,
            textvariable=self.status_var,
            font=fonts["statusValue"],
            text_color=panelColors["text"],
            anchor="w",
        )
        self.status_value.grid(row=0, column=1, padx=(0, 12), pady=8, sticky="ew")

        # Range line
        self._range_label_var = tk.StringVar(value="Ranging: 0 cm")
        self.range_label = ctk.CTkLabel(
            statusCard,
            textvariable=self._range_label_var,
            font=fonts["range"],
            text_color=panelColors["mutedText"],
            anchor="w",
        )
        self.range_label.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))

        # Action button
        # Keeps your command + mode logic the same, but improves visuals.
        self.start_test_button = ctk.CTkButton(
            statusCard,
            text="start test",
            height=40,
            corner_radius=10,
            font=fonts["button"],
            fg_color=panelColors["accent"],
            hover_color=panelColors["accentHover"],
            text_color="white",
            command=self.on_start_test_clicked,
        )
        self.start_test_button.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 14))

        # =========================
        # Variable tracing (UI refresh only)
        # =========================
        self.range_var.trace_add("write", self._on_range_var_changed)
        self.status_var.trace_add("write", lambda *_: self.updateStatusVisuals(statusPill, statusDot, statusStyles, panelColors))

        self._refresh_range_label()
        self.updateStatusVisuals(statusPill, statusDot, statusStyles, panelColors)

    # -------------------------
    # UI refresh helpers
    # -------------------------
    def updateStatusVisuals(self, statusPill, statusDot, statusStyles, panelColors) -> None:
        """Update the status pill color + dot color based on status_var."""
        current = str(self.status_var.get())
        style = statusStyles.get(current, statusStyles["Idle"])

        statusPill.configure(
            fg_color=style["pill"],
            border_color=panelColors["border"],
        )
        statusDot.configure(text_color=style["dot"])

    # -------------------------
    # VAR UPDATES / HELPERS 
    # -------------------------
    def _on_range_var_changed(self, *_args) -> None:
        """Triggered whenever range_var changes."""
        self._refresh_range_label()

    def _refresh_range_label(self) -> None:
        """Formats the range label as: 'Ranging: XXX cm'."""
        try:
            value = float(self.range_var.get())
            if abs(value - int(value)) < 1e-9:
                self._range_label_var.set(f"Ranging: {int(value)} cm")
            else:
                self._range_label_var.set(f"Ranging: {value:.1f} cm")
        except Exception:
            self._range_label_var.set("Ranging: ? cm")

    # -------------------------
    # Public setters 
    # -------------------------
    def set_minimum_angle(self, value: float) -> None:
        """Convenience setter for minimum angle."""
        self.minimum_angle_var.set(float(value))
        self._min_value.configure(textvariable=self.minimum_angle_var)

    def set_maximum_angle(self, value: float) -> None:
        """Convenience setter for maximum angle."""
        self.maximum_angle_var.set(float(value))
        self._max_value.configure(textvariable=self.maximum_angle_var)

    def set_status(self, value: Literal["Idle", "Scanning", "Error", "Done", "in progress"]) -> None:
        """Convenience setter for status text."""
        self.status_var.set(str(value))
        self.status_value.configure(textvariable=self.status_var)

    def set_range_cm(self, value: float) -> None:
        """Convenience setter for range in centimeters."""
        self.range_var.set(float(value))
        self._refresh_range_label()

    def dis(self, state: Literal["disabled", "normal"]) -> None:
        self.start_test_button.configure(state=state)
        self.start_test_button.configure(
            fg_color="#1f6aa5" if state == "normal" else "#D21010",
            hover_color="#195A8D" if state == "normal" else "#B10D0D",
            text_color="white",
        )

    # -------------------------
    # Button behavior 
    # -------------------------
    def on_start_test_clicked(self) -> None:
        if self.mode == "start":
            self.mode = "stop"
            self.start_test_button.configure(text="stop test ")
        else:
            self.mode = "start"
            self.start_test_button.configure(text="start test")
        self.command(self.Axis, self.mode)
