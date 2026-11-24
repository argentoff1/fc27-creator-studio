
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
)


def create_navigation(window):
    navigation_buttons = []

    sidebar = QFrame()
    sidebar.setObjectName("Sidebar")
    sidebar.setFixedWidth(220)

    sidebar_layout = QVBoxLayout(sidebar)
    sidebar_layout.setContentsMargins(16, 24, 16, 20)
    sidebar_layout.setSpacing(10)

    logo = QLabel("FC27 Creator")
    logo.setObjectName("Logo")

    subtitle = QLabel("STUDIO")
    subtitle.setObjectName("Subtitle")

    sidebar_layout.addWidget(logo)
    sidebar_layout.addWidget(subtitle)
    sidebar_layout.addSpacing(25)

    menu_items = [
        ("⌂   Обзор", 0),
        ("▣   Медиатека", 1),
        ("✂   Монтаж", 2),
        ("✧   ИИ-ассистент", 3),
        ("▤   Статистика", 4),
    ]

    for title, page_index in menu_items:
        button = QPushButton(title)
        button.setCheckable(True)

        button.clicked.connect(
            lambda checked=False, index=page_index:
            window.switch_page(index)
        )

        sidebar_layout.addWidget(button)
        navigation_buttons.append(button)

    sidebar_layout.addStretch()

    version = QLabel("Локальная версия • 0.1.0")
    version.setObjectName("Subtitle")
    sidebar_layout.addWidget(version)

    return sidebar, navigation_buttons

def switch_page(window, index):
    window.pages.setCurrentIndex(index)

    for i, button in enumerate(window.navigation_buttons):
        button.setChecked(i == index)
        button.setObjectName(
            "ActiveButton" if i == index else ""
        )
        button.style().unpolish(button)
        button.style().polish(button)
