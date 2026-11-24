
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame


class ClickableCard(QFrame):
    def __init__(self, on_click):
        super().__init__()
        self.on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_click()

        super().mousePressEvent(event)
