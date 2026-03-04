import customtkinter as ctk
from typing import Tuple
from shared.protocol import PointState


class SmartRectangle:
    def __init__(
        self,
        canvas: ctk.CTkCanvas,
        state: PointState,
        gridIndex: Tuple[int, int],
        hover,
        unhover,
        on_select,
        x1, y1, x2, y2,
        **kwargs
    ):
        self.canvas = canvas
        self.state: PointState = state
        self.gridIndex = gridIndex
        self.on_select = on_select

        # -------------------------
        # Visual tokens (local only)
        # -------------------------
        self.visual = {
            "tileBorder": "#1F2630",
            "hoverBorder": "#00E5FF",
            "selectedBorder": "#FF2FB3",
            "voidFill": "#0F1115",
            "defaultFill": "#151A21",
        }

        # Selection + hover state
        self.is_selected = False
        self.is_Zone = False
        self.is_void = False
        self.is_hovered = False

        # Keep your selected color (but now we also use outlines for clarity)
        self.color_selected = "#FF2FB3"

        # Current fill color (cached for fast restore)
        self.main_color = self.visual["defaultFill"]

        # Create the actual canvas item and store its ID
        # (Outline + width give a cleaner grid look than pure fill-only)
        self.id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=self.main_color,
            outline=self.visual["tileBorder"],
            width=1,
            **kwargs
        )

        # Bind interactions
        self.canvas.tag_bind(self.id, "<Button-1>", lambda e: self.on_select(self))
        self.canvas.tag_bind(self.id, "<Enter>", lambda e: hover(self.id, self.gridIndex))
        self.canvas.tag_bind(self.id, "<Leave>", lambda e: unhover(self.id, self.gridIndex))

        # Initial color based on distance
        self.auto_color()

    # -------------------------
    # Layout helper
    # -------------------------
    def setCoords(self, x1, y1, x2, y2):
        """UI-only: update rectangle position without recreating."""
        self.canvas.coords(self.id, x1, y1, x2, y2)

    # -------------------------
    # Hover helper
    # -------------------------
    def setHover(self, hovered: bool):
        """UI-only: hover is an outline highlight, not a full fill override."""
        self.is_hovered = hovered
        self.applyOutline()

    def applyOutline(self):
        """Apply outline based on hover/selection state."""
        if self.is_selected:
            self.canvas.itemconfig(self.id, outline=self.visual["selectedBorder"], width=2)
            return
        if self.is_hovered:
            self.canvas.itemconfig(self.id, outline=self.visual["hoverBorder"], width=2)
            return
        self.canvas.itemconfig(self.id, outline=self.visual["tileBorder"], width=1)

    # -------------------------
    # Color logic (UI-facing)
    # -------------------------
    def auto_color(self):
        """
        UI-only color mapping for distances.
        Keeps your thresholds but uses a cleaner palette + fixes "sticky void".
        """
        distance = getattr(self.state, "distant", -1)

        # Fix: void should be computed fresh each time (not sticky forever)
        invalid = distance is None or distance < 0
        voidNow = invalid or (distance >= 400)

        self.is_void = bool(voidNow)

        if  self.is_Zone:
            self.main_color = "#8B5CF6"   # purple
            self.canvas.itemconfig(self.id, fill=self.main_color)
            self.applyOutline()
            return

        # Selection: keep your strong highlight
        if self.is_selected:
            self.main_color = self.color_selected
            self.canvas.itemconfig(self.id, fill=self.main_color)
            self.applyOutline()
            return

        # Void: disappear into background
        if self.is_void:
            self.main_color = self.visual["voidFill"]
            self.canvas.itemconfig(self.id, fill=self.main_color)
            self.applyOutline()
            return

        # Distance palette (same ranges, cleaner tones)
        if 0 <= distance < 80:
            self.main_color = "#E05252"   # red
        elif 80 <= distance < 160:
            self.main_color = "#F08A3C"   # orange
        elif 160 <= distance < 240:
            self.main_color = "#F2C14E"   # amber
        elif 240 <= distance < 390:
            self.main_color = "#33B37E"   # green
        elif 390 <= distance < 400:
            self.main_color = "#3B82F6"   # blue
        else:
            self.main_color = self.visual["defaultFill"]

        self.canvas.itemconfig(self.id, fill=self.main_color)
        self.applyOutline()
