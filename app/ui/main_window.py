from pathlib import Path

from app.ui.pages import create_pages
from app.ui.navigation import (
    create_navigation,
    switch_page as update_navigation_page
)

from app.core.controller_setup import (
    setup_editor_controllers,
    setup_page_controllers,
)
from app.core.media_storage import setup_media_storage

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QMessageBox,
    QFileDialog,
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

        # Контроллеры редактора нужны уже во время создания страницы монтажа.
        setup_editor_controllers(self)

        # Страницы создают виджеты. После этого можно подключать контроллеры,
        # которые обращаются к элементам интерфейса.
        self.pages = create_pages(self)
        setup_page_controllers(self)
        self.editor_sequence_controller.attach()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)

        self.switch_page(0)
        self.refresh_media_library()
        self.load_exported_clips()

    def open_video_preview(self, row, column):
        self.media_library_controller.open_video_preview(row, column)

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
        self.editor_clips_controller.add_clip(clip_path, save_settings)

    def browse_analysis_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбери запись матча",
            str(Path.home()),
            "Видеофайлы (*.mp4 *.mkv *.webm *.mov *.m4v);;Все файлы (*.*)",
        )
        if not file_path:
            return

        self.moment_analysis_controller.set_source(file_path)

    def start_moment_analysis(self):
        self.moment_analysis_controller.start_analysis()

    def open_analysis_candidate(self, row, column):
        self.moment_analysis_controller.open_candidate(row)

    def switch_page(self, index):
        update_navigation_page(self, index)

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)
