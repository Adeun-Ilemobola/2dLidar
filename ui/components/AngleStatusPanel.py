
import tkinter as tk
import customtkinter as ctk
from typing import Callable, Literal

from shared.protocol import Command, findMinMax , Axis


class AngleStatusPanel(ctk.CTkFrame):
    """
    A reusable "component" widget that displays:
      - Minimum angle
      - Maximum angle
      - Range (cm)
      - Status

    Public variables:
      - self.minimum_angle_var (tk.IntVar)
      - self.maximum_angle_var (tk.IntVar)
      - self.status_var        (tk.StringVar)
      - self.range_var         (tk.DoubleVar)  # interpreted as centimeters

    You can set these vars directly, or use the setter methods.
    """

    def __init__(
        self,
        master,
        command: Callable[[Axis , Literal["stop", "start"]], None],
        Axis: Axis,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        # --- Colors (tweak these to taste) ---
        self._panel_bg = "#BDBDBD"     # grey bar background
        self._status_bg = "#4F4F4F"    # dark box background

        self.mode: Literal["stop", "start"] = "stop"

        # Outer appearance
        self.configure(fg_color=self._panel_bg, corner_radius=12)

        # --- Public variables 
        self.minimum_angle_var = tk.IntVar(value=180)
        self.maximum_angle_var = tk.IntVar(value=180)
        self.status_var =  tk.StringVar(value="Idle")
        self.range_var =  tk.DoubleVar(value=100.0)
        self.command = command
        self.Axis = Axis

        # --- Layout root grid ---
        # Left area (min/max) takes most space; right status box is fixed-ish.
        self.grid_columnconfigure(0, weight=1)  # left
        self.grid_columnconfigure(1, weight=0)  # right
        self.grid_rowconfigure(0, weight=1)

        # Build UI

        #  \\---------build left  section-----------\\
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=18, pady=14)

        # Grid: [Min block] [dash] [Max block]
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=0)
        left.grid_columnconfigure(2, weight=1)
        left.grid_rowconfigure(0, weight=1)

        # Fonts (adjust sizes if you want it even bigger)
        label_font = ctk.CTkFont(size=28, weight="normal")
        value_font = ctk.CTkFont(size=96, weight="bold")
        dash_font = ctk.CTkFont(size=72, weight="bold")

        # --- Min block ---
        min_frame = ctk.CTkFrame(left, fg_color="transparent")
        min_frame.grid(row=0, column=0, sticky="w")

        self._min_label = ctk.CTkLabel(
            min_frame,
            text="Min",
            text_color="black",
            font=label_font,
        )
        self._min_label.grid(row=0, column=0, sticky="w")

        self._min_value = ctk.CTkLabel(
            min_frame,
            textvariable=self.minimum_angle_var,
            text_color="black",
            font=value_font,
        )
        self._min_value.grid(row=1, column=0, sticky="w")

        # --- Dash ---
        self._dash_label = ctk.CTkLabel(
            left,
            text="-",
            text_color="black",
            font=dash_font,
        )
        self._dash_label.grid(row=0, column=1, sticky="n", padx=18)

        # --- Max block ---
        max_frame = ctk.CTkFrame(left, fg_color="transparent")
        max_frame.grid(row=0, column=2, sticky="w")

        self._max_label = ctk.CTkLabel(
            max_frame,
            text="Max",
            text_color="black",
            font=label_font,
        )
        self._max_label.grid(row=0, column=0, sticky="w")

        self._max_value = ctk.CTkLabel(
            max_frame,
            textvariable=self.maximum_angle_var,
            text_color="black",
            font=value_font,
        )
        self._max_value.grid(row=1, column=0, sticky="w")



        #  \\---------build status  section-----------\\ 
        box = ctk.CTkFrame(self, fg_color=self._status_bg, corner_radius=10)
        box.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=14)

        # Make it feel like the mockup: narrow, vertically stacked
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(0, weight=0)  # button
        box.grid_rowconfigure(1, weight=0)  # range
        box.grid_rowconfigure(2, weight=1)  # status label/value area

        # Button
        self.start_test_button = ctk.CTkButton(
            box,
            text="start test",
            height=32,
            corner_radius=6,
            fg_color="#E6E6E6",
            text_color="black",
            hover_color="#D8D8D8",
            command=self.on_start_test_clicked,  
        )
        self.start_test_button.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))

        # Range text (auto-formatted from range_var)
        self._range_label_var = tk.StringVar(value="Ranging: 0 cm")
        self.range_label = ctk.CTkLabel(
            box,
            textvariable=self._range_label_var,
            text_color="white",
            font=ctk.CTkFont(size=16, weight="normal"),
        )
        self.range_label.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

        # Status title
        self.status_title = ctk.CTkLabel(
            box,
            text="Status",
            text_color="white",
            font=ctk.CTkFont(size=32, weight="bold"),
        )
        self.status_title.grid(row=2, column=0, sticky="n", padx=14, pady=(10, 0))

        # Optional: actual status value (you can hide/remove if you want)
        self.status_value = ctk.CTkLabel(
            box,
            textvariable=self.status_var,
            text_color="white",
            font=ctk.CTkFont(size=18, weight="normal"),
        )
        self.status_value.grid(row=2, column=0, sticky="n", padx=14, pady=(55, 0))       

        # Keep range label updated whenever range_var changes
        self.range_var.trace_add("write", self._on_range_var_changed)
        self._refresh_range_label()

  
   
    # -------------------------
    # VAR UPDATES / HELPERS
    # -------------------------
    def _on_range_var_changed(self, *_args) -> None:
        """Triggered whenever range_var changes."""
        self._refresh_range_label()

    def _refresh_range_label(self) -> None:
        """Formats the range label as: 'Ranging:XXX cm'."""
        try:
            value = float(self.range_var.get())
            # Keep it clean: if it's basically an integer, show no decimals
            if abs(value - int(value)) < 1e-9:
                self._range_label_var.set(f"Ranging:{int(value)} cm")
            else:
                self._range_label_var.set(f"Ranging:{value:.1f} cm")
        except Exception:
            # If range_var becomes invalid, don't crash the UI
            self._range_label_var.set("Ranging: ? cm")

    
    def set_minimum_angle(self, value: float) -> None:
        """Convenience setter for minimum angle."""
        self.minimum_angle_var.set(float(value))
        self._min_value.configure(textvariable=self.minimum_angle_var)  
        

    def set_maximum_angle(self, value: float) -> None:
        """Convenience setter for maximum angle."""
        self.maximum_angle_var.set(float(value))
        self._max_value.configure(textvariable=self.maximum_angle_var)

    def set_status(self, value:Literal["Idle", "Scanning", "Error"  , "Done" , "in progress"]) -> None:
        """Convenience setter for status text."""
        self.status_var.set(str(value))
        self.status_value.configure(textvariable=self.status_var)

    def set_range_cm(self, value: float) -> None:
        """Convenience setter for range in centimeters."""
        self.range_var.set(float(value))
        self._refresh_range_label()
    def dis(self , state:Literal['disabled', 'normal']) -> None:
      
        self.start_test_button.configure(state=state)
        self.start_test_button.configure(fg_color="#1f6aa5" if state == "normal" else "#D21010")

  
    def on_start_test_clicked(self) -> None:
        if self.mode == "start":
            self.mode = "stop"
            self.start_test_button.configure(text="stop test ")
        else:
            self.mode = "start"
            self.start_test_button.configure(text="start test")
        self.command(self.Axis , self.mode)  
        

   