
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton
)

from app.ui.clickable_card import ClickableCard


def create_home_page(window):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(35, 30, 35, 30)
    layout.setSpacing(18)

    title = QLabel("Добро пожаловать!")
    title.setObjectName("PageTitle")

    description = QLabel(
        "Твой локальный центр создания контента EA FC 27."
    )
    description.setObjectName("Subtitle")

    layout.addWidget(title)
    layout.addWidget(description)
    layout.addSpacing(15)

    new_project = QPushButton("＋   Создать проект")
    new_project.setObjectName("ActionButton")
    new_project.clicked.connect(
        lambda: window.show_message(
            "Создание проекта",
            "Функция создания проекта будет добавлена на следующем этапе."
        )
    )

    open_project = QPushButton("📂   Открыть проект")
    open_project.setObjectName("ActionButton")
    open_project.clicked.connect(
        lambda: window.show_message(
            "Открытие проекта",
            "Функция открытия проекта будет добавлена позже."
        )
    )

    layout.addWidget(new_project)
    layout.addWidget(open_project)
    layout.addSpacing(15)

    section_title = QLabel("Рабочие разделы")
    section_title.setObjectName("PageTitle")
    section_title.setStyleSheet("font-size: 15pt;")

    layout.addWidget(section_title)

    cards = [
        ("Медиатека", "Импорт и организация видеозаписей."),
        ("Монтаж", "Нарезка, склейка и экспорт видео."),
        ("ИИ-ассистент", "Локальный ассистент  для работы с контентом."),
        ("Статистика", "Результаты матчей и игровой прогресс."),
    ]

    for index, (name, description) in enumerate(cards, start=1):
        card = ClickableCard(
            lambda page_index=index: window.switch_page(page_index)
        )
        card.setObjectName("ContentCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 14)

        card_title = QLabel(name)
        card_title.setObjectName("CardTitle")

        card_description = QLabel(description)
        card_description.setObjectName("CardDescription")

        card_layout.addWidget(card_title)
        card_layout.addWidget(card_description)

        layout.addWidget(card)

    layout.addStretch()
    return page
