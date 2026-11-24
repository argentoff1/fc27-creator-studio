
import os
from pathlib import Path

from PySide6.QtCore import Qt

from app.ui.video_player import VideoPlayerDialog
from app.ui.clip_library import (
    create_clip_list_item,
    normalize_clip_paths
)


class EditorClipsController:
    def __init__(self, window):
        self.window = window

    def load_clips(self):
        window = self.window
        window.exported_clips = []

        saved_clips = normalize_clip_paths(
            window.settings.value(
                "editor/exported_clips",
                []
            )
        )

        for clip_path in saved_clips:
            self.add_clip(
                clip_path,
                save_settings=False
            )

        self.save_clips()

    def add_clip(self, clip_path, save_settings=True):
        window = self.window

        clip_path = str(Path(clip_path).resolve())

        if not Path(clip_path).is_file():
            return

        if clip_path in window.exported_clips:
            return

        window.exported_clips.append(clip_path)

        item = create_clip_list_item(clip_path)

        window.editor_clips_list.addItem(item)

        if save_settings:
            self.save_clips()

    def save_clips(self):
        self.window.settings.setValue(
            "editor/exported_clips",
            self.window.exported_clips
        )

    def update_selection(self):
        window = self.window

        has_selection = (
            window.editor_clips_list.currentItem() is not None
        )

        window.editor_open_clip_button.setEnabled(
            has_selection
        )

        window.editor_open_clip_folder_button.setEnabled(
            has_selection
        )

    def open_selected_clip(self):
        window = self.window
        selected_item = window.editor_clips_list.currentItem()

        if selected_item is None:
            return

        clip_path = selected_item.data(
            Qt.ItemDataRole.UserRole
        )

        if not clip_path or not Path(clip_path).is_file():
            window.show_message(
                "Ошибка",
                "Видео­фрагмент не найден."
            )
            return

        player_dialog = VideoPlayerDialog(
            clip_path,
            window
        )
        player_dialog.exec()

    def open_selected_clip_folder(self):
        window = self.window
        selected_item = window.editor_clips_list.currentItem()

        if selected_item is None:
            return

        clip_path = selected_item.data(
            Qt.ItemDataRole.UserRole
        )

        if not clip_path or not Path(clip_path).is_file():
            window.show_message(
                "Ошибка",
                "Не удалось найти видеофрагмент."
            )
            return

        try:
            os.startfile(str(Path(clip_path).parent))

        except OSError as error:
            window.show_message(
                "Ошибка",
                f"Не удалось открыть папку:\n{error}"
            )
