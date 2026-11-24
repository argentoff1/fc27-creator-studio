from app.core.editor_playback import EditorPlaybackController
from app.core.editor_frame import FramePreviewLabel

from app.ui.editor_timeline import EditorTimelineWidget

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedLayout,
    QLabel,
    QPushButton,
    QSlider,
    QListWidget,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget


def create_editor_page(window):
    # Вся рабочая область находится внутри прокручиваемого контейнера.
    # Это позволяет добраться до монтажных проектов даже на небольшом экране.
    page = QWidget()
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(0, 0, 0, 0)
    page_layout.setSpacing(0)

    scroll_area = QScrollArea()
    scroll_area.setObjectName("EditorScrollArea")
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll_area.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    scroll_area.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )

    content = QWidget()
    content.setObjectName("EditorContent")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(28, 22, 28, 28)
    layout.setSpacing(12)

    title = QLabel("Монтаж")
    title.setObjectName("PageTitle")

    description = QLabel(
        "Рабочее пространство для просмотра и обработки видео."
    )
    description.setObjectName("Subtitle")

    layout.addWidget(title)
    layout.addWidget(description)

    window.editor_video_name = QLabel("Исходное видео не выбрано")
    window.editor_video_name.setObjectName("CardTitle")

    window.editor_video_path = QLabel(
        "Передай видео из медиатеки, чтобы начать работу."
    )
    window.editor_video_path.setObjectName("Subtitle")
    window.editor_video_path.setWordWrap(True)

    layout.addWidget(window.editor_video_name)
    layout.addWidget(window.editor_video_path)

    # Область просмотра видео и извлечённого кадра.
    window.editor_video_widget = QVideoWidget()
    window.editor_video_widget.setMinimumHeight(300)
    window.editor_video_widget.setStyleSheet(
        "background-color: #000000;"
    )

    window.editor_frame_preview = FramePreviewLabel()
    window.editor_frame_preview.setMinimumHeight(300)

    window.editor_video_stack = QWidget()
    window.editor_video_stack.setObjectName("EditorVideoArea")
    window.editor_video_stack.setMinimumHeight(300)
    window.editor_video_stack.setMaximumHeight(400)
    window.editor_video_stack.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Fixed,
    )

    video_stack_layout = QStackedLayout(window.editor_video_stack)
    video_stack_layout.setContentsMargins(0, 0, 0, 0)
    video_stack_layout.setStackingMode(
        QStackedLayout.StackingMode.StackOne
    )

    video_stack_layout.addWidget(window.editor_video_widget)
    video_stack_layout.addWidget(window.editor_frame_preview)
    video_stack_layout.setCurrentWidget(window.editor_video_widget)

    window.editor_player = QMediaPlayer(window)
    window.editor_audio_output = QAudioOutput(window)

    window.editor_player.setAudioOutput(window.editor_audio_output)
    window.editor_audio_output.setVolume(0.7)
    window.editor_player.setVideoOutput(window.editor_video_widget)

    # Контроллер воспроизведения.
    window.editor_playback_controller = EditorPlaybackController(window)

    # Подключаем покадровый контроллер.
    window.editor_frame_controller.attach()

    layout.addWidget(window.editor_video_stack)

    # Панель управления воспроизведением.
    controls_layout = QHBoxLayout()

    window.editor_play_button = QPushButton("▶ Воспроизвести")
    window.editor_play_button.clicked.connect(
        window.editor_playback_controller.toggle_playback
    )

    window.editor_position_slider = QSlider(Qt.Orientation.Horizontal)
    window.editor_position_slider.setRange(0, 0)
    window.editor_position_slider.sliderMoved.connect(
        window.editor_player.setPosition
    )
    window.editor_position_slider.sliderReleased.connect(
        window.editor_playback_controller.seek_video
    )

    window.editor_time_label = QLabel("00:00 / 00:00")

    controls_layout.addWidget(window.editor_play_button)
    controls_layout.addWidget(window.editor_position_slider, 1)
    controls_layout.addWidget(window.editor_time_label)
    layout.addLayout(controls_layout)

    # Визуальная шкала монтажа.
    timeline_title = QLabel("Шкала монтажа")
    timeline_title.setObjectName("CardTitle")
    layout.addWidget(timeline_title)

    window.editor_timeline = EditorTimelineWidget()
    window.editor_timeline.seekRequested.connect(
        window.editor_playback_controller.seek_to_frame
    )
    window.editor_timeline.trimStartChanged.connect(
        window.editor_trim_controller.set_start_frame
    )
    window.editor_timeline.trimEndChanged.connect(
        window.editor_trim_controller.set_end_frame
    )
    layout.addWidget(window.editor_timeline)

    # Панель покадровой навигации.
    frame_controls_layout = QHBoxLayout()

    window.editor_frame_back_button = QPushButton("◀ Предыдущий кадр")
    window.editor_frame_back_button.setEnabled(False)
    window.editor_frame_back_button.clicked.connect(
        window.editor_frame_controller.step_backward
    )

    window.editor_frame_forward_button = QPushButton("Следующий кадр ▶")
    window.editor_frame_forward_button.setEnabled(False)
    window.editor_frame_forward_button.clicked.connect(
        window.editor_frame_controller.step_forward
    )

    window.editor_frame_info_label = QLabel(
        "Покадровая навигация: видео не выбрано"
    )
    window.editor_frame_info_label.setObjectName("Subtitle")

    frame_controls_layout.addWidget(window.editor_frame_back_button)
    frame_controls_layout.addWidget(window.editor_frame_forward_button)
    frame_controls_layout.addWidget(window.editor_frame_info_label, 1)
    layout.addLayout(frame_controls_layout)

    # Панель выделения фрагмента.
    window.editor_trim_start_ms = 0
    window.editor_trim_end_ms = 0

    trim_layout = QHBoxLayout()

    window.editor_set_start_button = QPushButton("Установить начало")
    window.editor_set_start_button.setObjectName("TrimButton")
    window.editor_set_start_button.clicked.connect(
        window.editor_trim_controller.set_start
    )

    window.editor_set_end_button = QPushButton("Установить конец")
    window.editor_set_end_button.setObjectName("TrimButton")
    window.editor_set_end_button.clicked.connect(
        window.editor_trim_controller.set_end
    )

    window.editor_reset_trim_button = QPushButton("Сбросить границы")
    window.editor_reset_trim_button.setObjectName("TrimButton")
    window.editor_reset_trim_button.clicked.connect(
        window.editor_trim_controller.reset
    )

    window.editor_trim_preview_button = QPushButton(
        "▶ Просмотреть выделенный фрагмент"
    )
    window.editor_trim_preview_button.setEnabled(False)
    window.editor_trim_preview_button.clicked.connect(
        window.editor_playback_controller.preview_trim
    )

    window.editor_export_button = QPushButton("Создать видеофрагмент")
    window.editor_export_button.setObjectName("ActionButton")
    window.editor_export_button.clicked.connect(
        window.editor_export_controller.export_clip
    )

    window.editor_trim_start_label = QLabel("Начало: 00:00")
    window.editor_trim_end_label = QLabel("Конец: 00:00")
    window.editor_trim_duration_label = QLabel("Длительность: 00:00")

    trim_layout.addWidget(window.editor_set_start_button)
    trim_layout.addWidget(window.editor_set_end_button)
    trim_layout.addWidget(window.editor_reset_trim_button)
    trim_layout.addWidget(window.editor_trim_preview_button)
    trim_layout.addWidget(window.editor_export_button)
    trim_layout.addStretch()
    trim_layout.addWidget(window.editor_trim_start_label)
    trim_layout.addWidget(window.editor_trim_end_label)
    trim_layout.addWidget(window.editor_trim_duration_label)
    layout.addLayout(trim_layout)

    # Библиотека созданных фрагментов.
    clips_title = QLabel("Созданные видеофрагменты")
    clips_title.setObjectName("CardTitle")
    layout.addWidget(clips_title)

    window.editor_clips_list = QListWidget()
    window.editor_clips_list.setMinimumHeight(110)
    window.editor_clips_list.setMaximumHeight(160)
    window.editor_clips_list.itemDoubleClicked.connect(
        lambda item: window.editor_clips_controller.open_selected_clip()
    )
    window.editor_clips_list.itemSelectionChanged.connect(
        window.editor_clips_controller.update_selection
    )
    layout.addWidget(window.editor_clips_list)

    clips_buttons_layout = QHBoxLayout()

    window.editor_open_clip_button = QPushButton("▶ Просмотреть фрагмент")
    window.editor_open_clip_button.setEnabled(False)
    window.editor_open_clip_button.clicked.connect(
        window.editor_clips_controller.open_selected_clip
    )

    window.editor_open_clip_folder_button = QPushButton("📂 Открыть папку")
    window.editor_open_clip_folder_button.setEnabled(False)
    window.editor_open_clip_folder_button.clicked.connect(
        window.editor_clips_controller.open_selected_clip_folder
    )

    clips_buttons_layout.addWidget(window.editor_open_clip_button)
    clips_buttons_layout.addWidget(window.editor_open_clip_folder_button)
    clips_buttons_layout.addStretch()
    layout.addLayout(clips_buttons_layout)

    # Контроллер добавляет сюда блок «Монтажные проекты».
    # Важно: список фрагментов и этот блок имеют одного родителя content.

    scroll_area.setWidget(content)
    page_layout.addWidget(scroll_area)

    # Сохраняем ссылку для диагностики/доступа из других частей интерфейса.
    window.editor_scroll_area = scroll_area
    window.editor_content_widget = content

    return page
