# SmartCanvas: A custom canvas widget for visualizing and interacting with a grid of points.
from customtkinter import CTkCanvas
from typing import List
from dataclasses import replace

from shared.protocol import PointState, ScanLimits
from ui.components.SmartRectangle import SmartRectangle


class SmartCanvas(CTkCanvas):
    def __init__(
        self,
        parent,
        send_cmd,
        width: int,
        height: int,
        point_states: List[List[PointState]],
        **kwargs
    ):
        super().__init__(parent, width=width, height=height, **kwargs)

        self.send_cmd = send_cmd
        self.point_states = point_states

        self.MIN_ANGLE = -50.0
        self.MAX_ANGLE = 50.0
        self.ANGLE_STEP = 1

        self.smart_rectangles: List[List[SmartRectangle]] = []
        self.rect_map: dict[tuple[int, int], SmartRectangle] = {}

        self.point_1: SmartRectangle | None = None
        self.point_2: SmartRectangle | None = None

        self.grid_cols = 0
        self.grid_rows = 0

        self.canvas_colors = {
            "background": "#0F1115",
            "gridPadding": 10,
            "cellGap": 3,
        }

        self.configure(
            background=self.canvas_colors["background"],
            highlightthickness=0,
            bd=0,
        )

        self.MAX_ANGLE = 100
        self.ANGLE_STEP = 1
        self.resize_job = None

        self.recompute_grid_dims()
        self.create_smart_rectangles()
        self.bind("<Configure>", self.on_canvas_resize)

    # Layout -------------------------------------------------

    def on_canvas_resize(self, _event=None):
        """Debounce resize updates."""
        if self.resize_job is not None:
            try:
                self.after_cancel(self.resize_job)
            except Exception:
                pass

        self.resize_job = self.after(20, self.layout_rectangles)

    def layout_rectangles(self):
       
       """Update rectangle positions for current canvas size."""
       if not self.smart_rectangles or self.grid_cols == 0 or self.grid_rows == 0:
            return

       canvas_width = self.winfo_width() if self.winfo_width() > 5 else self.winfo_reqwidth()
       canvas_height = self.winfo_height() if self.winfo_height() > 5 else self.winfo_reqheight()

       pad = self.canvas_colors["gridPadding"]
       gap = self.canvas_colors["cellGap"]

       usable_width = max(1, canvas_width - (pad * 2))
       usable_height = max(1, canvas_height - (pad * 2))

       cell_width = usable_width / self.grid_cols
       cell_height = usable_height / self.grid_rows
       inset = gap / 2

       for y in range(self.grid_rows):
            
            for x in range(self.grid_cols):
                rect = self.smart_rectangles[y][x]
                
                # Calculate centered range
                x1 = pad + (x * cell_width) + inset
                y1 = pad + (y * cell_height) + inset
                x2 = pad + ((x + 1) * cell_width) - inset
                y2 = pad + ((y + 1) * cell_height) - inset

                rect.setCoords(x1, y1, x2, y2)

    def create_smart_rectangles(self):
       if not self.grid_cols or not self.grid_rows:
            return
       

       self.smart_rectangles.clear()
       self.rect_map.clear()

       for y in range(self.grid_rows):
            row_rectangles: List[SmartRectangle] = []
            for x in range(self.grid_cols):
               
                state = PointState(x, y, -1) 
                
                rect = SmartRectangle(
                    self,
                    state,
                    gridIndex=(x, y),
                    hover=self.Hover,
                    unhover=self.Unhover,
                    on_select=self.on_select_point,
                    x1=0, y1=0, x2=10, y2=10,
                )
                row_rectangles.append(rect)
                self.rect_map[(x, y)] = rect
            self.smart_rectangles.append(row_rectangles)

       self.after_idle(self.layout_rectangles)

    # Grid helpers ------------------------------------------

    def recompute_grid_dims(self):
        total_range = self.MAX_ANGLE - self.MIN_ANGLE
        steps = int(round(total_range / self.ANGLE_STEP))
        self.grid_cols = steps + 1
        self.grid_rows = steps + 1

    def angle_to_index(self, angle: float, max_index: int) -> int:
       # Shift angle by the minimum to normalize to a 0-start range
        normalized_angle = angle - self.MIN_ANGLE
        idx = int(round(normalized_angle / self.ANGLE_STEP))
        return max(0, min(idx, max_index))

    def index_to_angle(self, idx: int) -> float:
        return self.MIN_ANGLE + (idx * self.ANGLE_STEP)

    def get_rectangle_by_coordinates(self, x: int, y: int) -> SmartRectangle | None:
        return self.rect_map.get((x, y))

    # Point updates -----------------------------------------

    def setPoint(self, state: PointState):
        """Update one point."""
        rect = self.get_rectangle_by_coordinates(state.x, state.y)
        if rect is None:
            return

        rect.state.distant = state.distant
        rect.auto_color()

    def Update_point_grid(self, new_embedded_points: List[PointState]):
        """Update a batch of scan points."""
        for state in new_embedded_points:
            x = self.angle_to_index(state.x, self.grid_cols - 1)
            y = self.angle_to_index(state.y, self.grid_rows - 1)

            rect = self.get_rectangle_by_coordinates(x, y)
            if rect is None:
                continue

            rect.state.distant = state.distant
            rect.auto_color()

    # Selection ---------------------------------------------
    def update_grid_range(self, x_range: tuple[float, float], y_range: tuple[float, float], step: float):
        """Update the canvas grid to match the calibrated scan volume."""
        # Use the wider of the two ranges to keep the grid square, or use specific limits
        self.MIN_ANGLE = min(x_range[0], y_range[0])
        self.MAX_ANGLE = max(x_range[1], y_range[1])
        self.ANGLE_STEP = step
        
        # Clear existing visual blocks
        for row in self.smart_rectangles:
            for rect in row:
                self.delete(rect.id)
        
        # Re-build the grid for the new 'Scan Volume'
        self.recompute_grid_dims()
        self.create_smart_rectangles()
    def sendNewScanRange(self):
        if self.point_1 is None or self.point_2 is None:
            return None

        x1, y1 = self.point_1.state.x, self.point_1.state.y
        x2, y2 = self.point_2.state.x, self.point_2.state.y

        motor_x_limit = (
            self.index_to_angle(min(x1, x2)),
            self.index_to_angle(max(x1, x2)),
        )
        motor_y_limit = (
            self.index_to_angle(min(y1, y2)),
            self.index_to_angle(max(y1, y2)),
        )

        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                rect = self.get_rectangle_by_coordinates(x, y)
                if rect is None:
                    continue

                rect.is_selected = False
                rect.is_Zone = True
                rect.auto_color()

        print(
            f"""
            --------------- Min-Max Scan Range Selected ---------------
            Scan Range X: [{motor_x_limit[0]:.2f}, {motor_x_limit[1]:.2f}]
            Scan Range Y: [{motor_y_limit[0]:.2f}, {motor_y_limit[1]:.2f}]
            """
        )

        self.send_cmd(ScanLimits(X=motor_x_limit, Y=motor_y_limit))
        return motor_x_limit, motor_y_limit

    def on_select_point(self, selected_rect: SmartRectangle):
        if self.point_1 and self.point_1.id == selected_rect.id:
            self._deselect_point_1()
            return

        if self.point_2 and self.point_2.id == selected_rect.id:
            self._deselect_point_2()
            return

        if self.point_1 is None:
            self.point_1 = selected_rect
            self.point_1.is_selected = True
            self.point_1.auto_color()
            print(
                f"Selected Point 1 at [grid index {self.point_1.gridIndex}] "
                f"| [coord pos {self.point_1.state.x}, {self.point_1.state.y}] "
                f"with distance {self.point_1.state.distant}"
            )
            return

        if self.point_2 is None:
            self.point_2 = selected_rect
            self.point_2.is_selected = True
            self.point_2.auto_color()
            print(
                f"Selected Point 2 at [grid index {self.point_2.gridIndex}] "
                f"| [coord pos {self.point_2.state.x}, {self.point_2.state.y}] "
                f"with distance {self.point_2.state.distant}"
            )
            print("----------------------------------------------------")
            self.sendNewScanRange()
            return

        print("Both points are already selected. Stop selecting more.")

    def _deselect_point_1(self):
        if self.point_1 is None:
            return

        print(
            f"Deselected Point 1 at [grid index {self.point_1.gridIndex}] "
            f"| [coord pos {self.point_1.state.x}, {self.point_1.state.y}] "
            f"with distance {self.point_1.state.distant}"
        )
        self.point_1.is_selected = False
        self.point_1.auto_color()
        self.point_1 = None

    def _deselect_point_2(self):
        if self.point_2 is None:
            return

        print(
            f"Deselected Point 2 at [grid index {self.point_2.gridIndex}] "
            f"| [coord pos {self.point_2.state.x}, {self.point_2.state.y}] "
            f"with distance {self.point_2.state.distant}"
        )
        self.point_2.is_selected = False
        self.point_2.auto_color()
        self.point_2 = None

    def clear(self):
        """Reset the grid state."""
        for row in self.smart_rectangles:
            for rect in row:
                rect.state = replace(rect.state, distant=-1)
                rect.is_selected = False
                rect.is_Zone = False
                rect.auto_color()

        self.point_1 = None
        self.point_2 = None

    # Hover --------------------------------------------------

    def Hover(self, _id=None, gridIndex=None):
        if gridIndex is None:
            return

        rect = self.get_rectangle_by_coordinates(gridIndex[0], gridIndex[1])
        if rect is not None:
            rect.setHover(True)

    def Unhover(self, _id=None, gridIndex=None):
        if gridIndex is None:
            return

        rect = self.get_rectangle_by_coordinates(gridIndex[0], gridIndex[1])
        if rect is not None:
            rect.setHover(False)