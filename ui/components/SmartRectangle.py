
import customtkinter as ctk
from typing import Optional
from shared.protocol import PointState

class SmartRectangle:
    def __init__(self, canvas: ctk.CTkCanvas, state: PointState, x1, y1, x2, y2, **kwargs):
        self.canvas = canvas
        self.state: PointState = state
        # Create the actual canvas item and store its ID
        self.id = self.canvas.create_rectangle(x1, y1, x2, y2, **kwargs)
        
        self.canvas.tag_bind(self.id, "<Button-1>", self.on_click)

        # Custom properties
        self.is_selected = False
        self.is_void = False
        # self.next_SmartRectangle: Optional["SmartRectangle"] = None  
        # self.prev_SmartRectangle: Optional["SmartRectangle"] = None

       
        self.color_selected = "blue"
        self.auto_color()

    def on_click(self, event):
        if self.is_void :
            return
        self.is_selected = not self.is_selected
        if self.is_selected:
            self.canvas.itemconfig(self.id, fill=self.color_selected)
        else:
            self.auto_color()


        
    def auto_color(self):
        distance = self.state.distant
        if distance >= 0 and distance < 80:
            self.canvas.itemconfig(self.id, fill="red")
        elif distance >= 80 and distance < 160:
            self.canvas.itemconfig(self.id, fill="orange")
        elif distance >= 160 and distance < 240:
            self.canvas.itemconfig(self.id, fill="yellow")
        elif distance >= 240 and distance < 320:
            self.canvas.itemconfig(self.id, fill="green")
        elif distance >= 320 and distance < 400:
            self.canvas.itemconfig(self.id, fill="white")
        elif distance >= 400:
            self.canvas.itemconfig(self.id, fill="white")
            self.is_void = True
        else:
            self.is_void = True
            self.canvas.itemconfig(self.id, fill="white")  # Default color for invalid distances