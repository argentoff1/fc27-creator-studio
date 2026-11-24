
from app.core.time_format import format_media_time


class EditorTrimController:
    def __init__(self, window):
        self.window = window

    def _frame_controller(self):
        return self.window.editor_frame_controller

    def _set_button_styles(self, start_selected=False, end_selected=False):
        window = self.window

        window.editor_set_start_button.setObjectName(
            "TrimButtonSelectedStart" if start_selected else "TrimButton"
        )
        window.editor_set_end_button.setObjectName(
            "TrimButtonSelectedEnd" if end_selected else "TrimButton"
        )

        for button in (
            window.editor_set_start_button,
            window.editor_set_end_button,
        ):
            button.style().unpolish(button)
            button.style().polish(button)

    def set_start(self):
        window = self.window
        frame_controller = self._frame_controller()

        if frame_controller.frame_rate is None or frame_controller.frame_count <= 0:
            window.show_message(
                "Внимание",
                "Сначала дождись загрузки видео и покадровой навигации."
            )
            return

        current_frame = frame_controller.current_frame
        end_frame = window.editor_trim_end_frame

        if current_frame >= end_frame:
            window.show_message(
                "Неверная позиция",
                "Начало фрагмента должно находиться раньше конца."
            )
            return

        window.editor_trim_start_frame = current_frame
        window.editor_trim_start_ms = frame_controller.frame_timestamp_ms(
            current_frame
        )

        self.update_labels()
        self._set_button_styles(start_selected=True)

    def set_end(self):
        window = self.window
        frame_controller = self._frame_controller()

        if frame_controller.frame_rate is None or frame_controller.frame_count <= 0:
            window.show_message(
                "Внимание",
                "Сначала дождись загрузки видео и покадровой навигации."
            )
            return

        # Конец задаётся как граница ПОСЛЕ выбранного кадра.
        end_frame = frame_controller.current_frame + 1
        start_frame = window.editor_trim_start_frame

        if end_frame <= start_frame:
            window.show_message(
                "Неверная позиция",
                "Конец фрагмента должен находиться позже начала."
            )
            return

        window.editor_trim_end_frame = end_frame
        window.editor_trim_end_ms = frame_controller.frame_timestamp_ms(
            end_frame
        )

        self.update_labels()
        self._set_button_styles(end_selected=True)

    def set_start_frame(self, frame_number):
        window = self.window
        frame_controller = self._frame_controller()

        if frame_controller.frame_rate is None:
            return

        frame_number = max(
            0,
            min(
                window.editor_trim_end_frame - 1,
                int(frame_number)
            )
        )

        window.editor_trim_start_frame = frame_number
        window.editor_trim_start_ms = (
            frame_controller.frame_timestamp_ms(frame_number)
        )

        self.update_labels()
        self._set_button_styles(start_selected=True)

    def set_end_frame(self, frame_number):
        window = self.window
        frame_controller = self._frame_controller()

        if frame_controller.frame_rate is None:
            return

        frame_number = max(
            window.editor_trim_start_frame + 1,
            min(
                frame_controller.frame_count,
                int(frame_number)
            )
        )

        window.editor_trim_end_frame = frame_number
        window.editor_trim_end_ms = (
            frame_controller.frame_timestamp_ms(frame_number)
        )

        self.update_labels()
        self._set_button_styles(end_selected=True)

    def reset(self):
        window = self.window
        frame_controller = self._frame_controller()

        window.editor_trim_start_frame = 0
        window.editor_trim_start_ms = 0

        if frame_controller.frame_rate is not None:
            window.editor_trim_end_frame = frame_controller.frame_count
            window.editor_trim_end_ms = frame_controller.frame_timestamp_ms(
                frame_controller.frame_count
            )
        else:
            window.editor_trim_end_frame = 0
            window.editor_trim_end_ms = window.editor_player.duration()

        self._set_button_styles()
        self.update_labels()

    def update_labels(self):
        window = self.window
        frame_controller = self._frame_controller()
        frame_rate = frame_controller.frame_rate

        if frame_rate is not None:
            start_frame = window.editor_trim_start_frame
            end_frame = window.editor_trim_end_frame

            start_text = frame_controller.frame_timestamp_text(start_frame)
            end_text = frame_controller.frame_timestamp_text(end_frame)
            duration = (end_frame - start_frame) / float(frame_rate)
            duration_text = self._format_precise_seconds(duration)
        else:
            start_text = format_media_time(window.editor_trim_start_ms // 1000)
            end_text = format_media_time(window.editor_trim_end_ms // 1000)
            duration_ms = max(
                0,
                window.editor_trim_end_ms - window.editor_trim_start_ms
            )
            duration_text = format_media_time(duration_ms // 1000)

        window.editor_trim_start_label.setText(f"Начало: {start_text}")
        window.editor_trim_end_label.setText(f"Конец: {end_text}")
        window.editor_trim_duration_label.setText(
            f"Длительность: {duration_text}"
        )

        if hasattr(window, "editor_frame_controller"):
            window.editor_frame_controller.update_timeline()

    @staticmethod
    def _format_precise_seconds(total_seconds):
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:09.6f}"
