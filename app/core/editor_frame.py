
import hashlib
from fractions import Fraction
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

from app.core.media_probe import FFMPEG_PATH, probe_video


class FramePreviewLabel(QLabel):
    """Показывает извлечённый кадр без искажения пропорций."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.original_pixmap = None

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background-color: #000000; color: #ffffff;"
        )

    def set_frame(self, pixmap):
        self.original_pixmap = pixmap
        self.update_scaled_pixmap()

    def update_scaled_pixmap(self):
        if self.original_pixmap is None:
            return

        scaled = self.original_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_scaled_pixmap()


class EditorFrameController:
    def __init__(self, window):
        self.window = window

        self.source_path = None
        self.frame_rate = None
        self.frame_count = 0
        self.current_frame = 0
        self.has_audio = False

        self.cache_folder = (
            Path(__file__).resolve().parents[2]
            / "media"
            / "cache"
            / "editor_frames"
        )

        self.process = None
        self.pending_output = None
        self.pending_frame = None
        self.cache_prefix = None

    def attach(self):
        self.player = self.window.editor_player

        self.video_stack = (
            self.window.editor_video_stack.layout()
        )

        self.video_widget = self.window.editor_video_widget
        self.preview_label = self.window.editor_frame_preview

        self.player.playbackStateChanged.connect(
            self.on_playback_state_changed
        )

    def update_timeline(self):
        timeline = getattr(
            self.window,
            "editor_timeline",
            None
        )

        if timeline is None:
            return

        timeline.set_state(
            self.frame_count,
            self.current_frame,
            self.window.editor_trim_start_frame,
            self.window.editor_trim_end_frame
        )

    def load_video(self, file_path):
        self.source_path = Path(file_path)
        self.frame_rate = None
        self.frame_count = 0
        self.current_frame = 0
        self.has_audio = False

        self.cache_prefix = None

        self.update_timeline()

        metadata = probe_video(file_path)

        if not metadata:
            self.set_unavailable(
                "Не удалось получить параметры видео."
            )
            return

        numerator = metadata.get("frame_rate_num", 0)
        denominator = metadata.get("frame_rate_den", 1)

        if numerator <= 0 or denominator <= 0:
            self.set_unavailable(
                "Не удалось определить частоту кадров."
            )
            return

        if not metadata.get("is_cfr", False):
            self.set_unavailable(
                "Покадровая навигация пока доступна "
                "только для видео с постоянной частотой кадров."
            )
            return

        self.frame_rate = Fraction(
            numerator,
            denominator
        )

        self.frame_count = metadata.get("frame_count", 0)
        self.has_audio = metadata.get("audio_codec", "—") != "—"

        if self.frame_count <= 0:
            self.set_unavailable(
                "Не удалось определить количество кадров."
            )
            return

        file_stat = self.source_path.stat()

        cache_identity = (
            f"{self.source_path.resolve()}|"
            f"{file_stat.st_size}|"
            f"{file_stat.st_mtime_ns}"
        )

        self.cache_prefix = hashlib.sha256(
            cache_identity.encode("utf-8")
        ).hexdigest()

        self.window.editor_trim_start_frame = 0
        self.window.editor_trim_end_frame = self.frame_count
        self.window.editor_trim_start_ms = 0
        self.window.editor_trim_end_ms = self.frame_timestamp_ms(
            self.frame_count
        )

        self.window.editor_trim_controller.update_labels()

        self.window.editor_frame_back_button.setEnabled(True)
        self.window.editor_frame_forward_button.setEnabled(True)

        self.display_frame_info()
        self.update_timeline()

        self.show_frame(0)

    def set_unavailable(self, message):
        self.frame_rate = None
        self.frame_count = 0
        self.current_frame = 0

        self.window.editor_frame_back_button.setEnabled(False)
        self.window.editor_frame_forward_button.setEnabled(False)

        self.window.editor_frame_info_label.setText(message)

        self.update_timeline()

    def frame_timestamp_ms(self, frame_number):
        timestamp = (
            Fraction(frame_number, 1)
            / self.frame_rate
        )

        return round(float(timestamp) * 1000)

    def frame_timestamp_text(self, frame_number):
        timestamp = (
            Fraction(frame_number, 1)
            / self.frame_rate
        )

        total_seconds = float(timestamp)

        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:09.6f}"
        )

    def display_frame_info(self):
        if self.frame_rate is None:
            return

        fps = float(self.frame_rate)

        self.window.editor_frame_info_label.setText(
            f"Кадр: {self.current_frame + 1} / "
            f"{self.frame_count}    |    "
            f"FPS: {fps:g}    |    "
            f"Время: {self.frame_timestamp_text(self.current_frame)}"
        )

    def step_backward(self):
        self.step_frame(-1)

    def step_forward(self):
        self.step_frame(1)

    def step_frame(self, offset):
        if self.frame_rate is None or self.frame_count <= 0:
            return

        if self.player.playbackState().name == "PlayingState":
            self.player.pause()

        target_frame = max(
            0,
            min(
                self.frame_count - 1,
                self.current_frame + offset
            )
        )

        self.show_frame(target_frame)

    def show_frame(self, frame_number):
        if self.frame_rate is None:
            return

        frame_number = max(
            0,
            min(self.frame_count - 1, frame_number)
        )

        self.current_frame = frame_number
        self.display_frame_info()
        self.update_timeline()

        self.player.setPosition(
            self.frame_timestamp_ms(frame_number)
        )

        self.video_stack.setCurrentWidget(
            self.preview_label
        )

        output_path = (
            self.cache_folder
            / f"{self.cache_prefix}_{frame_number:09d}.jpg"
        )

        if output_path.is_file():
            self.display_image(output_path)
            return

        if self.process is not None:
            return

        self.extract_frame(frame_number, output_path)

    def extract_frame(self, frame_number, output_path):
        self.cache_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = (
            Fraction(frame_number, 1)
            / self.frame_rate
        )

        timestamp_text = (
            f"{float(timestamp):.9f}"
        )

        process = QProcess(self.window)

        self.process = process
        self.pending_output = output_path
        self.pending_frame = frame_number

        self.window.editor_frame_back_button.setEnabled(False)
        self.window.editor_frame_forward_button.setEnabled(False)

        process.finished.connect(
            self.on_extraction_finished
        )

        process.errorOccurred.connect(
            self.on_extraction_error
        )

        process.start(
            str(FFMPEG_PATH),
            [
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-ss", timestamp_text,
                "-i", str(self.source_path),
                "-map", "0:v:0",
                "-frames:v", "1",
                "-q:v", "2",
                str(output_path)
            ]
        )

    def on_extraction_finished(self, exit_code, exit_status):
        process = self.process
        output_path = self.pending_output

        if process is None:
            return

        error_text = bytes(
            process.readAllStandardError()
        ).decode("utf-8", errors="replace")

        process.deleteLater()

        self.process = None
        self.pending_output = None
        self.pending_frame = None

        self.window.editor_frame_back_button.setEnabled(True)
        self.window.editor_frame_forward_button.setEnabled(True)

        if (
            exit_code == 0
            and output_path is not None
            and output_path.is_file()
        ):
            self.display_image(output_path)
        else:
            self.window.editor_frame_info_label.setText(
                "Не удалось извлечь кадр. "
                + error_text[-300:]
            )

    def on_extraction_error(self, error):
        if self.process is None:
            return

        if error == QProcess.ProcessError.FailedToStart:
            self.process.deleteLater()
            self.process = None
            self.pending_output = None
            self.pending_frame = None

            self.window.editor_frame_back_button.setEnabled(True)
            self.window.editor_frame_forward_button.setEnabled(True)

            self.window.editor_frame_info_label.setText(
                "Не удалось запустить FFmpeg."
            )

    def display_image(self, image_path):
        pixmap = QPixmap(str(image_path))

        if pixmap.isNull():
            self.window.editor_frame_info_label.setText(
                "Не удалось открыть изображение кадра."
            )
            return

        self.preview_label.set_frame(pixmap)

        self.video_stack.setCurrentWidget(
            self.preview_label
        )

    def sync_from_position(self, position_ms):
        if self.frame_rate is None:
            return

        frame_number = round(
            position_ms
            * self.frame_rate.numerator
            / (1000 * self.frame_rate.denominator)
        )

        self.current_frame = max(
            0,
            min(self.frame_count - 1, frame_number)
        )

        self.display_frame_info()
        self.update_timeline()

    def hide_preview(self):
        if hasattr(self, "video_stack"):
            self.video_stack.setCurrentWidget(
                self.video_widget
            )

    def on_playback_state_changed(self, state):
        if state.name == "PlayingState":
            self.hide_preview()
