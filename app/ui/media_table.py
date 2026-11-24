
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.ui.sortable_table import SortableTableWidgetItem


def populate_media_table(table, results):
    table.setSortingEnabled(False)
    table.setRowCount(0)

    for item in results:
        row = table.rowCount()
        table.insertRow(row)

        values = [
            item["name"],
            item["format"],
            item["duration"],
            item["resolution"],
            item["fps"],
            item["video_codec"],
            item["audio_codec"],
            item["size"],
            item["folder"]
        ]

        for column, value in enumerate(values):
            cell = SortableTableWidgetItem(str(value))

            sort_value = str(value).casefold()

            if column == 2:
                hours, minutes, seconds = map(
                    int, item["duration"].split(":")
                )
                sort_value = hours * 3600 + minutes * 60 + seconds

            elif column == 4:
                try:
                    sort_value = float(item["fps"])
                except ValueError:
                    sort_value = -1

            elif column == 7:
                sort_value = item["size_bytes"]

            cell.setData(
                Qt.ItemDataRole.UserRole + 1,
                sort_value
            )

            table.setItem(row, column, cell)

            if column == 0:
                cell.setData(
                    Qt.ItemDataRole.UserRole,
                    item["path"]
                )

                thumbnail_path = item.get("thumbnail")

                if thumbnail_path and Path(thumbnail_path).is_file():
                    cell.setIcon(QIcon(thumbnail_path))

    table.setSortingEnabled(True)

def filter_media_table(table, search_text):
    search_text = search_text.strip().casefold()

    for row in range(table.rowCount()):
        row_matches = False

        for column in range(table.columnCount()):
            item = table.item(row, column)

            if item and search_text in item.text().casefold():
                row_matches = True
                break

        table.setRowHidden(
            row,
            not row_matches
        )