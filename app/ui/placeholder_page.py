from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel
)


def create_placeholder_page(title_text, description_text):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(35, 30, 35, 30)

    title = QLabel(title_text)
    title.setObjectName("PageTitle")

    description = QLabel(description_text)
    description.setObjectName("Subtitle")

    layout.addWidget(title)
    layout.addWidget(description)
    layout.addStretch()

    return page