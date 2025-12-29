from ui.main_window import MainWindow
import sys
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


    print("Hello World")


if __name__ == "__main__":
    main()