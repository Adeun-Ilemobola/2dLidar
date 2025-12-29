from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QSlider,  QPushButton , QHBoxLayout, QVBoxLayout , QCheckBox ,
)
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Qt, Slot
from ui.controller import Controller
from shared.protocol import MotorAngleState ,Axis
beautiful_line_edit_style = """
    QLineEdit {
        background-color: #2b2b2b;
        color: #e0e0e0;
        border: 2px solid #3f3f3f;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 14px;
        selection-background-color: #4a90e2;
    }

    QLineEdit:hover {
        border: 2px solid #505050;
    }

    QLineEdit:focus {
        border: 2px solid #4a90e2;
        background-color: #323232;
    }

    QLineEdit:disabled {
        background-color: #1e1e1e;
        color: #777777;
        border: 2px solid #252525;
    }
"""
unified_style = """
    /* --- QPushButton Design --- */
    QPushButton {
        background-color: #4a90e2;
        color: white;
        border-radius: 6px;
        padding: 6px 15px;
        font-weight: bold;
        font-size: 13px;
        border: none;
    }
    QPushButton:hover {
        background-color: #357abd;
    }
    QPushButton:pressed {
        background-color: #2a5f96;
    }

    /* --- QSlider Design --- */
    QSlider::groove:horizontal {
        border: 1px solid #3f3f3f;
        height: 6px;
        background: #2b2b2b;
        margin: 2px 0;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #4a90e2;
        border: 1px solid #4a90e2;
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #67a6f0;
    }

    /* --- QCheckBox Design --- */
    QCheckBox {
        color: #e0e0e0;
        spacing: 8px;
        font-size: 14px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #3f3f3f;
        background-color: #2b2b2b;
    }
    QCheckBox::indicator:checked {
        background-color: #4a90e2;
        border: 2px solid #4a90e2;
        /* You can add a checkmark image here if you have one */
    }
    QCheckBox::indicator:hover {
        border: 2px solid #505050;
    }
"""


universal_container_style = """
    /* The Main Panel Container */
    MotorPanel {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 12px;
    }

    /* Labels inside the container */
    QLabel {
        color: #bbbbbb;
        font-family: 'Segoe UI', sans-serif;
    }

    /* The Section Title */
    QLabel#panelTitle {
        color: #ffffff;
        font-size: 18px;
        font-weight: bold;
        padding-bottom: 5px;
    }

    /* Grouping Rows/Boxes (if using QFrame) */
    QFrame#rowContainer {
        background-color: #252525;
        border-radius: 8px;
    }
"""
# Apply this to the whole panel
MODERN_DARK_QSS = """
/* ---------- Base ---------- */
* {
    font-family: Inter, Segoe UI, Arial;
    font-size: 13px;
}

QToolTip {
    background: #151a21;
    color: #e7ecf2;
    border: 1px solid #2a3240;
    padding: 6px 8px;
    border-radius: 8px;
}

/* ---------- Buttons ---------- */
QPushButton {
    background: #1a2230;
    border: 1px solid #2a3446;
    padding: 8px 12px;
    border-radius: 10px;
}
QPushButton:hover { background: #202a3a; border-color: #344158; }
QPushButton:pressed { background: #141b27; }
QPushButton:disabled { color: #738099; background: #121723; border-color: #1f2736; }

/* "Primary" button by objectName */
QPushButton#primaryButton {
    background: #2d6cff;
    border: 1px solid #2d6cff;
    color: #0b1020;
    font-weight: 600;
}
QPushButton#primaryButton:hover { background: #3a79ff; }
QPushButton#primaryButton:pressed { background: #2559d4; }

/* "Danger" button by objectName */
QPushButton#dangerButton {
    background: #ff3b5c;
    border: 1px solid #ff3b5c;
    color: #24060d;
    font-weight: 600;
}
QPushButton#dangerButton:hover { background: #ff5672; }
QPushButton#dangerButton:pressed { background: #d62f4b; }

/* ---------- Inputs ---------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #121723;
    border: 1px solid #273043;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #2d6cff;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
    border-color: #3a4964;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2d6cff;
}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
    color: #7a879f;
    background: #0f141f;
}

/* ComboBox popup */
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow {
    width: 10px; height: 10px;
    /* Optional asset */
   
}
/* If you don't have the asset, comment the image line above and use this:
QComboBox::down-arrow { border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #9aa7bd; }
*/
QAbstractItemView {
    background: #121723;
    border: 1px solid #273043;
    padding: 6px;
    outline: 0px;
    selection-background-color: #203a76;
    border-radius: 10px;
}

/* ---------- CheckBox / Radio ---------- */
QCheckBox, QRadioButton {
    spacing: 10px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px; height: 18px;
    border-radius: 6px;
    background: #121723;
    border: 1px solid #2a3446;
}
QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: #3a4964; }

QCheckBox::indicator:checked {
    background: #2d6cff;
    border: 1px solid #2d6cff;
    /* Optional asset: a white check SVG */
    image: url(:/icons/check.svg);
}
QCheckBox::indicator:checked:disabled { background: #2348a1; border-color: #2348a1; }

QRadioButton::indicator {
    border-radius: 9px;
}
QRadioButton::indicator:checked {
    background: #121723;
    border: 1px solid #2d6cff;
    /* inner dot */
}
QRadioButton::indicator:checked {
    image: url(:/icons/radio-dot.svg);
}

/* ---------- Sliders ---------- */
QSlider { min-height: 28px; }
QSlider::groove:horizontal {
    height: 8px;
    background: #131a28;
    border: 1px solid #273043;
    border-radius: 5px;
}
QSlider::sub-page:horizontal {
    background: #2d6cff;
    border-radius: 5px;
}
QSlider::add-page:horizontal {
    background: #131a28;
    border-radius: 5px;
}
QSlider::handle:horizontal {
    width: 18px;
    margin: -6px 0; /* makes handle sit centered */
    border-radius: 9px;
    background: #e7ecf2;
    border: 2px solid #2d6cff;
}
QSlider::handle:horizontal:hover {
    background: #ffffff;
}
QSlider::handle:horizontal:pressed {
    background: #d7def0;
}

/* Vertical slider too */
QSlider::groove:vertical {
    width: 8px;
    background: #131a28;
    border: 1px solid #273043;
    border-radius: 5px;
}
QSlider::sub-page:vertical { background: #131a28; border-radius: 5px; }
QSlider::add-page:vertical { background: #2d6cff; border-radius: 5px; }
QSlider::handle:vertical {
    height: 18px;
    margin: 0 -6px;
    border-radius: 9px;
    background: #e7ecf2;
    border: 2px solid #2d6cff;
}

/* ---------- Scrollbars (nice to have) ---------- */
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 10px 2px 10px 2px;
}
QScrollBar::handle:vertical {
    background: #273043;
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #33405a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 2px 10px 2px 10px;
}
QScrollBar::handle:horizontal {
    background: #273043;
    border-radius: 6px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #33405a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
"""

