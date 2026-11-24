from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
)


def format_timestamp(seconds):
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    remainder = total % 60
    return f"{hours:02d}:{minutes:02d}:{remainder:02d}"


def create_ai_assistant_page(window):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(35, 30, 35, 30)
    layout.setSpacing(14)

    title = QLabel("Поиск интересных моментов")
    title.setObjectName("PageTitle")

    description = QLabel(
        "Поиск моментов по трём сигналам: изменения счёта на табло, "
        "всплески громкости и смены сцен. Изменение счёта считается "
        "кандидатом на гол; аудио и видеоряд помогают найти другие "
        "интересные эпизоды."
    )
    description.setObjectName("Subtitle")
    description.setWordWrap(True)

    layout.addWidget(title)
    layout.addWidget(description)

    source_layout = QHBoxLayout()
    window.analysis_source_input = QLineEdit()
    window.analysis_source_input.setPlaceholderText(
        "Выбери запись матча в формате MP4, MKV, WEBM или MOV..."
    )
    window.analysis_source_input.setReadOnly(True)

    browse_button = QPushButton("Выбрать видео")
    browse_button.clicked.connect(window.browse_analysis_video)

    source_layout.addWidget(window.analysis_source_input, 1)
    source_layout.addWidget(browse_button)
    layout.addLayout(source_layout)

    options_layout = QHBoxLayout()
    options_layout.addWidget(QLabel("Чувствительность поиска:"))

    window.analysis_sensitivity_combo = QComboBox()
    window.analysis_sensitivity_combo.addItem("Низкая — меньше кандидатов", 0.35)
    window.analysis_sensitivity_combo.addItem("Средняя", 0.25)
    window.analysis_sensitivity_combo.addItem("Высокая — больше кандидатов", 0.18)
    window.analysis_sensitivity_combo.setCurrentIndex(1)

    window.analysis_start_button = QPushButton("Найти моменты")
    window.analysis_start_button.setObjectName("ActionButton")
    window.analysis_start_button.setEnabled(False)
    window.analysis_start_button.clicked.connect(
        window.start_moment_analysis
    )

    options_layout.addWidget(window.analysis_sensitivity_combo, 1)
    options_layout.addWidget(window.analysis_start_button)
    layout.addLayout(options_layout)

    window.analysis_progress = QProgressBar()
    window.analysis_progress.setRange(0, 1)
    window.analysis_progress.setValue(0)
    window.analysis_progress.setFormat("Ожидание анализа")
    window.analysis_progress.setVisible(False)
    layout.addWidget(window.analysis_progress)

    window.analysis_status_label = QLabel(
        "Выбери запись матча, чтобы начать анализ."
    )
    window.analysis_status_label.setObjectName("Subtitle")
    window.analysis_status_label.setWordWrap(True)
    layout.addWidget(window.analysis_status_label)

    results_title = QLabel("Найденные кандидаты")
    results_title.setObjectName("CardTitle")
    layout.addWidget(results_title)

    window.analysis_results_table = QTableWidget()
    window.analysis_results_table.setColumnCount(3)
    window.analysis_results_table.setHorizontalHeaderLabels([
        "Время",
        "Причина обнаружения",
        "Предлагаемый фрагмент",
    ])
    window.analysis_results_table.setEditTriggers(
        QTableWidget.EditTrigger.NoEditTriggers
    )
    window.analysis_results_table.setSelectionBehavior(
        QTableWidget.SelectionBehavior.SelectRows
    )
    window.analysis_results_table.setSelectionMode(
        QTableWidget.SelectionMode.SingleSelection
    )
    window.analysis_results_table.verticalHeader().setVisible(False)
    window.analysis_results_table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.ResizeMode.ResizeToContents
    )
    window.analysis_results_table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.ResizeMode.Stretch
    )
    window.analysis_results_table.horizontalHeader().setSectionResizeMode(
        2, QHeaderView.ResizeMode.Stretch
    )
    window.analysis_results_table.cellDoubleClicked.connect(
        window.open_analysis_candidate
    )
    layout.addWidget(window.analysis_results_table, 1)

    footer = QLabel(
        "Дважды щёлкни по кандидату, чтобы открыть запись в монтажной "
        "и перейти к этому моменту. Анализ выполняется локально через FFmpeg."
    )
    footer.setObjectName("Subtitle")
    footer.setWordWrap(True)
    layout.addWidget(footer)

    return page
