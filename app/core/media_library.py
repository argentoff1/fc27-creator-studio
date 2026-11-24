
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from app.ui.video_player import VideoPlayerDialog
from app.ui.media_table import (
    populate_media_table,
    filter_media_table
)
from app.core.media_scanner import MediaScanWorker
from app.core.media_cache import save_metadata_cache
from app.core.media_settings import save_media_folders


class MediaLibraryController:
    def __init__(self, window):
        self.window = window

    def add_folder(self):
        window = self.window

        folder = QFileDialog.getExistingDirectory(
            window,
            "Выберите папку с видео",
            str(Path.home())
        )

        if not folder:
            return

        folder = str(Path(folder).resolve())

        if folder not in window.media_folders:
            window.media_folders.append(folder)

            save_media_folders(
                window.settings,
                window.media_folders
            )

        self.refresh()

    def refresh(self):
        window = self.window

        if (
            hasattr(window, "scan_worker")
            and window.scan_worker.isRunning()
        ):
            return

        window.media_status.setText(
            "Сканирование медиатеки..."
        )

        window.scan_worker = MediaScanWorker(
            window.media_folders,
            window.metadata_cache
        )

        window.scan_worker.scan_completed.connect(
            self.on_scan_completed
        )

        window.scan_worker.progress_changed.connect(
            self.on_progress
        )

        window.media_progress.setValue(0)
        window.media_progress.setFormat(
            "Подготовка к сканированию..."
        )
        window.media_progress.setVisible(True)

        window.scan_worker.start()

    def on_progress(self, position, total):
        window = self.window

        if total == 0:
            window.media_progress.setValue(0)
            window.media_progress.setFormat(
                "Видео не найдены"
            )
            return

        percent = int(position / total * 100)

        window.media_progress.setValue(percent)
        window.media_progress.setFormat(
            f"{position} из {total} файлов ({percent}%)"
        )

    def on_scan_completed(self, results, updated_cache):
        window = self.window

        window.media_progress.setVisible(False)
        window.metadata_cache = updated_cache

        populate_media_table(
            window.media_table,
            results
        )

        count = len(results)
        folder_count = len(window.media_folders)

        window.media_status.setText(
            f"Видео: {count} | Подключено папок: {folder_count}"
        )

        save_metadata_cache(
            window.metadata_cache_path,
            window.metadata_cache
        )

        filter_media_table(
            window.media_table,
            window.media_search.text()
        )

    def open_video_preview(self, row, column):
        window = self.window

        video_item = window.media_table.item(row, 0)

        if video_item is None:
            return

        file_path = video_item.data(
            Qt.ItemDataRole.UserRole
        )

        if not file_path:
            window.show_message(
                "Ошибка",
                "Не удалось получить путь к видео."
            )
            return

        if not Path(file_path).is_file():
            window.show_message(
                "Ошибка",
                "Файл не найден:\n" + file_path
            )
            return

        player_dialog = VideoPlayerDialog(
            file_path,
            window
        )
        player_dialog.exec()

    def update_selection_action(self):
        window = self.window

        selected_rows = (
            window.media_table
            .selectionModel()
            .selectedRows()
        )

        window.send_to_editor_button.setEnabled(
            len(selected_rows) > 0
        )

    def send_selected_to_editor(self):
        window = self.window

        selected_rows = (
            window.media_table
            .selectionModel()
            .selectedRows()
        )

        if not selected_rows:
            return

        row = selected_rows[0].row()
        video_item = window.media_table.item(row, 0)

        if video_item is None:
            return

        file_path = video_item.data(
            Qt.ItemDataRole.UserRole
        )

        if not file_path or not Path(file_path).is_file():
            window.show_message(
                "Ошибка",
                "Не удалось найти выбранный видеофайл."
            )
            return

        window.editor_source_path = file_path
        window.switch_page(2)
        window.editor_playback_controller.load_video(
            file_path
        )
