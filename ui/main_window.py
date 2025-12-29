from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QPushButton, QFrame, QLabel
)
from ui.components.motor_panel import MotorPanel

from ui.controller import Controller



class MainWindow(QMainWindow):
    def __init__(self ,Title ="Pi Control Panel (Qt)" , size =(1000 , 1000)):
        super().__init__()
        self.setWindowTitle(Title)
        self.resize(size[0], size[1])
        self.controller = Controller()
        # 2. Main Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 3. Main Vertical Layout (Splits Top Control area vs Bottom Canvas)
        self.main_layout = QVBoxLayout(self.central_widget)

        # ============================================================
        # SECTION A: TOP AREA (Controllers + List)
        # ============================================================
        self.top_container = QWidget()
        self.top_layout = QHBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(0, 0, 0, 0)  # Optional cleanup

        # --- A1. Left Side (Motors + Buttons) ---
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)

        # Part 1: Motor Controller (Pink Area)
        self.motor_container = QWidget()
        self.motor_layout = QHBoxLayout(self.motor_container)

        self.motorX = MotorPanel(self.controller, axis='x', parent=self)
        self.motorY = MotorPanel(self.controller, axis='y', parent=self)

        self.motor_layout.addWidget(self.motorX)
        self.motor_layout.addWidget(self.motorY)

        # Part 2: Button Grid (Blue Area)
        self.button_container = QWidget()
        self.button_grid = QGridLayout(self.button_container)

        # Adding dummy buttons to match your 2x3 grid
        button_names = ["Button 1", "Button 2", "Button 3",
                        "Button 4", "Button 5", "Button 6"]

        for i, name in enumerate(button_names):
            btn = QPushButton(name)
            row = i // 3  # 0, 0, 0, 1, 1, 1
            col = i % 3  # 0, 1, 2, 0, 1, 2
            self.button_grid.addWidget(btn, row, col)

        # Add parts to Left Panel
        self.left_layout.addWidget(self.motor_container)
        self.left_layout.addWidget(self.button_container)
        self.left_layout.addStretch()  # Pushes everything up

        # --- A2. Right Side (Scroll Area) (Purple Area) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # Placeholder content for scroll area
        self.scroll_content = QLabel("List of points goes here...\n" * 20)
        self.scroll_area.setWidget(self.scroll_content)

        # Add Left and Right to Top Layout
        self.top_layout.addWidget(self.left_panel, stretch=2)  # 2/3 width
        self.top_layout.addWidget(self.scroll_area, stretch=1)  # 1/3 width

        # ============================================================
        # SECTION B: BOTTOM AREA (Canvas/SVG) (Grey Area)
        # ============================================================
        self.canvas_area = QFrame()
        self.canvas_area.setFrameShape(QFrame.Shape.StyledPanel)
        self.canvas_area.setStyleSheet("background-color: #DDDDDD;")  # Just to visualize grey area

        # Label placeholder
        canvas_label = QLabel("SVG or Canvas Area", self.canvas_area)
        canvas_label.move(20, 20)

        # ============================================================
        # FINAL ASSEMBLY
        # ============================================================

        # Add Top Section and Bottom Section to Main Layout
        self.main_layout.addWidget(self.top_container, stretch=1)  # Top takes less height
        self.main_layout.addWidget(self.canvas_area, stretch=2)  # Canvas takes more height





