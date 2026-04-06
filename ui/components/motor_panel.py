from typing_extensions import Literal
import customtkinter as ctk
from shared.protocol import Axis, SetMotorAngle, SetMotorOffset, EnableMotor
from decimal import Decimal


class MotorPanel(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        axis: Axis,
        send_cmd,
        *,
        width=360,
        height=160,
        range_min_max: tuple[float, float],
        offset_min_max: tuple[float, float] | None = None
    ):
        super().__init__(parent, width=width, height=height)

        # =========================
        # State (core logic unchanged)
        # =========================
        self.axis = axis
        self.send_cmd = send_cmd  # function: (Command) -> None
        self.Disable = False

        self.angle = 0.0
        self.offset_deg = 0.0
        self.max_min = range_min_max
        self.offset_max_min = offset_min_max

        # UI state var (unchanged behavior)
        self.offset_mode_var = ctk.BooleanVar(value=False)

        # =========================
        # Component-local styling (no global theme changes)
        # =========================
        panelColors = {
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

        fonts = {
            "title": ctk.CTkFont(size=16, weight="bold"),
            "small": ctk.CTkFont(size=12, weight="normal"),
            "metricLabel": ctk.CTkFont(size=12, weight="bold"),
            "metricValue": ctk.CTkFont(size=18, weight="bold"),
            "button": ctk.CTkFont(size=13, weight="bold"),
        }

        # Outer container appearance
        self.configure(
            fg_color=panelColors["surface"],
            corner_radius=16,
            border_width=1,
            border_color=panelColors["border"],
        )

        # =========================
        # Layout grid (more consistent + responsive)
        # =========================
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # =========================
        # Header
        # =========================
        # Header row: title (left) + mode hint (right)
        headerRow = ctk.CTkFrame(self, fg_color="transparent")
        headerRow.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        headerRow.grid_columnconfigure(0, weight=1)
        headerRow.grid_columnconfigure(1, weight=0)

        self.title = ctk.CTkLabel(
            headerRow,
            text=f"Motor {axis.upper()}",
            font=fonts["title"],
            text_color=panelColors["text"],
            anchor="w",
        )
        self.title.grid(row=0, column=0, sticky="w")

        # Small mode label (Angle / Offset) – UI only, no logic change
        modeBadge = ctk.CTkLabel(
            headerRow,
            text="ANGLE",
            font=fonts["small"],
            text_color=panelColors["mutedText"],
            anchor="e",
        )
        modeBadge.grid(row=0, column=1, sticky="e")

        # =========================
        # Metrics row (Angle + Offset tiles)
        # =========================
        metricsRow = ctk.CTkFrame(self, fg_color="transparent")
        metricsRow.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        metricsRow.grid_columnconfigure(0, weight=1)
        metricsRow.grid_columnconfigure(1, weight=1)

        # Angle metric tile
        angleTile = ctk.CTkFrame(
            metricsRow,
            fg_color=panelColors["card"],
            corner_radius=12,
            border_width=1,
            border_color=panelColors["border"],
        )
        angleTile.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        angleTile.grid_columnconfigure(0, weight=1)

        angleTitle = ctk.CTkLabel(
            angleTile,
            text="ANGLE",
            font=fonts["metricLabel"],
            text_color=panelColors["mutedText"],
            anchor="w",
        )
        angleTitle.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

        self.angle_label = ctk.CTkLabel(
            angleTile,
            text=f"{self.angle:.2f}°",
            font=fonts["metricValue"],
            text_color=panelColors["text"],
            anchor="w",
        )
        self.angle_label.grid(row=1, column=0, sticky="w", padx=10, pady=(2, 8))

        # Offset metric tile
        offsetTile = ctk.CTkFrame(
            metricsRow,
            fg_color=panelColors["card"],
            corner_radius=12,
            border_width=1,
            border_color=panelColors["border"],
        )
        offsetTile.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        offsetTile.grid_columnconfigure(0, weight=1)

        offsetTitle = ctk.CTkLabel(
            offsetTile,
            text="OFFSET",
            font=fonts["metricLabel"],
            text_color=panelColors["mutedText"],
            anchor="w",
        )
        offsetTitle.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

        self.offset_label = ctk.CTkLabel(
            offsetTile,
            text=f"{self.offset_deg:.2f}°",
            font=fonts["metricValue"],
            text_color=panelColors["text"],
            anchor="w",
        )
        self.offset_label.grid(row=1, column=0, sticky="w", padx=10, pady=(2, 8))

        # =========================
        # Slider section
        # =========================
        sliderBlock = ctk.CTkFrame(self, fg_color="transparent")
        sliderBlock.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        sliderBlock.grid_columnconfigure(0, weight=1)

        # End labels row (shows range ends)
        sliderEnds = ctk.CTkFrame(sliderBlock, fg_color="transparent")
        sliderEnds.grid(row=0, column=0, sticky="ew")
        sliderEnds.grid_columnconfigure(0, weight=1)
        sliderEnds.grid_columnconfigure(1, weight=1)

        self.sliderMinLabel = ctk.CTkLabel(
            sliderEnds,
            text="",  # set by updateSliderEnds()
            font=fonts["small"],
            text_color=panelColors["mutedText"],
            anchor="w",
        )
        self.sliderMinLabel.grid(row=0, column=0, sticky="w")

        self.sliderMaxLabel = ctk.CTkLabel(
            sliderEnds,
            text="",  # set by updateSliderEnds()
            font=fonts["small"],
            text_color=panelColors["mutedText"],
            anchor="e",
        )
        self.sliderMaxLabel.grid(row=0, column=1, sticky="e")

        # Slider (core behavior unchanged)
        self.slider = ctk.CTkSlider(
            sliderBlock,
            from_=self.max_min[1],
            to=self.max_min[0],
            command=self.on_slider_move,
        )
        self.dragging = False
        self.slider.bind("<Button-1>", self.start_drag)
        self.slider.bind("<ButtonRelease-1>", self.stop_drag)
        self.slider.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.slider.set(0)

        # =========================
        # Input + Send row
        # =========================
        inputRow = ctk.CTkFrame(self, fg_color="transparent")
        inputRow.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        inputRow.grid_columnconfigure(0, weight=1)
        inputRow.grid_columnconfigure(1, weight=0)

        # Entry (UI only improvements: placeholder + consistent width)
        self.entry = ctk.CTkEntry(
            inputRow,
            width=110,
            placeholder_text="Angle (°)",
        )
        self.entry.bind("<Return>", lambda event: self.on_send_button())
        self.entry.grid(row=0, column=0, sticky="w")

        # Primary action button
        self.send_button = ctk.CTkButton(
            inputRow,
            text="Send Angle",
            command=self.on_send_button,
            height=36,
            corner_radius=10,
            font=fonts["button"],
            fg_color=panelColors["accent"],
            hover_color=panelColors["accentHover"],
            text_color="white",
        )
        self.send_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # =========================
        # Mode row (Offset Mode)
        # =========================
        modeRow = ctk.CTkFrame(self, fg_color="transparent")
        modeRow.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
        modeRow.grid_columnconfigure(0, weight=1)
        modeRow.grid_columnconfigure(1, weight=0)

        self.offset_checkbox = ctk.CTkCheckBox(
            modeRow,
            text="Offset Mode",
            variable=self.offset_mode_var,
            onvalue=True,
            offvalue=False,
            command=self.on_offset_checkbox,
        )
        self.offset_checkbox.grid(row=0, column=0, sticky="w")


        # Respect fixed size (unchanged)
        self.pack_propagate(False)

        # Initialize slider end labels for current mode
        self.updateSliderEnds()
        self.updateModeBadge(modeBadge)

    # ---------- UI -> commands ----------
    def on_send_button(self):
        if self.Disable:
            return
        value = self.read_float(self.entry.get(), default=0.0)

        if self.offset_mode_var.get():
            if (value <= self.offset_max_min[0]) or (value >= self.offset_max_min[1]):
                self.send_cmd(SetMotorOffset(self.axis, self.offset_deg))
                self.update_angle_label()
                return
            self.offset_deg = value
            self.slider.set(self.offset_deg)
            self.send_cmd(SetMotorOffset(self.axis, self.offset_deg))
        else:
            self.angle = value
            self.slider.set(self.angle)
            self.send_cmd(SetMotorAngle(self.axis, self.angle))

        self.update_angle_label()

    def on_slider_move(self, value: float):
        if self.Disable:
            return
        if self.offset_mode_var.get():
            self.offset_deg = float(Decimal(value).quantize(Decimal("0.1")))
            self.slider.set(self.offset_deg)
            self.send_cmd(SetMotorOffset(self.axis, self.offset_deg))
        else:
            self.angle = float(Decimal(value).quantize(Decimal("0.1")))
            self.slider.set(self.angle)
            self.send_cmd(SetMotorAngle(self.axis, self.angle))

        self.update_angle_label()

    def start_drag(self, event):
        self.dragging = True

    def stop_drag(self, event):
        self.dragging = False

    # ---------- Worker -> UI updates ----------
    def apply_motor_state(self, *, angle_deg: float, offset_deg: float, enabled: bool):
        """Call this from your UI event handler (after polling event_queue)."""
        self.angle = angle_deg
        self.offset_deg = offset_deg
        if not self.dragging:
            if self.offset_mode_var.get():
                # If in Offset Mode, update to the OFFSET value
                self.angle = 0
                self.slider.set(self.offset_deg)
            else:
                # If in Normal Mode, update to the ANGLE value
                self.slider.set(self.angle)
        self.update_angle_label()

    # ---------- helpers ----------
    def update_angle_label(self):
        # Metric tiles (UI formatting only)
        self.angle_label.configure(text=f"{self.angle:.2f}°")
        self.offset_label.configure(text=f"{self.offset_deg:.2f}°")

        # Keep your entry behavior the same, just better placeholder switching elsewhere
        self.entry.delete(0, ctk.END)
        if self.offset_mode_var.get():
            self.entry.insert(0, str(self.offset_deg))
        else:
            self.entry.insert(0, str(self.angle))

    def on_offset_checkbox(self):
        if self.Disable:
            return

        # Switch slider range (unchanged logic)
        if self.offset_mode_var.get():
            if self.offset_max_min is not None:
                self.slider.configure(from_=self.offset_max_min[1], to=self.offset_max_min[0])
            else:
                self.slider.configure(from_=0, to=180)

            self.slider.set(self.offset_deg)
            self.entry.delete(0, ctk.END)
            self.entry.insert(0, str(self.offset_deg))
        else:
            self.slider.configure(from_=self.max_min[1], to=self.max_min[0])
            self.slider.set(self.angle)
            self.entry.delete(0, ctk.END)
            self.entry.insert(0, str(self.angle))

        # UI-only: improve clarity when mode switches
        self.updateSliderEnds()
        self.updateModeText()

        self.update_angle_label()

    # UI-only: updates slider end labels based on current mode/range
    def updateSliderEnds(self):
        if self.offset_mode_var.get():
            if self.offset_max_min is not None:
                left = self.offset_max_min[1]
                right = self.offset_max_min[0]
            else:
                left = 180
                right = 0
        else:
            left = self.max_min[1]
            right = self.max_min[0]

        # Slider is configured from_=left to=right, so labels match visual ends
        self.sliderMinLabel.configure(text=f"{left:.0f}°")
        self.sliderMaxLabel.configure(text=f"{right:.0f}°")

    # UI-only: updates button text + entry placeholder when mode changes
    def updateModeText(self):
        if self.offset_mode_var.get():
            self.send_button.configure(text="Send Offset")
            self.entry.configure(placeholder_text="Offset (°)")
        else:
            self.send_button.configure(text="Send Angle")
            self.entry.configure(placeholder_text="Angle (°)")

    # UI-only: updates the small header badge ("ANGLE" / "OFFSET") without changing behavior
    def updateModeBadge(self, badgeLabel):
        if self.offset_mode_var.get():
            badgeLabel.configure(text="OFFSET")
        else:
            badgeLabel.configure(text="ANGLE")

    
    def DisablePanel(self):
         self.Disable = True
         self.slider.configure(state="disabled")
         self.entry.configure(state="disabled")
         self.send_button.configure(state="disabled")
         self.offset_checkbox.configure(state="disabled")

         # UI-only: disabled look should be muted (not error red)
         self.configure(fg_color=("#ECEFF3", "#111318"))
         self.send_button.configure(fg_color=("#B9C3CF", "#2A2F37"), hover_color=("#B9C3CF", "#2A2F37"))
        
        

    def EnablePanel(self):
        self.Disable = False
        self.slider.configure(state="normal")
        self.entry.configure(state="normal")
        self.send_button.configure(state="normal")
        self.offset_checkbox.configure(state="normal")

        # Restore default surface + primary button look
        self.configure(fg_color=("#F2F3F5", "#14161A"))
        self.send_button.configure(fg_color=("#1F6AA5", "#1F6AA5"), hover_color=("#195A8D", "#195A8D"))
        
        
    def changLimit(self, min :float, max: float,):
        range_min_max = (min, max)
        self.max_min = range_min_max
        self.slider.configure(from_=self.max_min[1], to=self.max_min[0])

        self.updateSliderEnds()
    def increment(self , setp: float):
        if self.Disable:
            return
        if self.offset_mode_var.get():
            new_value = self.offset_deg + setp
            if (new_value <= self.offset_max_min[0]) or (new_value >= self.offset_max_min[1]):
                return
            self.offset_deg = new_value
            self.slider.set(self.offset_deg)
            self.send_cmd(SetMotorOffset(self.axis, self.offset_deg))
        else:
            new_value = self.angle + setp
            if (new_value <= self.max_min[0]) or (new_value >= self.max_min[1]):
                return
            self.angle = new_value
            self.slider.set(self.angle)
            self.send_cmd(SetMotorAngle(self.axis, self.angle))

        self.update_angle_label()


    def decrement(self , setp: float):
        if self.Disable:
            return
        if self.offset_mode_var.get():
            new_value = self.offset_deg - setp
            if (new_value <= self.offset_max_min[0]) or (new_value >= self.offset_max_min[1]):
                return
            self.offset_deg = new_value
            self.slider.set(self.offset_deg)
            self.send_cmd(SetMotorOffset(self.axis, self.offset_deg))
        else:
            new_value = self.angle - setp
            if (new_value <= self.max_min[0]) or (new_value >= self.max_min[1]):
                return
            self.angle = new_value
            self.slider.set(self.angle)
            self.send_cmd(SetMotorAngle(self.axis, self.angle))

        self.update_angle_label()

    @staticmethod
    def read_float(text: str, default: float) -> float:
        try:
            return float(text.strip())
        except Exception:
            return default