class MotorPanel(QWidget):
    def __init__(self, controller:Controller, axis: Axis, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.angle = 0.00
        self.is_offsetMode = False
        self.offsetMode_Angle = 0.0
        self.axis = axis

        # ---  Widgets ---
        self.title = QLabel(f"Motor {axis.upper()}")
        self.status = QLabel("Status: unknown")
        self.AngleL = QLabel(f"Angle: {self.angle}")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 270)
        self.slider.valueChanged.connect(self.on_slider_move)

        self.sendNewAngle = QPushButton("Send New Angle")
        self.sendNewAngle.clicked.connect(self.on_sendNewAngleBtu)
        self.offsetMode = QCheckBox("Offset Mode")
        self.AngleTextInput = QLineEdit()
        self.AngleTextInput.setFixedWidth(95)  # Keep input box small

        # ---  Styling ---



        self.title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 0px;")
        self.status.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        self.AngleL.setStyleSheet("font-size: 13px; color: #aaaaaa;")

        # self.AngleTextInput.setStyleSheet(beautiful_line_edit_style)
        # self.slider.setStyleSheet(unified_style)
        # self.sendNewAngle.setStyleSheet(unified_style)
        # self.offsetMode.setStyleSheet(unified_style)
        self.setStyleSheet(MODERN_DARK_QSS)

        # ---  Layouts ---
        self.main_layout = QVBoxLayout(self)
        # self.main_layout.setContentsMargins(10, 5, 10, 5)  # Tighten edges
        self.main_layout.setSpacing(5)  # Tighten widget gaps

        # Row 1: Labels (Align them so they stay close to the title)
        self.col1 = QHBoxLayout()
        self.col1.addWidget(self.status)
        self.col1.addSpacing(20)  # Small gap between Status and Angle
        self.col1.addWidget(self.AngleL)
        self.col1.addStretch()  # Pushes labels to the left

        # Assemble
        self.main_layout.addWidget(self.title)
        self.main_layout.addLayout(self.col1)
        self.main_layout.addWidget(self.slider)

        self.col3 = QHBoxLayout()
        self.col3.addWidget(self.AngleTextInput)
        self.col3.addWidget(self.sendNewAngle)
        self.col3.addWidget(self.offsetMode)
        self.col3.addStretch()  # Pushes input/button to the left
        self.main_layout.addLayout(self.col3)



        # THE FIX: Add stretch at bottom to stop vertical expansion
        self.main_layout.addStretch()

        # CONSTRAIN SIZE
        self.setFixedHeight(160)
        self.setFixedWidth(360)

    @Slot()
    def on_sendNewAngleBtu(self):
        text = self.AngleTextInput.text()
        if text.isdigit():
            if self.is_offsetMode:
                self.offsetMode_Angle = float(text)
            else:
               self.angle = float(text)
               self.send()


        else:
            self.AngleTextInput.setText("0")

    @Slot(int)
    def on_slider_move(self, value):
        self.controller.send(
            MotorAngleState(
                self.axis,
                float(value),
                self.offsetMode_Angle,
                True
            )
        )

    def send(self):
        self.controller.send(
            MotorAngleState(
                self.axis,
                self.angle,
                self.offsetMode_Angle,
                True
            )
        )
