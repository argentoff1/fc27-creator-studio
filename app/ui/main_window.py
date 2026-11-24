
from app.ui.pages import create_pages
from app.ui.navigation import (
    create_navigation,
    switch_page as update_navigation_page
)

from app.core.controller_setup import setup_controllers
from app.core.media_storage import setup_media_storage

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QMessageBox,
)


class CreatorStudio(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("FC27 Creator Studio")
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)

        self.navigation_buttons = []

        setup_media_storage(self)

        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar, self.navigation_buttons = create_navigation(self)

        # Создаём контроллеры до страниц.
        setup_controllers(self)

        # Создаём рабочие страницы.
        self.pages = create_pages(self)

        # Добавляем блок сборки после создания редактора.
        self.editor_sequence_controller.attach()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)

        self.switch_page(0)
        self.refresh_media_library()
        self.load_exported_clips()

    def open_video_preview(self, row, column):
        self.media_library_controller.open_video_preview(
            row,
            column
        )

    def update_media_selection_action(self):
        self.media_library_controller.update_selection_action()

    def send_selected_to_editor(self):
        self.media_library_controller.send_selected_to_editor()

    def add_media_folder(self):
        self.media_library_controller.add_folder()

    def refresh_media_library(self):
        self.media_library_controller.refresh()

    def load_exported_clips(self):
        self.editor_clips_controller.load_clips()

    def add_exported_clip(self, clip_path, save_settings=True):
        self.editor_clips_controller.add_clip(
            clip_path,
            save_settings
        )

    def switch_page(self, index):
        update_navigation_page(self, index)

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)
