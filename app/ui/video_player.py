
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
)


class VideoPlayerDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)

        self.setWindowTitle(Path(file_path).name)
        self.resize(1000, 650)
        self.setMinimumSize(700, 450)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)

        self.player.setAudioOutput(self.audio_output)

        # Область видео
        self.video_widget = QVideoWidget()

        self.player.setVideoOutput(self.video_widget)

        # Кнопка воспроизведения
        self.play_button = QPushButton("▶ Воспроизвести")
        self.play_button.clicked.connect(self.toggle_playback)

        # Шкала перемотки
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)

        self.position_slider.sliderMoved.connect(
            self.player.setPosition
        )

        # Отображение времени
        self.time_label = QLabel("00:00 / 00:00")

        # Громкость
        volume_label = QLabel("Громкость")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)

        self.audio_output.setVolume(0.7)

        self.volume_slider.valueChanged.connect(
            lambda value: self.audio_output.setVolume(value / 100)
        )

        # Нижняя панель управления
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.position_slider, 1)
        controls_layout.addWidget(self.time_label)
        controls_layout.addWidget(volume_label)
        controls_layout.addWidget(self.volume_slider)

        # Основной интерфейс окна
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.video_widget, 1)
        main_layout.addLayout(controls_layout)

        # Сигналы плеера
        self.player.positionChanged.connect(
            self.update_position
        )

        self.player.durationChanged.connect(
            self.update_duration
        )

        self.player.playbackStateChanged.connect(
            self.update_play_button
        )

        self.position_slider.sliderPressed.connect(
            self.pause_slider_updates
        )

        self.position_slider.sliderReleased.connect(
            self.resume_slider_updates
        )

        # Открываем видео
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def update_play_button(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("⏸ Пауза")
        else:
            self.play_button.setText("▶ Воспроизвести")

    def update_position(self, position):
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)

        self.update_time_label()

    def update_duration(self, duration):
        self.position_slider.setRange(0, duration)
        self.update_time_label()

    def update_time_label(self):
        position = self.player.position() // 1000
        duration = self.player.duration() // 1000

        current_time = self.format_time(position)
        total_time = self.format_time(duration)

        self.time_label.setText(
            f"{current_time} / {total_time}"
        )

    def format_time(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return f"{minutes:02d}:{seconds:02d}"

    def pause_slider_updates(self):
        pass

    def resume_slider_updates(self):
        self.player.setPosition(self.position_slider.value())

    def closeEvent(self, event):
        self.player.stop()
        event.accept()
