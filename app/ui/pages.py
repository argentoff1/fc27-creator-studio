from PySide6.QtWidgets import QStackedWidget

from app.ui.home_page import create_home_page
from app.ui.media_page import create_media_page
from app.ui.editor_page import create_editor_page
from app.ui.ai_assistant_page import create_ai_assistant_page
from app.ui.placeholder_page import create_placeholder_page


def create_pages(window):
    pages = QStackedWidget()

    pages.addWidget(create_home_page(window))
    pages.addWidget(create_media_page(window))
    pages.addWidget(create_editor_page(window))
    pages.addWidget(create_ai_assistant_page(window))

    pages.addWidget(create_placeholder_page(
        "Статистика",
        "Здесь будет храниться история матчей и игровой прогресс."
    ))

    return pages
