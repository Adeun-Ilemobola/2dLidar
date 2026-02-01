
import customtkinter as ctk
from typing_extensions import Literal

from shared.protocol import Axis, callRange, getRange   # use

class RangePane(ctk.CTkFrame):
    def __init__(self, parent, send_cmd, *, width=360, height=120):
        super().__init__(parent, width=width, height=height)
        self.send_cmd = send_cmd  
        self.Disable = False

        self.range_value = ctk.StringVar(value="N/A")

        # --- Widgets ---
        self.title = ctk.CTkLabel(self, text="Range Sensor", font=("Inter", 18, "bold"))
        self.range_label = ctk.CTkLabel(self, textvariable=self.range_value, font=("Inter", 16))

        self.refresh_button = ctk.CTkButton(self, text="Get Range", command=self.on_refresh_button)

        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)

        self.title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        self.range_label.grid(row=1, column=0, sticky="w", padx=10, pady=(4, 0))
        self.refresh_button.grid(row=2, column=0, sticky="ew", padx=10, pady=8)

        self.pack_propagate(False)  # respect fixed size

    # ---------- UI -> commands ----------
    def on_refresh_button(self):
        if self.Disable:
            return
        self.send_cmd(callRange())
        print("Range request sent.")
    # ---------- Events (embedded -> UI) ----------
    def update_range(self, distance: float):
        self.range_value.set(f"{distance:.2f} cm")
    def setDisable(self , state:Literal['disabled', 'normal']):
        self.Disable = state == "disabled"
        if self.Disable:
            self.refresh_button.configure(state="disabled")
        else:
            self.refresh_button.configure(state="normal")
       