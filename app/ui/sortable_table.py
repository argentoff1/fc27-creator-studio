
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        self_value = self.data(Qt.ItemDataRole.UserRole + 1)
        other_value = other.data(Qt.ItemDataRole.UserRole + 1)

        if self_value is not None and other_value is not None:
            return self_value < other_value

        return self.text().casefold() < other.text().casefold()
