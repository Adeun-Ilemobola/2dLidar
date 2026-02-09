
import customtkinter as ctk
from typing import Optional ,Tuple
from shared.protocol import PointState

class SmartRectangle:
    def __init__(self, canvas: ctk.CTkCanvas, state: PointState , gridIndex:Tuple[int,int] , hover , unhover  , on_select, x1, y1, x2, y2, **kwargs):
        self.canvas = canvas
        self.state: PointState = state
        self.gridIndex = gridIndex
        self.on_select = on_select
        # Create the actual canvas item and store its ID
        self.id = self.canvas.create_rectangle(x1, y1, x2, y2, **kwargs)
        
        self.canvas.tag_bind(self.id, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.id, "<Enter>", lambda e: hover(self.id, self.gridIndex))
        self.canvas.tag_bind(self.id, "<Leave>", lambda e: unhover(self.id, self.gridIndex))

        # Custom properties
        self.is_selected = False
        self.is_void = False
        # self.next_SmartRectangle: Optional["SmartRectangle"] = None  
        # self.prev_SmartRectangle: Optional["SmartRectangle"] = None

       
        self.color_selected = "#FF2FB3"
        self.auto_color()

    def on_click(self, event):
       
        if not self.is_selected:
            self.is_selected = True
            self.canvas.itemconfig(self.id, fill=self.color_selected)
            self.on_select(self)  # Notify the SmartCanvas of the selection
        else:
            self.is_selected = False
            self.auto_color()
            self.on_select(self)  # Notify the SmartCanvas of the deselection

    def auto_color(self):
        distance = self.state.distant
        if self.is_selected:
            self.canvas.itemconfig(self.id, fill=self.color_selected)
            return  # Keep selected color
        if self.is_void:
            self.canvas.itemconfig(self.id, fill="#6C757D")
            return
        
        if distance >= 0 and distance < 80:
            self.canvas.itemconfig(self.id, fill="#D64545")
        elif distance >= 80 and distance < 160:
            self.canvas.itemconfig(self.id, fill="#E07A3F")
        elif distance >= 160 and distance < 240:
            self.canvas.itemconfig(self.id, fill="#E6B566")
        elif distance >= 240 and distance < 390:
            self.canvas.itemconfig(self.id, fill="#6FAF8F")
        elif distance >= 390 and distance < 400:
            self.canvas.itemconfig(self.id, fill="#4C6FAE")
        elif distance >= 400:
            self.canvas.itemconfig(self.id, fill="#2A2E2E")
            self.is_void = True
        else:
            self.is_void = True
            self.canvas.itemconfig(self.id, fill="#2A2E2E")  # Default color for invalid distances
    