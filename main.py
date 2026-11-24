import sys

from PySide6.QtWidgets import QApplication

from app.ui.styles import STYLESHEET
from app.ui.main_window import CreatorStudio

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    window = CreatorStudio()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
