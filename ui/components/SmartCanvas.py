
from customtkinter import CTkCanvas
from typing import List
from shared.protocol import PointState
from ui.components.SmartRectangle import SmartRectangle
class SmartCanvas(CTkCanvas):
    def __init__(self, parent, width: int, height: int, point_states: List[List[PointState]], **kwargs):
        super().__init__(parent, width=width, height=height, **kwargs)
        self.point_states = point_states
        self.smart_rectangles: List[List[SmartRectangle]] = []
        self.create_smart_rectangles()

    def create_smart_rectangles(self):
        if not self.point_states:
            return
        
        rows = len(self.point_states)
        cols = len(self.point_states[0]) if rows > 0 else 0
        
        size_ = 1.1

        rect_width = self.winfo_reqwidth() / cols * size_
        rect_height = self.winfo_reqheight() / rows * size_

        for i in range(rows):
            row_rectangles = []
            for j in range(cols):
                state = self.point_states[i][j]
                x1 = j * rect_width
                y1 = i * rect_height
                x2 = x1 + rect_width
                y2 = y1 + rect_height

                smart_rect = SmartRectangle(self, state, x1, y1, x2, y2)
                row_rectangles.append(smart_rect)
            self.smart_rectangles.append(row_rectangles)

    def update_point_states(self, new_point_states: List[List[PointState]]):
        self.point_states = new_point_states
        for i, row in enumerate(self.smart_rectangles):
            for j, smart_rect in enumerate(row):
                smart_rect.state = new_point_states[i][j]
                smart_rect.auto_color()