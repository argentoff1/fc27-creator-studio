
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import QWidget


class EditorTimelineWidget(QWidget):
    seekRequested = Signal(int)
    trimStartChanged = Signal(int)
    trimEndChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.frame_count = 0
        self.current_frame = 0
        self.start_frame = 0
        self.end_frame = 0

        self.drag_mode = None

        self.setMinimumHeight(76)
        self.setMaximumHeight(90)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_state(
        self,
        frame_count,
        current_frame,
        start_frame,
        end_frame
    ):
        self.frame_count = max(0, int(frame_count))

        if self.frame_count <= 0:
            self.current_frame = 0
            self.start_frame = 0
            self.end_frame = 0
        else:
            self.current_frame = max(
                0,
                min(self.frame_count - 1, int(current_frame))
            )

            self.start_frame = max(
                0,
                min(self.frame_count - 1, int(start_frame))
            )

            self.end_frame = max(
                self.start_frame + 1,
                min(self.frame_count, int(end_frame))
            )

        self.update()

    def _track_rect(self):
        return QRectF(
            14,
            31,
            max(1, self.width() - 28),
            18
        )

    def _frame_to_x(self, frame_number):
        if self.frame_count <= 0:
            return self._track_rect().left()

        track = self._track_rect()

        frame_number = max(
            0,
            min(self.frame_count, frame_number)
        )

        return (
            track.left()
            + track.width() * frame_number / self.frame_count
        )

    def _x_to_frame(self, x):
        if self.frame_count <= 0:
            return 0

        track = self._track_rect()

        ratio = (
            (x - track.left())
            / max(1.0, track.width())
        )

        ratio = max(0.0, min(1.0, ratio))

        return round(ratio * self.frame_count)

    def _start_handle_rect(self):
        x = self._frame_to_x(self.start_frame)

        return QRectF(
            x - 6,
            25,
            12,
            30
        )

    def _end_handle_rect(self):
        x = self._frame_to_x(self.end_frame)

        return QRectF(
            x - 6,
            25,
            12,
            30
        )

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        painter.fillRect(
            self.rect(),
            QColor("#20242b")
        )

        if self.frame_count <= 0:
            painter.setPen(QColor("#9299a5"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Шкала монтажа: видео не выбрано"
            )
            painter.end()
            return

        track = self._track_rect()

        start_x = self._frame_to_x(self.start_frame)
        end_x = self._frame_to_x(self.end_frame)
        current_x = self._frame_to_x(self.current_frame)

        # Вся продолжительность видео.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#444b56"))
        painter.drawRoundedRect(
            track,
            5,
            5
        )

        # Область выбранного фрагмента.
        selected_rect = QRectF(
            start_x,
            track.top(),
            max(1, end_x - start_x),
            track.height()
        )

        painter.setBrush(QColor("#3979c9"))
        painter.drawRoundedRect(
            selected_rect,
            4,
            4
        )

        # Затемнение частей за пределами выделения.
        painter.setBrush(QColor(0, 0, 0, 105))

        painter.drawRect(
            QRectF(
                track.left(),
                track.top(),
                max(0, start_x - track.left()),
                track.height()
            )
        )

        painter.drawRect(
            QRectF(
                end_x,
                track.top(),
                max(0, track.right() - end_x),
                track.height()
            )
        )

        # Маркер начала.
        painter.setBrush(QColor("#54d68b"))
        painter.setPen(
            QPen(QColor("#d5ffe5"), 1)
        )
        painter.drawRoundedRect(
            self._start_handle_rect(),
            3,
            3
        )

        # Маркер конца.
        painter.setBrush(QColor("#f0a34a"))
        painter.setPen(
            QPen(QColor("#fff0d9"), 1)
        )
        painter.drawRoundedRect(
            self._end_handle_rect(),
            3,
            3
        )

        # Текущая позиция воспроизведения.
        painter.setPen(
            QPen(QColor("#ffffff"), 2)
        )

        painter.drawLine(
            int(current_x),
            17,
            int(current_x),
            62
        )

        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.PenStyle.NoPen)

        painter.drawEllipse(
            QRectF(
                current_x - 4,
                13,
                8,
                8
            )
        )

        # Подписи.
        painter.setPen(QColor("#d5d9e0"))

        painter.drawText(
            14,
            13,
            "Начало"
        )

        painter.drawText(
            self.width() - 65,
            13,
            "Конец"
        )

        painter.end()

    def mousePressEvent(self, event):
        if (
            self.frame_count <= 0
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return

        position = event.position()

        start_rect = self._start_handle_rect()
        end_rect = self._end_handle_rect()

        start_hit = start_rect.adjusted(
            -5, -5, 5, 5
        ).contains(position)

        end_hit = end_rect.adjusted(
            -5, -5, 5, 5
        ).contains(position)

        if start_hit and end_hit:
            start_distance = abs(
                position.x() - self._frame_to_x(self.start_frame)
            )
            end_distance = abs(
                position.x() - self._frame_to_x(self.end_frame)
            )

            self.drag_mode = (
                "start"
                if start_distance <= end_distance
                else "end"
            )

        elif start_hit:
            self.drag_mode = "start"

        elif end_hit:
            self.drag_mode = "end"

        else:
            self.drag_mode = None
            frame = self._x_to_frame(position.x())

            frame = max(
                0,
                min(self.frame_count - 1, frame)
            )

            self.seekRequested.emit(frame)

        if self.drag_mode is not None:
            self._update_drag(position.x())

        event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_mode is None:
            start_hit = self._start_handle_rect().adjusted(
                -5, -5, 5, 5
            ).contains(event.position())

            end_hit = self._end_handle_rect().adjusted(
                -5, -5, 5, 5
            ).contains(event.position())

            if start_hit or end_hit:
                self.setCursor(
                    Qt.CursorShape.SizeHorCursor
                )
            else:
                self.setCursor(
                    Qt.CursorShape.PointingHandCursor
                )

            return

        self._update_drag(event.position().x())
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_mode = None
            event.accept()

    def _update_drag(self, x):
        frame = self._x_to_frame(x)

        if self.drag_mode == "start":
            frame = max(
                0,
                min(self.end_frame - 1, frame)
            )

            if frame != self.start_frame:
                self.start_frame = frame
                self.trimStartChanged.emit(frame)
                self.update()

        elif self.drag_mode == "end":
            frame = max(
                self.start_frame + 1,
                min(self.frame_count, frame)
            )

            if frame != self.end_frame:
                self.end_frame = frame
                self.trimEndChanged.emit(frame)
                self.update()
