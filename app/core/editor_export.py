from fractions import Fraction
from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QFileDialog

from app.core.media_probe import FFMPEG_PATH
from app.core.media_export import build_clip_export_command


class EditorExportController:
    def __init__(self, window):
        self.window = window
        self.process = None
        self.output_path = None

    def export_clip(self):
        window = self.window
        frame_controller = window.editor_frame_controller

        source_path = getattr(window, "editor_source_path", None)
        if not source_path or not Path(source_path).is_file():
            window.show_message("Ошибка", "Сначала выбери исходное видео.")
            return

        frame_rate = frame_controller.frame_rate
        if frame_rate is None:
            window.show_message(
                "Ошибка",
                "Не удалось определить частоту кадров исходного видео."
            )
            return

        start_frame = window.editor_trim_start_frame
        end_frame = window.editor_trim_end_frame

        if start_frame < 0 or end_frame <= start_frame:
            window.show_message(
                "Ошибка",
                "Конец фрагмента должен быть позже начала."
            )
            return

        if end_frame > frame_controller.frame_count:
            window.show_message(
                "Ошибка",
                "Границы фрагмента выходят за пределы исходного видео."
            )
            return

        duration_seconds = float(
            Fraction(end_frame - start_frame, 1) / frame_rate
        )
        if duration_seconds < 1:
            window.show_message(
                "Ошибка",
                "Выбранный фрагмент слишком короткий. Минимальная длительность — 1 секунда."
            )
            return

        output_folder = (
            Path(__file__).resolve().parents[2]
            / "output"
            / "clips"
        )
        output_folder.mkdir(parents=True, exist_ok=True)

        source_file = Path(source_path)
        default_path = output_folder / f"{source_file.stem}_clip.mp4"

        output_path, _ = QFileDialog.getSaveFileName(
            window,
            "Сохранить видеофрагмент",
            str(default_path),
            "Видео MP4 (*.mp4)"
        )
        if not output_path:
            return

        output_path = Path(output_path)
        if output_path.suffix.lower() != ".mp4":
            output_path = output_path.with_suffix(".mp4")

        if output_path.resolve() == source_file.resolve():
            window.show_message(
                "Ошибка",
                "Нельзя сохранить фрагмент поверх оригинала."
            )
            return

        if output_path.exists():
            window.show_message(
                "Ошибка",
                "Файл с таким именем уже существует. Выбери другое имя."
            )
            return

        command = build_clip_export_command(
            source_file,
            start_frame,
            end_frame,
            frame_rate,
            output_path,
            has_audio=frame_controller.has_audio,
        )

        window.editor_export_button.setEnabled(False)
        window.editor_export_button.setText("Создание фрагмента...")

        self.output_path = output_path
        self.process = QProcess(window)
        self.process.finished.connect(self.on_export_finished)
        self.process.errorOccurred.connect(self.on_export_error)
        self.process.start(str(FFMPEG_PATH), command)

    def on_export_finished(self, exit_code, exit_status):
        window = self.window
        process = self.process

        window.editor_export_button.setEnabled(True)
        window.editor_export_button.setText("Создать видеофрагмент")

        if process is None:
            return

        error_text = bytes(
            process.readAllStandardError()
        ).decode("utf-8", errors="replace")
        process.deleteLater()
        self.process = None

        output_path = self.output_path
        self.output_path = None

        if exit_code == 0 and output_path is not None and output_path.is_file():
            window.add_exported_clip(str(output_path))
            window.show_message(
                "Экспорт завершён",
                "Видеофрагмент успешно создан и добавлен в библиотеку.\n\n"
                "Оригинальный файл не изменялся."
            )
        else:
            window.show_message(
                "Ошибка экспорта",
                "FFmpeg не смог создать фрагмент.\n\n" + error_text[-2500:]
            )

    def on_export_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            window = self.window
            window.editor_export_button.setEnabled(True)
            window.editor_export_button.setText("Создать видеофрагмент")
            if self.process is not None:
                self.process.deleteLater()
                self.process = None
            window.show_message(
                "Ошибка",
                "Не удалось запустить FFmpeg.\nПроверь наличие файла:\n"
                + str(FFMPEG_PATH)
            )
