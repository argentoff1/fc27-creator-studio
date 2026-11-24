
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer

from app.core.time_format import format_media_time


class EditorPlaybackController:
    def __init__(self, window):
        self.window = window
        self.player = window.editor_player
        self.trim_controller = window.editor_trim_controller

        self.trim_preview_end_ms = None

        self.player.positionChanged.connect(
            self.update_position
        )

        self.player.durationChanged.connect(
            self.update_duration
        )

        self.player.playbackStateChanged.connect(
            self.update_play_button
        )

    def load_video(self, file_path):
        window = self.window

        self.cancel_trim_preview()
        self.player.stop()
        self.player.setSource(
            QUrl.fromLocalFile(file_path)
        )

        window.editor_video_name.setText(
            Path(file_path).name
        )

        window.editor_video_path.setText(file_path)

        window.editor_position_slider.setRange(0, 0)
        window.editor_trim_start_ms = 0
        window.editor_trim_end_ms = 0
        window.editor_trim_start_frame = 0
        window.editor_trim_end_frame = 0

        window.editor_set_start_button.setObjectName(
            "TrimButton"
        )
        window.editor_set_end_button.setObjectName(
            "TrimButton"
        )

        window.editor_set_start_button.style().unpolish(
            window.editor_set_start_button
        )
        window.editor_set_start_button.style().polish(
            window.editor_set_start_button
        )

        window.editor_set_end_button.style().unpolish(
            window.editor_set_end_button
        )
        window.editor_set_end_button.style().polish(
            window.editor_set_end_button
        )

        self.trim_controller.update_labels()

        window.editor_time_label.setText(
            "00:00 / 00:00"
        )

        window.editor_play_button.setText(
            "▶ Воспроизвести"
        )

        window.editor_trim_preview_button.setEnabled(False)

        window.editor_frame_controller.load_video(
            file_path
        )

    def toggle_playback(self):
        if (
            self.player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.cancel_trim_preview()
            self.player.pause()
        else:
            self.cancel_trim_preview()
            self.window.editor_frame_controller.hide_preview()
            self.player.play()

    def preview_trim(self):
        frame_controller = self.window.editor_frame_controller

        if (
            frame_controller.frame_rate is None
            or frame_controller.frame_count <= 0
            or frame_controller.source_path is None
        ):
            self.window.show_message(
                "Видео не готово",
                "Сначала дождись загрузки видео и покадровой навигации."
            )
            return

        start_frame = self.window.editor_trim_start_frame
        end_frame = self.window.editor_trim_end_frame

        if start_frame < 0 or end_frame <= start_frame:
            self.window.show_message(
                "Неверные границы",
                "Установи корректные начало и конец фрагмента."
            )
            return

        start_ms = frame_controller.frame_timestamp_ms(start_frame)
        end_ms = frame_controller.frame_timestamp_ms(end_frame)

        if end_ms <= start_ms:
            self.window.show_message(
                "Слишком короткий фрагмент",
                "Выбранный фрагмент слишком короткий для предпросмотра."
            )
            return

        self.player.pause()
        self.window.editor_frame_controller.hide_preview()

        self.trim_preview_end_ms = end_ms
        self.player.setPosition(start_ms)
        self.player.play()

    def cancel_trim_preview(self):
        self.trim_preview_end_ms = None

    def seek_to_frame(self, frame_number):
        frame_controller = self.window.editor_frame_controller

        if (
            frame_controller.frame_rate is None
            or frame_controller.frame_count <= 0
        ):
            return

        self.cancel_trim_preview()
        self.player.pause()

        frame_controller.show_frame(
            int(frame_number)
        )

    def update_play_button(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.window.editor_play_button.setText(
                "⏸ Пауза"
            )
        else:
            self.window.editor_play_button.setText(
                "▶ Воспроизвести"
            )

    def update_position(self, position):
        slider = self.window.editor_position_slider

        if not slider.isSliderDown():
            slider.setValue(position)

        self.window.editor_frame_controller.sync_from_position(
            position
        )

        self.update_time_label()

        if (
            self.trim_preview_end_ms is not None
            and position >= self.trim_preview_end_ms
        ):
            self.cancel_trim_preview()
            self.player.pause()

    def update_duration(self, duration):
        self.window.editor_position_slider.setRange(
            0,
            duration
        )

        self.window.editor_trim_end_ms = duration

        self.update_time_label()
        self.trim_controller.update_labels()

        frame_controller = self.window.editor_frame_controller
        self.window.editor_trim_preview_button.setEnabled(
            frame_controller.frame_rate is not None
            and frame_controller.frame_count > 0
        )

    def seek_video(self):
        self.cancel_trim_preview()
        self.window.editor_frame_controller.hide_preview()

        self.player.setPosition(
            self.window.editor_position_slider.value()
        )

    def update_time_label(self):
        position = self.player.position() // 1000
        duration = self.player.duration() // 1000

        self.window.editor_time_label.setText(
            f"{format_media_time(position)} / "
            f"{format_media_time(duration)}"
        )
