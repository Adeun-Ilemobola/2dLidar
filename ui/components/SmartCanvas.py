
from customtkinter import CTkCanvas
from typing import List, Tuple
from shared.protocol import PointState
from ui.components.SmartRectangle import SmartRectangle
class SmartCanvas(CTkCanvas):
    def __init__(self, parent, width: int, height: int, point_states: List[List[PointState]], **kwargs):
        super().__init__(parent, width=width, height=height, **kwargs)
        self.point_states = point_states
        self.smart_rectangles: List[List[SmartRectangle]] = []

        self.point_1 :SmartRectangle | None = None
        self.point_2 :SmartRectangle | None = None



        self.configure( background="#1e2121")
        self.create_smart_rectangles()

    def create_smart_rectangles(self):
        if not self.point_states:
            return
        
        rows = len(self.point_states)
        cols = len(self.point_states[0]) if rows > 0 else 0
        
        size_ = 0.9

        rect_width = self.winfo_reqwidth() / cols * size_
        rect_height = self.winfo_reqheight() / rows * size_

        for i in range(rows):
            row_rectangles = []
            for j in range(cols):
                state = self.point_states[i][j]
                gridIndex = (i,j)
                x1 = j * rect_width
                y1 = i * rect_height
                x2 = x1 + rect_width
                y2 = y1 + rect_height

                smart_rect = SmartRectangle(self, state, gridIndex=gridIndex, hover=self.Hover, unhover=self.Unhover , on_select=self.on_select_point, x1=x1, y1=y1, x2=x2, y2=y2)
                row_rectangles.append(smart_rect)
            self.smart_rectangles.append(row_rectangles)
    
    
    
    def on_select_point(self, selRect:SmartRectangle):
        # This method is called when a SmartRectangle is clicked. It updates point_1 and point_2 based on the selection.
        if self.point_1 is not  selRect :
           self.point_1 = selRect
        elif self.point_2 is not selRect and selRect is not self.point_1:
            self.point_2 = selRect

        # If the clicked rectangle is already selected, deselect it
        if self.point_1 is selRect:
            self.point_1 = None
        elif self.point_2 is selRect:
            self.point_2 = None

        # Print the selected points and their distances for debugging
        if self.point_1 is not None and self.point_2 is not None:
            print(f"Selected points: Point 1 at grid index {self.point_1.gridIndex} with distance {self.point_1.state.distant}, Point 2 at grid index {self.point_2.gridIndex} with distance {self.point_2.state.distant}")
          
      
    def get_rectangle_by_grid_index(self, gridIndex: Tuple[int,int]) -> SmartRectangle | None:
        if ( gridIndex[0] >=0 and  gridIndex[0] < len(self.smart_rectangles) ) and ( gridIndex[1] >=0 and  gridIndex[1] < len(self.smart_rectangles[0]) ) :
            return self.smart_rectangles[gridIndex[0]][gridIndex[1]]
        return None
    
    
    def Hover(self, id:int |None , gridIndex:Tuple[int,int]|None):
        if id is not None and gridIndex is not None and ( gridIndex[0] >=0 and  gridIndex[0] < len(self.smart_rectangles) ) and ( gridIndex[1] >=0 and  gridIndex[1] < len(self.smart_rectangles[0]) ) :
            item = self.smart_rectangles[gridIndex[0]][gridIndex[1]]
            self.itemconfig(item.id, fill="#00E5FF")
            print(f"Hovering over rectangle at grid index: {gridIndex} with distance: {item.state.distant} and id: {id}")
    
    
    def Unhover(self, id:int |None , gridIndex:Tuple[int,int]|None):
        if id is not None and gridIndex is not None and ( gridIndex[0] >=0 and  gridIndex[0] < len(self.smart_rectangles) ) and ( gridIndex[1] >=0 and  gridIndex[1] < len(self.smart_rectangles[0]) ) :
            item = self.smart_rectangles[gridIndex[0]][gridIndex[1]]
            item.auto_color()
            print(f"Unhovering rectangle at grid index: {gridIndex} with distance: {item.state.distant} and id: {id}")
       
    
    def update_point_states(self, new_point_states: List[List[PointState]]):
        self.point_states = new_point_states
        self.delete("all")  # Clear existing rectangles
        self.smart_rectangles.clear()
        self.create_smart_rectangles()