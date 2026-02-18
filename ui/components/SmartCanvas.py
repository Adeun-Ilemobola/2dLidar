# components/SmartCanvas.py
from customtkinter import CTkCanvas
from typing import List, Tuple, Optional
from shared.protocol import PointState
from ui.components.SmartRectangle import SmartRectangle


class SmartCanvas(CTkCanvas):
    def __init__(
        self,
        parent,
        width: int,
        height: int,
        point_states: List[List[PointState]],
        **kwargs
    ):
        super().__init__(parent, width=width, height=height, **kwargs)

        # Grid data
        self.point_states = point_states
        self.smart_rectangles: List[List[SmartRectangle]] = []

        # Selected points (kept as-is for your logic)
        self.point_1: SmartRectangle | None = None
        self.point_2: SmartRectangle | None = None

        # --- Visual tokens (local only) ---
        self.canvasColors = {
            "background": "#0F1115",   # main canvas background
            "gridPadding": 10,         # space around grid
            "cellGap": 3,              # gap between cells
        }

        # Canvas appearance (clean, no default Tk highlight border)
        self.configure(
            background=self.canvasColors["background"],
            highlightthickness=0,
            bd=0,
        )

        # Used to debounce resize handling
        self.resizeJob = None

        # Build rectangles once (positions get updated on first resize/layout)
        self.create_smart_rectangles()

        # Keep layout responsive when the canvas resizes
        self.bind("<Configure>", self.onCanvasResize)

    # -------------------------
    # Layout and rendering
    # -------------------------
    def onCanvasResize(self, _event=None):
        """Debounced resize: reposition rectangles without rebuilding objects."""
        if self.resizeJob is not None:
            try:
                self.after_cancel(self.resizeJob)
            except Exception:
                pass
        self.resizeJob = self.after(20, self.layoutRectangles)

    def layoutRectangles(self):
        """Recompute rectangle coordinates based on current canvas size."""
        if not self.smart_rectangles:
            return

        rows = len(self.smart_rectangles)
        cols = len(self.smart_rectangles[0]) if rows else 0
        if cols == 0:
            return

        # Use current displayed size (fallback to requested size if not ready)
        canvasWidth = self.winfo_width() if self.winfo_width() > 5 else self.winfo_reqwidth()
        canvasHeight = self.winfo_height() if self.winfo_height() > 5 else self.winfo_reqheight()

        pad = self.canvasColors["gridPadding"]
        gap = self.canvasColors["cellGap"]

        usableW = max(1, canvasWidth - (pad * 2))
        usableH = max(1, canvasHeight - (pad * 2))

        cellW = usableW / cols
        cellH = usableH / rows

        # Place each rect with a consistent gap “inset”
        inset = gap / 2

        for i in range(rows):
            for j in range(cols):
                rect = self.smart_rectangles[i][j]

                x1 = pad + (j * cellW) + inset
                y1 = pad + (i * cellH) + inset
                x2 = pad + ((j + 1) * cellW) - inset
                y2 = pad + ((i + 1) * cellH) - inset

                rect.setCoords(x1, y1, x2, y2)

    def create_smart_rectangles(self):
        """Create SmartRectangle objects once; layout is handled separately."""
        if not self.point_states:
            return

        rows = len(self.point_states)
        cols = len(self.point_states[0]) if rows > 0 else 0
        if cols == 0:
            return

        self.smart_rectangles.clear()

        for i in range(rows):
            row_rectangles: List[SmartRectangle] = []
            for j in range(cols):
                state = self.point_states[i][j]
                gridIndex = (i, j)

                # Create with placeholder coords; layoutRectangles will set final positions
                smart_rect = SmartRectangle(
                    self,
                    state,
                    gridIndex=gridIndex,
                    hover=self.Hover,
                    unhover=self.Unhover,
                    on_select=self.on_select_point,
                    x1=0, y1=0, x2=10, y2=10,
                )
                row_rectangles.append(smart_rect)

            self.smart_rectangles.append(row_rectangles)

        # Ensure we place them correctly once the widget is realized
        self.after_idle(self.layoutRectangles)

    # -------------------------
    # Public update helpers
    # -------------------------
    def setPoint(self, state: PointState):
        """Update a single point's distance and refresh its color."""
        rect = self.get_rectangle_by_coordinates(state.x, state.y)
        if rect:
            rect.state.distant = state.distant
            rect.auto_color()

    def update_point_states(self, new_point_states: List[List[PointState]]):
        """Replace the entire grid and rebuild rectangles."""
        self.point_states = new_point_states

        # Clear existing rectangles
        self.delete("all")
        self.smart_rectangles.clear()

        # Reset selection pointers because old rectangle IDs are gone
        self.point_1 = None
        self.point_2 = None

        self.create_smart_rectangles()

    def Update_point_grid(self, new_point_state: List[PointState]):
        """Batch update a list of points (your existing method name kept)."""
        for state in new_point_state:
            rect = self.get_rectangle_by_coordinates(state.x, state.y)
            if rect:
                rect.state.distant = state.distant
                rect.auto_color()

    # -------------------------
    # Selection logic (unchanged)
    # -------------------------
    def on_select_point(self, selRect: SmartRectangle):
        if (
            (self.point_1 is not None and self.point_2 is not None)
            and (selRect.id != self.point_1.id and selRect.id != self.point_2.id)
        ):
            print("Both points are already selected. stop selecting more.")
            return

        if self.point_1 is not selRect and self.point_1 is None:
            self.point_1 = selRect
            self.point_1.is_selected = True
            self.point_1.auto_color()
            print(
                f"Selected Point 1 at [ grid index {self.point_1.gridIndex}] "
                f"| [cod pos {self.point_1.state.x}, {self.point_1.state.y}] "
                f"with distance {self.point_1.state.distant}"
            )
            return

        elif (self.point_2 is not selRect and self.point_2 is None) and selRect is not self.point_1:
            self.point_2 = selRect
            self.point_2.is_selected = True
            self.point_2.auto_color()
            print(
                f"Selected Point 2 at [ grid index {self.point_2.gridIndex}] "
                f"| [cod pos {self.point_2.state.x}, {self.point_2.state.y}] "
                f"with distance {self.point_2.state.distant}"
            )
            return

        # Deselect if clicked again
        if self.point_1 and self.point_1.id == selRect.id:
            print(
                f"Deselected Point 1 at [ grid index {self.point_1.gridIndex}] "
                f"| [cod pos {self.point_1.state.x}, {self.point_1.state.y}] "
                f"with distance {self.point_1.state.distant}"
            )
            self.point_1.is_selected = False
            self.point_1.auto_color()
            self.point_1 = None

        if self.point_2 and self.point_2.id == selRect.id:
            print(
                f"Deselected Point 2 at [ grid index {self.point_2.gridIndex}] "
                f"| [cod pos {self.point_2.state.x}, {self.point_2.state.y}] "
                f"with distance {self.point_2.state.distant}"
            )
            self.point_2.is_selected = False
            self.point_2.auto_color()
            self.point_2 = None

    # -------------------------
    # Lookups 
    # -------------------------
    def get_rectangle_by_grid_index(self, gridIndex: Tuple[int, int]) -> SmartRectangle | None:
        if (
            (gridIndex[0] >= 0 and gridIndex[0] < len(self.smart_rectangles))
            and (gridIndex[1] >= 0 and gridIndex[1] < len(self.smart_rectangles[0]))
        ):
            return self.smart_rectangles[gridIndex[0]][gridIndex[1]]
        return None

    def get_rectangle_by_coordinates(self, x: int, y: int) -> SmartRectangle | None:
        for row in self.smart_rectangles:
            for rect in row:
                if rect.state.x == x and rect.state.y == y:
                    return rect
        return None

    # -------------------------
    # Hover handling 
    # -------------------------
    def Hover(self, _id: int | None, gridIndex: Tuple[int, int] | None):
        """UI-only hover: outline highlight without destroying fill color."""
        if gridIndex is None:
            return
        item = self.get_rectangle_by_grid_index(gridIndex)
        if item:
            item.setHover(True)

    def Unhover(self, _id: int | None, gridIndex: Tuple[int, int] | None):
        """UI-only unhover: restore outline + fill based on state."""
        if gridIndex is None:
            return
        item = self.get_rectangle_by_grid_index(gridIndex)
        if item:
            item.setHover(False)
