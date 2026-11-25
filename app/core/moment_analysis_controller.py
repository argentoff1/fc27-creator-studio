from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QTableWidgetItem

from app.core.moment_analysis import MomentAnalysisWorker
from app.ui.ai_assistant_page import format_timestamp


class MomentAnalysisController:
    def __init__(self, window):
        self.window = window
        self.source_path = None
        self.candidates = []
        self.worker = None
        self.diagnostic_folder = ""
        self.window.analysis_open_diagnostics_button.setEnabled(False)
        self.window.analysis_open_diagnostics_button.clicked.connect(
            self.open_diagnostics_folder
        )

    def set_source(self, file_path):
        self.source_path = str(Path(file_path).resolve())
        self.window.analysis_source_input.setText(self.source_path)
        self.window.analysis_results_table.setRowCount(0)
        self.candidates = []
        self.diagnostic_folder = ""
        self.window.analysis_open_diagnostics_button.setEnabled(False)
        self.window.analysis_status_label.setText(
            "Видео выбрано. Будут проверены табло, видеоряд и аудиодорожка."
        )
        self.window.analysis_start_button.setEnabled(True)

    def start_analysis(self):
        if not self.source_path or not Path(self.source_path).is_file():
            self.window.show_message(
                "Видео не выбрано",
                "Сначала выбери существующий видеофайл."
            )
            return

        if self.worker is not None and self.worker.isRunning():
            return

        sensitivity = self.window.analysis_sensitivity_combo.currentData()
        self.worker = MomentAnalysisWorker(
            self.source_path,
            sensitivity,
            self.window,
        )
        self.worker.completed.connect(self.on_analysis_completed)
        self.worker.failed.connect(self.on_analysis_failed)

        self.window.analysis_results_table.setRowCount(0)
        self.candidates = []
        self.window.analysis_start_button.setEnabled(False)
        self.window.analysis_progress.setRange(0, 0)
        self.window.analysis_progress.setFormat("Распознавание табло и анализ видео/звука...")
        self.window.analysis_progress.setVisible(True)
        self.window.analysis_status_label.setText(
            "Распознаём счёт на табло, анализируем видеоряд и аудиодорожку. "
            "На длинной записи это может занять время."
        )
        self.worker.start()

    def on_analysis_completed(self, candidates, diagnostic_folder=""):
        self.candidates = candidates
        self.diagnostic_folder = diagnostic_folder
        self.window.analysis_open_diagnostics_button.setEnabled(
            bool(diagnostic_folder and Path(diagnostic_folder).is_dir())
        )
        table = self.window.analysis_results_table
        table.setRowCount(0)

        for candidate in candidates:
            row = table.rowCount()
            table.insertRow(row)

            values = [
                format_timestamp(candidate["timestamp"]),
                candidate["kind"],
                (
                    f"{format_timestamp(candidate['start'])} — "
                    f"{format_timestamp(candidate['end'])}"
                ),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row)
                table.setItem(row, column, item)

        self.finish_worker_ui()

        if candidates:
            scoreboard_count = sum(
                "scoreboard" in candidate.get("sources", [])
                for candidate in candidates
            )
            audio_count = sum(
                "audio" in candidate.get("sources", [])
                for candidate in candidates
            )
            scene_count = sum(
                "scene" in candidate.get("sources", [])
                for candidate in candidates
            )
            self.window.analysis_status_label.setText(
                f"Готово. Найдено кандидатов: {len(candidates)} "
                f"(изменений счёта: {scoreboard_count}, "
                f"аудиосигналов: {audio_count}, смен сцен: {scene_count}). "
                "Дважды щёлкни по строке, чтобы открыть момент в монтаже."
                + (
                    f" Кадры смен сцен сохранены: {diagnostic_folder}"
                    if diagnostic_folder else
                    " Диагностические кадры смен сцен не сохранены."
                )
            )
        else:
            self.window.analysis_status_label.setText(
                "Изменений счёта, выраженных аудиовсплесков и заметных смен сцен "
                "не найдено. "
                "Попробуй повысить чувствительность."
            )

    def open_diagnostics_folder(self):
        if self.diagnostic_folder and Path(self.diagnostic_folder).is_dir():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(self.diagnostic_folder)
            )

    def on_analysis_failed(self, message):
        self.finish_worker_ui()
        self.window.analysis_status_label.setText("Анализ не завершён.")
        self.window.show_message("Ошибка анализа", message)

    def finish_worker_ui(self):
        self.window.analysis_progress.setVisible(False)
        self.window.analysis_start_button.setEnabled(
            bool(self.source_path and Path(self.source_path).is_file())
        )

    def open_candidate(self, row):
        if row < 0 or row >= len(self.candidates):
            return

        candidate = self.candidates[row]
        file_path = self.source_path
        if not file_path or not Path(file_path).is_file():
            return

        self.window.editor_source_path = file_path
        self.window.switch_page(2)
        self.window.editor_playback_controller.load_video(file_path)

        frame_controller = self.window.editor_frame_controller
        if frame_controller.frame_rate is None:
            self.window.show_message(
                "Покадровая навигация недоступна",
                "Видео загружено, но не удалось определить частоту кадров. "
                "Открой запись обычным способом и проверь её параметры."
            )
            return

        fps = float(frame_controller.frame_rate)
        event_frame = round(candidate["timestamp"] * fps)
        start_frame = max(0, round(candidate["start"] * fps))
        end_frame = min(
            frame_controller.frame_count,
            round(candidate["end"] * fps),
        )

        if end_frame > start_frame:
            self.window.editor_trim_controller.set_start_frame(start_frame)
            self.window.editor_trim_controller.set_end_frame(end_frame)

        frame_controller.show_frame(event_frame)
