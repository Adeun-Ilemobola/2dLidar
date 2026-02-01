import customtkinter as ctk
from typing import Callable, Optional



class TextBox(ctk.CTkFrame):
    def __init__(self,set_callback: Optional[Callable[[str], None]] =None, parent=None, *,  width=400, height=200 , placeholder="" , label="" ):
        super().__init__(parent , width=width, height=height)

        self.text = ctk.StringVar(value="")
        self.set_callback = set_callback
        # --- Widgets ---
        self.label = ctk.CTkLabel(self, text=label, font=("Inter", 14, "bold"))
        self.entry = ctk.CTkEntry(self, width=width-20, height=height-20, textvariable=self.text)
        self.entry.bind("<Return>", lambda event: self.send_text())
        self.label.grid(row=0, column=0, sticky="w", padx=5, pady=(10, 0))
        self.entry.grid(row=1, column=0, sticky="nsew", padx=5, pady=10)
        self.entry.insert(0, placeholder)
        self.pack_propagate(False)  # respect fixed size
    
    def send_text(self):
        if self.set_callback:
            self.set_callback(self.text.get())
    def append_text(self, text: str):
        current = self.text.get()
        new_text = current + text
        self.text.set(new_text)
    def clear_text(self):
        self.text.set("")
    def get_text(self) -> str:
        return self.text.get()
