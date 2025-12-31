from ui.main_window import MainWindow
import sys
from PySide6.QtWidgets import QApplication
SHADCN_QSS = """
/* ===== Base ===== */
* {
  font-family: "Inter","Segoe UI","SF Pro Text","Helvetica","Arial";
  font-size: 12.5px;
  color: #e5e7eb;
}

QMainWindow, QDialog, QWidget {
  background: #0b0f14;
}

QLabel[muted="true"] { color: #9ca3af; }

/* Card containers */
QFrame[card="true"], QWidget[card="true"], QGroupBox {
  background: #0f172a;
  border: 1px solid #1f2937;
  border-radius: 12px;
}

QGroupBox {
  margin-top: 10px;
  padding: 10px;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 12px;
  padding: 0 6px;
  color: #9ca3af;
}

/* ===== Buttons ===== */
QPushButton, QToolButton {
  background: #111827;
  border: 1px solid #1f2937;
  border-radius: 10px;
  padding: 8px 12px;
}
QPushButton:hover, QToolButton:hover { background: #162033; }
QPushButton:pressed, QToolButton:pressed { background: #1b2a46; }
QPushButton:disabled, QToolButton:disabled {
  color: #9ca3af;
  background: #0f172a;
}

/* Variants: btn.setProperty("variant","primary"/"danger"/"ghost") */
QPushButton[variant="primary"] {
  background: #3b82f6;
  border: 1px solid #2563eb;
  color: #ffffff;
  font-weight: 600;
}
QPushButton[variant="primary"]:hover { background: #2563eb; }

QPushButton[variant="danger"] {
  background: #ef4444;
  border: 1px solid #ef4444;
  color: #ffffff;
  font-weight: 600;
}

QPushButton[variant="ghost"] {
  background: transparent;
  border: 1px solid transparent;
}
QPushButton[variant="ghost"]:hover {
  background: #162033;
  border: 1px solid #1f2937;
}

/* ===== Inputs ===== */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
  background: #0b1220;
  border: 1px solid #1f2937;
  border-radius: 10px;
  padding: 8px 10px;
  selection-background-color: #1d4ed8;
  selection-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
  border: 1px solid #3b82f6;
}

QComboBox QAbstractItemView {
  background: #111827;
  border: 1px solid #1f2937;
  border-radius: 10px;
  padding: 6px;
  selection-background-color: #1d4ed8;
  selection-color: #ffffff;
  outline: 0;
}

/* ===== Check / Radio ===== */
QCheckBox, QRadioButton { spacing: 10px; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }

QCheckBox::indicator {
  border: 1px solid #1f2937;
  border-radius: 4px;
  background: #0b1220;
}
QCheckBox::indicator:checked {
  background: #3b82f6;
  border: 1px solid #2563eb;
}

QRadioButton::indicator {
  border: 1px solid #1f2937;
  border-radius: 8px;
  background: #0b1220;
}
QRadioButton::indicator:checked {
  background: #3b82f6;
  border: 1px solid #2563eb;
}

/* ===== Slider / Progress ===== */
QSlider::groove:horizontal {
  height: 6px;
  background: #1f2937;
  border-radius: 3px;
}
QSlider::handle:horizontal {
  width: 16px;
  margin: -6px 0;
  border-radius: 8px;
  background: #3b82f6;
  border: 1px solid #2563eb;
}
QProgressBar {
  background: #0f172a;
  border: 1px solid #1f2937;
  border-radius: 10px;
  text-align: center;
  padding: 2px;
}
QProgressBar::chunk {
  border-radius: 8px;
  background: #3b82f6;
}

/* ===== Lists / Trees / Tables ===== */
QListWidget, QTreeWidget, QTableView {
  background: #0f172a;
  border: 1px solid #1f2937;
  border-radius: 12px;
  padding: 6px;
  selection-background-color: #1d4ed8;
  selection-color: #ffffff;
  outline: 0;
}
QListWidget::item, QTreeWidget::item { padding: 8px; border-radius: 8px; }
QListWidget::item:hover, QTreeWidget::item:hover { background: #162033; }

QHeaderView::section {
  background: #111827;
  border: 0px;
  border-bottom: 1px solid #1f2937;
  padding: 8px 10px;
  color: #9ca3af;
  font-weight: 600;
}

/* ===== Tabs ===== */
QTabWidget::pane {
  border: 1px solid #1f2937;
  border-radius: 12px;
  top: -1px;
  background: #0f172a;
}
QTabBar::tab {
  background: transparent;
  border: 1px solid transparent;
  padding: 8px 12px;
  margin-right: 4px;
  border-radius: 10px;
  color: #9ca3af;
}
QTabBar::tab:hover { background: #162033; color: #e5e7eb; }
QTabBar::tab:selected {
  background: #111827;
  border: 1px solid #1f2937;
  color: #e5e7eb;
  font-weight: 600;
}

/* ===== Menus / Tooltips ===== */
QMenu {
  background: #111827;
  border: 1px solid #1f2937;
  border-radius: 12px;
  padding: 8px;
}
QMenu::item { padding: 8px 10px; border-radius: 10px; }
QMenu::item:selected { background: #162033; }

QToolTip {
  background: #111827;
  color: #e5e7eb;
  border: 1px solid #1f2937;
  border-radius: 10px;
  padding: 6px 8px;
}

/* ===== Scrollbars ===== */
QScrollBar:vertical {
  background: transparent;
  width: 12px;
  margin: 6px 2px 6px 2px;
}
QScrollBar::handle:vertical {
  background: #1f2937;
  border-radius: 6px;
  min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: #9ca3af; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
  background: transparent;
  height: 12px;
  margin: 2px 6px 2px 6px;
}
QScrollBar::handle:horizontal {
  background: #1f2937;
  border-radius: 6px;
  min-width: 28px;
}
QScrollBar::handle:horizontal:hover { background: #9ca3af; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ===== Splitter / Canvas ===== */
QSplitter::handle { background: #1f2937; }
QSplitter::handle:hover { background: #9ca3af; }

QGraphicsView {
  background: #0f172a;
  border: 1px solid #1f2937;
  border-radius: 12px;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(SHADCN_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


    print("Hello World")


if __name__ == "__main__":
    main()