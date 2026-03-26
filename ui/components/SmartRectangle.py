# SmartRectangle: A custom rectangle widget that visually represents a point's state on a canvas.
import customtkinter as ctk
from collections.abc import Callable
from shared.protocol import PointState


class SmartRectangle:
    def __init__(
        self,
        canvas: ctk.CTkCanvas,
        state: PointState,
        gridIndex: tuple[int, int],
        hover: Callable,
        unhover: Callable,
        on_select: Callable,
        x1,
        y1,
        x2,
        y2,
        **kwargs,
    ):
        self.canvas = canvas
        self.state = state
        self.gridIndex = gridIndex
        self.on_select = on_select

        self.visual = {
            "tileBorder": "#1F2630",
            "hoverBorder": "#00E5FF",
            "selectedBorder": "#FF2FB3",
            "voidFill": "#0F1115",
            "defaultFill": "#151A21",
            "zoneFill": "#8B5CF6",
        }

        self.is_selected = False
        self.is_Zone = False
        self.is_void = False
        self.is_hovered = False

        self.color_selected = "#FF2FB3"
        self.main_color = self.visual["defaultFill"]

        self.id = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=self.main_color,
            outline=self.visual["tileBorder"],
            width=1,
            **kwargs,
        )

        self.canvas.tag_bind(self.id, "<Button-1>", lambda e: self.on_select(self))
        self.canvas.tag_bind(self.id, "<Enter>", lambda e: hover(self.id, self.gridIndex))
        self.canvas.tag_bind(self.id, "<Leave>", lambda e: unhover(self.id, self.gridIndex))

        self.auto_color()

    def setCoords(self, x1, y1, x2, y2):
        """Update the rectangle position."""
        self.canvas.coords(self.id, x1, y1, x2, y2)

    def setHover(self, hovered: bool):
        """Highlight the border on hover."""
        self.is_hovered = hovered
        self.applyOutline()

    def applyOutline(self):
        """Apply border style for normal, hover, and selected states."""
        if self.is_selected:
            self.canvas.itemconfig(
                self.id,
                outline=self.visual["selectedBorder"],
                width=2,
            )
            return

        if self.is_hovered:
            self.canvas.itemconfig(
                self.id,
                outline=self.visual["hoverBorder"],
                width=2,
            )
            return

        self.canvas.itemconfig(
            self.id,
            outline=self.visual["tileBorder"],
            width=1,
        )

    def auto_color(self):
        """Update fill color from the current point state."""
        distance = getattr(self.state, "distant", -1)

        self.is_void = distance is None or distance < 0 or distance >= 400

        if self.is_Zone:
            self.main_color = self.visual["zoneFill"]
        elif self.is_selected:
            self.main_color = self.color_selected
        elif self.is_void:
            self.main_color = self.visual["voidFill"]
        elif 0 <= distance < 80:
            self.main_color = "#E05252"
        elif 80 <= distance < 160:
            self.main_color = "#F08A3C"
        elif 160 <= distance < 240:
            self.main_color = "#F2C14E"
        elif 240 <= distance < 390:
            self.main_color = "#33B37E"
        elif 390 <= distance < 400:
            self.main_color = "#3B82F6"
        else:
            self.main_color = self.visual["defaultFill"]

        self.canvas.itemconfig(self.id, fill=self.main_color)
        self.applyOutline()