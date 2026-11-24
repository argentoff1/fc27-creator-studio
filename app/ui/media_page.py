
from PySide6.QtCore import Qt, QSize

from app.ui.media_table import filter_media_table

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QHeaderView,
    QProgressBar,
    QLineEdit
)


def create_media_page(window):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(35, 30, 35, 30)
    layout.setSpacing(18)

    title = QLabel("Медиатека")
    title.setObjectName("PageTitle")

    description = QLabel(
        "Управление видеозаписями и исходниками."
    )
    description.setObjectName("Subtitle")

    layout.addWidget(title)
    layout.addWidget(description)

    toolbar = QHBoxLayout()

    add_folder_button = QPushButton("＋   Добавить папку")
    add_folder_button.setObjectName("ActionButton")
    add_folder_button.clicked.connect(window.add_media_folder)

    refresh_button = QPushButton("Обновить")
    refresh_button.clicked.connect(window.refresh_media_library)

    window.send_to_editor_button = QPushButton(
        "Передать в монтаж"
    )
    window.send_to_editor_button.setObjectName(
        "SendToEditorButton"
    )
    window.send_to_editor_button.setEnabled(False)
    window.send_to_editor_button.clicked.connect(
        window.send_selected_to_editor
    )

    toolbar.addWidget(add_folder_button)
    toolbar.addWidget(refresh_button)
    toolbar.addWidget(window.send_to_editor_button)
    toolbar.addStretch()

    layout.addLayout(toolbar)

    window.media_progress = QProgressBar()
    window.media_progress.setRange(0, 100)
    window.media_progress.setValue(0)
    window.media_progress.setTextVisible(True)
    window.media_progress.setFormat("Ожидание сканирования")
    window.media_progress.setVisible(False)

    layout.addWidget(window.media_progress)

    window.media_search = QLineEdit()
    window.media_search.setPlaceholderText(
        "Поиск видео по названию, формату, кодеку или папке..."
    )

    layout.addWidget(window.media_search)

    window.media_search.textChanged.connect(
        lambda search_text: filter_media_table(
            window.media_table,
            search_text
        )
    )

    window.media_table = QTableWidget()
    window.media_table.setColumnCount(9)
    window.media_table.setHorizontalHeaderLabels([
        "Название",
        "Формат",
        "Длительность",
        "Разрешение",
        "FPS",
        "Видеокодек",
        "Аудиокодек",
        "Размер",
        "Расположение"
    ])

    window.media_table.setEditTriggers(
        QTableWidget.EditTrigger.NoEditTriggers
    )
    window.media_table.setSelectionBehavior(
        QTableWidget.SelectionBehavior.SelectRows
    )
    window.media_table.setAlternatingRowColors(True)
    window.media_table.verticalHeader().setVisible(False)

    window.media_table.setVerticalScrollBarPolicy(
        Qt.ScrollBarAlwaysOn
    )

    window.media_table.verticalHeader().setDefaultSectionSize(88)
    window.media_table.setIconSize(QSize(120, 68))
    window.media_table.horizontalHeader().setFixedHeight(38)

    header = window.media_table.horizontalHeader()

    header.setSectionResizeMode(
        0, QHeaderView.ResizeMode.Stretch
    )

    for column in range(1, 8):
        header.setSectionResizeMode(
            column, QHeaderView.ResizeMode.ResizeToContents
        )

    header.setSectionResizeMode(
        8, QHeaderView.ResizeMode.Stretch
    )

    layout.addWidget(window.media_table)

    window.media_table.cellDoubleClicked.connect(
        window.open_video_preview
    )

    window.media_table.itemSelectionChanged.connect(
        window.update_media_selection_action
    )

    window.media_status = QLabel("Видео пока не добавлены.")
    window.media_status.setObjectName("Subtitle")
    layout.addWidget(window.media_status)

    return page
