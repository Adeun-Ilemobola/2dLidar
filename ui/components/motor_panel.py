import customtkinter as ctk
from shared.protocol import Axis, SetMotorAngle, SetMotorOffset, EnableMotor  # use your real command names

class MotorPanel(ctk.CTkFrame):
    def __init__(self, parent, axis: Axis, send_cmd, *, width=360, height=160):
        super().__init__(parent, width=width, height=height)
        self.axis = axis
        self.send_cmd = send_cmd  # function: (Command) -> None

        self.angle = 0.0
        self.offset_deg = 0.0

        # --- UI state vars ---
        self.offset_mode_var = ctk.BooleanVar(value=False)

        # --- Widgets ---
        self.title = ctk.CTkLabel(self, text=f"Motor {axis.upper()}", font=("Inter", 18, "bold"))
        self.status = ctk.CTkLabel(self, text="Status: unknown", text_color="#aaaaaa")
        self.angle_label = ctk.CTkLabel(self, text=f"Angle: {self.angle:.2f}", text_color="#aaaaaa")

        self.slider = ctk.CTkSlider(self, from_=0, to=270, command=self.on_slider_move)
        self.slider.set(self.angle)

        self.entry = ctk.CTkEntry(self, width=95, placeholder_text="Angle")
        self.send_button = ctk.CTkButton(self, text="Send New Angle", command=self.on_send_button)

        self.offset_checkbox = ctk.CTkCheckBox(self, text="Offset Mode", variable=self.offset_mode_var)

        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.title.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0))

        self.status.grid(row=1, column=0, sticky="w", padx=10, pady=(4, 0))
        self.angle_label.grid(row=1, column=1, sticky="w", padx=10, pady=(4, 0))

        self.slider.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=8)

        self.entry.grid(row=3, column=0, sticky="w", padx=10, pady=(0, 10))
        self.send_button.grid(row=3, column=1, sticky="w", padx=10, pady=(0, 10))

        self.offset_checkbox.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        self.pack_propagate(False)  # respect fixed size

    # ---------- UI -> commands ----------
    def on_send_button(self):
        value = self.read_float(self.entry.get(), default=0.0)

        if self.offset_mode_var.get():
            self.offset_deg = value
            self.send_cmd(SetMotorOffset(self.axis, self.offset_deg))
        else:
            self.angle = value
            self.slider.set(self.angle)
            self.send_cmd(SetMotorAngle(self.axis, self.angle))

        self.update_angle_label()

    def on_slider_move(self, value: float):
        self.angle = float(value)
        if self.offset_mode_var.get():
            self.offset_deg = value
            self.send_cmd(SetMotorOffset(self.axis, self.offset_deg))
        else:
            self.angle = value
            self.slider.set(self.angle)
            self.send_cmd(SetMotorAngle(self.axis, self.angle))

        self.update_angle_label()
        self.send_cmd(SetMotorAngle(self.axis, self.angle))

    # ---------- Worker -> UI updates ----------
    def apply_motor_state(self, *, angle_deg: float, offset_deg: float, enabled: bool):
        """Call this from your UI event handler (after polling event_queue)."""
        self.angle = angle_deg
        self.offset_deg = offset_deg
        self.slider.set(self.angle)

        self.status.configure(text=f"Status: {'enabled' if enabled else 'disabled'}")
        self.update_angle_label()

    # ---------- helpers ----------
    def update_angle_label(self):
        self.angle_label.configure(text=f"Angle: {self.angle:.2f}")
        self.slider.set(self.angle)
        self.status.configure(text=f"Status: {'enabled' if self.angle else 'disabled'}")
        self.entry.delete(0 , ctk.END)
        self.entry.insert(0 , str(self.angle))

    @staticmethod
    def read_float(text: str, default: float) -> float:
        try:
            return float(text.strip())
        except Exception:
            return default
