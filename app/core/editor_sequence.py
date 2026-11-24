import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QProcess
from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QAbstractItemView,
    QComboBox,
    QSlider,
    QInputDialog,
    QMessageBox,
)

from app.core.media_probe import FFMPEG_PATH, probe_video


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_FILE = PROJECT_ROOT / "projects" / "editor_projects.json"


class EditorSequenceController:
    """Управляет монтажными проектами и последовательностью их фрагментов."""

    def __init__(self, window):
        self.window = window

        self.sequence_list = None
        self.export_button = None
        self.project_combo = None

        self.process = None
        self.output_path = None
        self.attached = False

        self.projects = []
        self.current_project_id = None
        self._loading_project = False

    def attach(self):
        if self.attached:
            return

        clips_list = getattr(self.window, "editor_clips_list", None)
        if clips_list is None:
            return

        clips_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        page = clips_list.parentWidget()
        layout = page.layout()
        if layout is None:
            return

        group = QGroupBox("Монтажные проекты")
        group_layout = QVBoxLayout(group)

        description = QLabel(
            "Создавай отдельные проекты для разных роликов. "
            "У каждого проекта свой список фрагментов и порядок монтажа. "
            "Изменения сохраняются автоматически."
        )
        description.setWordWrap(True)

        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("Текущий проект:"))

        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(180)
        self.project_combo.currentIndexChanged.connect(
            self.on_project_changed
        )
        project_layout.addWidget(self.project_combo, 1)

        project_buttons_layout = QHBoxLayout()
        self.new_project_button = QPushButton("＋ Создать")
        self.new_project_button.clicked.connect(self.create_project)
        self.rename_project_button = QPushButton("Переименовать")
        self.rename_project_button.clicked.connect(self.rename_project)
        self.delete_project_button = QPushButton("Удалить")
        self.delete_project_button.clicked.connect(self.delete_project)

        project_buttons_layout.addWidget(self.new_project_button)
        project_buttons_layout.addWidget(self.rename_project_button)
        project_buttons_layout.addWidget(self.delete_project_button)
        project_buttons_layout.addStretch()

        self.sequence_list = QListWidget()
        self.sequence_list.setMinimumHeight(150)
        self.sequence_list.setMaximumHeight(240)
        self.sequence_list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.sequence_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.sequence_list.itemSelectionChanged.connect(self.update_buttons)
        self.sequence_list.model().rowsMoved.connect(
            self.on_sequence_rows_moved
        )

        buttons_layout = QHBoxLayout()

        add_button = QPushButton("Добавить выбранные фрагменты")
        add_button.clicked.connect(self.add_selected_clips)

        self.remove_button = QPushButton("Удалить выбранный")
        self.remove_button.clicked.connect(self.remove_selected)

        self.up_button = QPushButton("↑ Выше")
        self.up_button.clicked.connect(self.move_up)

        self.down_button = QPushButton("↓ Ниже")
        self.down_button.clicked.connect(self.move_down)

        clear_button = QPushButton("Очистить список")
        clear_button.clicked.connect(self.clear_sequence)

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(self.remove_button)
        buttons_layout.addWidget(self.up_button)
        buttons_layout.addWidget(self.down_button)
        buttons_layout.addStretch()

        sequence_extra_layout = QHBoxLayout()
        sequence_extra_layout.addWidget(clear_button)
        sequence_extra_layout.addStretch()

        # Настройки итогового видео.
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Формат:"))

        self.profile_combo = QComboBox()
        self.profile_combo.addItem("YouTube — горизонтальный 16:9", "youtube")
        self.profile_combo.addItem("Shorts / TikTok — вертикальный 9:16", "vertical")
        settings_layout.addWidget(self.profile_combo, 2)

        settings_layout.addWidget(QLabel("Разрешение:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("1080p", "1080p")
        self.resolution_combo.addItem("720p", "720p")
        settings_layout.addWidget(self.resolution_combo)

        settings_layout.addWidget(QLabel("FPS:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItem("30", "30")
        self.fps_combo.addItem("60", "60")
        settings_layout.addWidget(self.fps_combo)

        settings_layout.addWidget(QLabel("Качество:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Высокое", "18")
        self.quality_combo.addItem("Сбалансированное", "20")
        self.quality_combo.addItem("Компактное", "23")
        settings_layout.addWidget(self.quality_combo, 1)

        framing_layout = QHBoxLayout()
        framing_layout.addWidget(QLabel("Кадрирование:"))
        self.framing_combo = QComboBox()
        self.framing_combo.addItem("Заполнить кадр (обрезка)", "crop")
        self.framing_combo.addItem("Вписать целиком (поля)", "pad")
        framing_layout.addWidget(self.framing_combo, 1)

        self.output_format_label = QLabel("Выходной размер: 1920 × 1080")
        self.output_format_label.setObjectName("Subtitle")
        framing_layout.addWidget(self.output_format_label, 1)

        crop_position_layout = QVBoxLayout()
        crop_x_layout = QHBoxLayout()
        crop_x_layout.addWidget(QLabel("Положение по горизонтали:"))
        self.crop_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_x_slider.setRange(0, 100)
        self.crop_x_slider.setSingleStep(1)
        self.crop_x_slider.setPageStep(10)
        self.crop_x_value_label = QLabel("50%")
        self.crop_x_value_label.setMinimumWidth(42)
        crop_x_layout.addWidget(self.crop_x_slider, 1)
        crop_x_layout.addWidget(self.crop_x_value_label)
        crop_position_layout.addLayout(crop_x_layout)

        crop_y_layout = QHBoxLayout()
        crop_y_layout.addWidget(QLabel("Положение по вертикали:"))
        self.crop_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_y_slider.setRange(0, 100)
        self.crop_y_slider.setSingleStep(1)
        self.crop_y_slider.setPageStep(10)
        self.crop_y_value_label = QLabel("50%")
        self.crop_y_value_label.setMinimumWidth(42)
        crop_y_layout.addWidget(self.crop_y_slider, 1)
        crop_y_layout.addWidget(self.crop_y_value_label)
        crop_position_layout.addLayout(crop_y_layout)

        crop_reset_layout = QHBoxLayout()
        self.crop_reset_button = QPushButton("По центру")
        self.crop_reset_button.clicked.connect(self.reset_crop_position)
        self.crop_position_hint = QLabel(
            "50% — центр; 0% и 100% — крайние положения области кадрирования."
        )
        self.crop_position_hint.setObjectName("Subtitle")
        crop_reset_layout.addWidget(self.crop_reset_button)
        crop_reset_layout.addWidget(self.crop_position_hint, 1)
        crop_position_layout.addLayout(crop_reset_layout)

        self._loading_export_settings = True
        self.load_export_settings()
        self._loading_export_settings = False
        for combo in (
            self.profile_combo,
            self.resolution_combo,
            self.fps_combo,
            self.quality_combo,
            self.framing_combo,
        ):
            combo.currentIndexChanged.connect(self.on_export_setting_changed)

        self.crop_x_slider.valueChanged.connect(self.on_crop_position_changed)
        self.crop_y_slider.valueChanged.connect(self.on_crop_position_changed)
        self.update_crop_controls_enabled()

        export_layout = QHBoxLayout()
        self.sequence_info = QLabel("Фрагментов в сборке: 0")
        self.export_button = QPushButton("Экспортировать итоговый ролик")
        self.export_button.setObjectName("ActionButton")
        self.export_button.clicked.connect(self.export_sequence)
        export_layout.addWidget(self.sequence_info, 1)
        export_layout.addWidget(self.export_button)

        group_layout.addWidget(description)
        group_layout.addLayout(project_layout)
        group_layout.addLayout(project_buttons_layout)
        group_layout.addWidget(self.sequence_list)
        group_layout.addLayout(buttons_layout)
        group_layout.addLayout(sequence_extra_layout)
        group_layout.addLayout(settings_layout)
        group_layout.addLayout(framing_layout)
        group_layout.addLayout(crop_position_layout)
        group_layout.addLayout(export_layout)
        layout.addWidget(group)

        self.attached = True
        self.load_projects()
        self.update_buttons()

    # ------------------------------------------------------------------
    # Хранение проектов
    # ------------------------------------------------------------------

    def load_projects(self):
        PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)

        if PROJECTS_FILE.is_file():
            try:
                data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
                raw_projects = data.get("projects", [])
                for entry in raw_projects:
                    if not isinstance(entry, dict):
                        continue
                    project_id = str(entry.get("id", "")).strip()
                    name = str(entry.get("name", "")).strip()
                    paths = entry.get("clips", [])
                    if not project_id or not name or not isinstance(paths, list):
                        continue
                    self.projects.append({
                        "id": project_id,
                        "name": name,
                        "clips": self._normalize_paths(paths),
                    })
            except (OSError, json.JSONDecodeError, AttributeError, TypeError) as error:
                backup_path = PROJECTS_FILE.with_name(
                    "editor_projects_backup_"
                    + datetime.now().strftime("%Y%m%d_%H%M%S")
                    + ".json"
                )
                try:
                    shutil.copy2(PROJECTS_FILE, backup_path)
                except OSError:
                    backup_path = None

                details = (
                    f"\n\nРезервная копия: {backup_path}"
                    if backup_path else
                    "\n\nНе удалось создать резервную копию исходного файла."
                )
                self.window.show_message(
                    "Не удалось прочитать монтажные проекты",
                    "Файл проектов повреждён или недоступен. "
                    "Будет создан новый файл проектов; исходный файл "
                    "сохранён отдельно, если удалось создать копию.\n\n"
                    f"{error}{details}\n\nФайл: {PROJECTS_FILE}"
                )

        if not self.projects:
            # Переносим последовательность из предыдущей версии приложения.
            legacy_paths = self.window.settings.value(
                "editor/sequence_paths", []
            )
            if isinstance(legacy_paths, str):
                legacy_paths = [legacy_paths]
            if not isinstance(legacy_paths, (list, tuple)):
                legacy_paths = []

            self.projects = [{
                "id": uuid.uuid4().hex,
                "name": "Мой проект",
                "clips": self._normalize_paths(legacy_paths),
            }]
            self.save_projects()

        saved_id = str(
            self.window.settings.value("editor/current_project_id", "")
        )
        if not any(p["id"] == saved_id for p in self.projects):
            saved_id = self.projects[0]["id"]

        self._loading_project = True
        self.project_combo.clear()
        for project in self.projects:
            self.project_combo.addItem(project["name"], project["id"])
        index = self.project_combo.findData(saved_id)
        self.project_combo.setCurrentIndex(max(index, 0))
        self.current_project_id = saved_id
        self._loading_project = False

        self.load_current_sequence()

    @staticmethod
    def _normalize_paths(paths):
        normalized = []
        seen = set()
        for value in paths:
            if not value:
                continue
            try:
                path = str(Path(str(value)).expanduser().resolve())
            except (OSError, RuntimeError):
                continue
            if path not in seen:
                normalized.append(path)
                seen.add(path)
        return normalized

    def save_projects(self):
        PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "projects": self.projects,
        }
        temporary_file = PROJECTS_FILE.with_suffix(".json.tmp")
        temporary_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_file.replace(PROJECTS_FILE)

    def get_current_project(self):
        return next(
            (p for p in self.projects if p["id"] == self.current_project_id),
            None,
        )

    def load_current_sequence(self):
        project = self.get_current_project()
        if project is None or self.sequence_list is None:
            return

        self.sequence_list.clear()
        for clip_path in project["clips"]:
            path = Path(clip_path)
            exists = path.is_file()
            title = path.name if exists else f"{path.name} (файл не найден)"
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, clip_path)
            item.setToolTip(clip_path)
            if not exists:
                item.setForeground(Qt.GlobalColor.darkRed)
            self.sequence_list.addItem(item)

        self.window.settings.setValue(
            "editor/current_project_id", self.current_project_id
        )
        self.update_buttons()

    def save_sequence(self):
        if self.sequence_list is None:
            return

        project = self.get_current_project()
        if project is None:
            return

        paths = [
            self.sequence_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.sequence_list.count())
        ]
        project["clips"] = self._normalize_paths(paths)
        self.window.settings.setValue("editor/sequence_paths", project["clips"])
        self.window.settings.setValue(
            "editor/current_project_id", self.current_project_id
        )
        self.save_projects()

    # ------------------------------------------------------------------
    # Управление монтажными проектами
    # ------------------------------------------------------------------

    def on_project_changed(self, index):
        if self._loading_project or index < 0:
            return

        new_id = self.project_combo.itemData(index)
        if not new_id or new_id == self.current_project_id:
            return

        self.save_sequence()
        self.current_project_id = new_id
        self.window.settings.setValue("editor/current_project_id", new_id)
        self.load_current_sequence()

    def create_project(self):
        name, accepted = QInputDialog.getText(
            self.window, "Новый монтажный проект", "Название проекта:"
        )
        name = name.strip()
        if not accepted:
            return
        if not name:
            self.window.show_message("Пустое название", "Введи название проекта.")
            return
        if any(p["name"].casefold() == name.casefold() for p in self.projects):
            self.window.show_message(
                "Проект уже существует", "Проект с таким названием уже есть."
            )
            return

        self.save_sequence()
        project = {"id": uuid.uuid4().hex, "name": name, "clips": []}
        self.projects.append(project)
        self.save_projects()

        self._loading_project = True
        self.project_combo.addItem(project["name"], project["id"])
        self.project_combo.setCurrentIndex(self.project_combo.count() - 1)
        self._loading_project = False
        self.current_project_id = project["id"]
        self.load_current_sequence()
        self.update_project_buttons()

    def rename_project(self):
        project = self.get_current_project()
        if project is None:
            return

        name, accepted = QInputDialog.getText(
            self.window,
            "Переименовать проект",
            "Новое название:",
            text=project["name"],
        )
        name = name.strip()
        if not accepted:
            return
        if not name:
            self.window.show_message("Пустое название", "Введи название проекта.")
            return
        if any(
            p["id"] != project["id"] and p["name"].casefold() == name.casefold()
            for p in self.projects
        ):
            self.window.show_message(
                "Проект уже существует", "Проект с таким названием уже есть."
            )
            return

        project["name"] = name
        index = self.project_combo.currentIndex()
        self.project_combo.setItemText(index, name)
        self.save_projects()

    def delete_project(self):
        project = self.get_current_project()
        if project is None:
            return
        if len(self.projects) <= 1:
            self.window.show_message(
                "Нельзя удалить проект",
                "В приложении должен оставаться хотя бы один монтажный проект.",
            )
            return

        answer = QMessageBox.question(
            self.window,
            "Удалить монтажный проект",
            f'Удалить проект «{project["name"]}»?\n\n'
            "Исходные видеофрагменты не будут удалены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        old_index = self.project_combo.currentIndex()
        self.projects = [p for p in self.projects if p["id"] != project["id"]]
        self.save_projects()

        self._loading_project = True
        self.project_combo.removeItem(old_index)
        new_index = min(old_index, self.project_combo.count() - 1)
        self.project_combo.setCurrentIndex(new_index)
        self._loading_project = False
        self.current_project_id = self.project_combo.itemData(new_index)
        self.window.settings.setValue(
            "editor/current_project_id", self.current_project_id
        )
        self.load_current_sequence()
        self.update_project_buttons()

    def update_project_buttons(self):
        has_project = self.get_current_project() is not None
        self.rename_project_button.setEnabled(has_project)
        self.delete_project_button.setEnabled(
            has_project and len(self.projects) > 1
        )

    # ------------------------------------------------------------------
    # Работа с фрагментами последовательности
    # ------------------------------------------------------------------

    def on_sequence_rows_moved(self, *args):
        self.save_sequence()
        self.update_buttons()

    def add_selected_clips(self):
        source_list = getattr(self.window, "editor_clips_list", None)
        if source_list is None:
            return

        selected_items = sorted(source_list.selectedItems(), key=source_list.row)
        if not selected_items:
            self.window.show_message(
                "Фрагменты не выбраны",
                "Сначала выбери один или несколько фрагментов в библиотеке.",
            )
            return

        existing_paths = {
            self.sequence_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.sequence_list.count())
        }
        added = 0

        for source_item in selected_items:
            clip_path = source_item.data(Qt.ItemDataRole.UserRole)
            if not clip_path:
                continue
            clip_path = str(Path(clip_path).resolve())
            if not Path(clip_path).is_file() or clip_path in existing_paths:
                continue

            item = QListWidgetItem(Path(clip_path).name)
            item.setData(Qt.ItemDataRole.UserRole, clip_path)
            item.setToolTip(clip_path)
            self.sequence_list.addItem(item)
            existing_paths.add(clip_path)
            added += 1

        self.save_sequence()
        self.update_buttons()
        if added == 0:
            self.window.show_message(
                "Ничего не добавлено",
                "Выбранные фрагменты уже находятся в списке или недоступны.",
            )

    def remove_selected(self):
        row = self.sequence_list.currentRow()
        if row < 0:
            return
        self.sequence_list.takeItem(row)
        self.save_sequence()
        self.update_buttons()

    def move_up(self):
        row = self.sequence_list.currentRow()
        if row <= 0:
            return
        item = self.sequence_list.takeItem(row)
        self.sequence_list.insertItem(row - 1, item)
        self.sequence_list.setCurrentRow(row - 1)
        self.save_sequence()
        self.update_buttons()

    def move_down(self):
        row = self.sequence_list.currentRow()
        if row < 0 or row >= self.sequence_list.count() - 1:
            return
        item = self.sequence_list.takeItem(row)
        self.sequence_list.insertItem(row + 1, item)
        self.sequence_list.setCurrentRow(row + 1)
        self.save_sequence()
        self.update_buttons()

    def clear_sequence(self):
        self.sequence_list.clear()
        self.save_sequence()
        self.update_buttons()

    def update_buttons(self):
        if self.sequence_list is None:
            return
        count = self.sequence_list.count()
        row = self.sequence_list.currentRow()
        self.sequence_info.setText(f"Фрагментов в сборке: {count}")
        self.remove_button.setEnabled(row >= 0)
        self.up_button.setEnabled(row > 0)
        self.down_button.setEnabled(row >= 0 and row < count - 1)
        self.export_button.setEnabled(count >= 2 and self.process is None)
        self.update_project_buttons()

    # ------------------------------------------------------------------
    # Настройки экспорта итогового ролика
    # ------------------------------------------------------------------

    def load_export_settings(self):
        settings = self.window.settings
        saved_profile = str(settings.value("editor/export/profile", "youtube"))
        saved_resolution = str(settings.value("editor/export/resolution", "1080p"))
        saved_fps = str(settings.value("editor/export/fps", "60"))
        saved_quality = str(settings.value("editor/export/quality", "20"))
        saved_framing = str(settings.value("editor/export/framing", "crop"))
        saved_crop_x = self._safe_crop_value(
            settings.value("editor/export/crop_x", 50)
        )
        saved_crop_y = self._safe_crop_value(
            settings.value("editor/export/crop_y", 50)
        )

        for combo, value in (
            (self.profile_combo, saved_profile),
            (self.resolution_combo, saved_resolution),
            (self.fps_combo, saved_fps),
            (self.quality_combo, saved_quality),
            (self.framing_combo, saved_framing),
        ):
            index = combo.findData(value)
            combo.setCurrentIndex(index if index >= 0 else 0)

        self.crop_x_slider.setValue(saved_crop_x)
        self.crop_y_slider.setValue(saved_crop_y)
        self.update_output_format_label()
        self.update_crop_position_labels()
        self.update_crop_controls_enabled()

    @staticmethod
    def _safe_crop_value(value):
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return 50

    def on_export_setting_changed(self, *args):
        if self._loading_export_settings:
            return
        self.save_export_settings()
        self.update_output_format_label()
        self.update_crop_controls_enabled()

    def on_crop_position_changed(self, *args):
        if self._loading_export_settings:
            return
        self.update_crop_position_labels()
        self.save_export_settings()

    def update_crop_position_labels(self):
        self.crop_x_value_label.setText(f"{self.crop_x_slider.value()}%")
        self.crop_y_value_label.setText(f"{self.crop_y_slider.value()}%")

    def update_crop_controls_enabled(self):
        crop_enabled = (
            self.framing_combo.currentData() == "crop"
            and self.framing_combo.isEnabled()
        )
        for widget in (
            self.crop_x_slider,
            self.crop_y_slider,
            self.crop_reset_button,
        ):
            widget.setEnabled(crop_enabled and self.process is None)
        self.crop_position_hint.setText(
            "50% — центр; 0% и 100% — крайние положения области кадрирования."
            if crop_enabled else
            "При режиме «Вписать целиком» положение кадра не используется."
        )

    def reset_crop_position(self):
        self.crop_x_slider.setValue(50)
        self.crop_y_slider.setValue(50)

    def save_export_settings(self):
        settings = self.window.settings
        settings.setValue("editor/export/profile", self.profile_combo.currentData())
        settings.setValue("editor/export/resolution", self.resolution_combo.currentData())
        settings.setValue("editor/export/fps", self.fps_combo.currentData())
        settings.setValue("editor/export/quality", self.quality_combo.currentData())
        settings.setValue("editor/export/framing", self.framing_combo.currentData())
        settings.setValue("editor/export/crop_x", self.crop_x_slider.value())
        settings.setValue("editor/export/crop_y", self.crop_y_slider.value())

    def get_export_settings(self):
        profile = self.profile_combo.currentData()
        resolution = self.resolution_combo.currentData()
        if profile == "vertical":
            dimensions = {
                "1080p": (1080, 1920),
                "720p": (720, 1280),
            }
        else:
            dimensions = {
                "1080p": (1920, 1080),
                "720p": (1280, 720),
            }

        width, height = dimensions.get(resolution, dimensions["1080p"])
        return {
            "width": width,
            "height": height,
            "fps": int(self.fps_combo.currentData()),
            "crf": int(self.quality_combo.currentData()),
            "framing": self.framing_combo.currentData(),
            "crop_x": self.crop_x_slider.value(),
            "crop_y": self.crop_y_slider.value(),
        }

    def update_output_format_label(self):
        if not hasattr(self, "output_format_label"):
            return
        options = self.get_export_settings()
        self.output_format_label.setText(
            f"Выходной размер: {options['width']} × {options['height']}"
        )

    def set_export_settings_enabled(self, enabled):
        for widget in (
            self.profile_combo,
            self.resolution_combo,
            self.fps_combo,
            self.quality_combo,
            self.framing_combo,
        ):
            widget.setEnabled(enabled)

        self.update_crop_controls_enabled()

    # ------------------------------------------------------------------
    # Экспорт итогового ролика
    # ------------------------------------------------------------------

    def export_sequence(self):
        count = self.sequence_list.count()
        if count < 2:
            self.window.show_message(
                "Недостаточно фрагментов",
                "Для сборки ролика добавь минимум два видеофрагмента.",
            )
            return

        paths = []
        for index in range(count):
            path = self.sequence_list.item(index).data(Qt.ItemDataRole.UserRole)
            if not path or not Path(path).is_file():
                self.window.show_message(
                    "Файл недоступен",
                    "Один из фрагментов был перемещён или удалён. "
                    "Удали его из списка и добавь доступный файл.",
                )
                return
            paths.append(Path(path))

        output_folder = PROJECT_ROOT / "output" / "sequences"
        output_folder.mkdir(parents=True, exist_ok=True)
        default_name = "sequence_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".mp4"
        output_path, _ = QFileDialog.getSaveFileName(
            self.window,
            "Сохранить итоговый ролик",
            str(output_folder / default_name),
            "Видео MP4 (*.mp4)",
        )
        if not output_path:
            return

        output_path = Path(output_path)
        if output_path.suffix.lower() != ".mp4":
            output_path = output_path.with_suffix(".mp4")
        if output_path.exists():
            self.window.show_message(
                "Файл уже существует", "Выбери другое имя для итогового ролика."
            )
            return

        metadata_list = []
        for path in paths:
            metadata = probe_video(path)
            if metadata is None or metadata.get("duration_ms", 0) <= 0:
                self.window.show_message(
                    "Ошибка анализа видео",
                    f"Не удалось прочитать параметры файла:\n{path}",
                )
                return
            metadata_list.append(metadata)

        export_settings = self.get_export_settings()
        self.save_export_settings()
        command = self.build_command(
            paths, metadata_list, output_path, export_settings
        )
        self.output_path = output_path
        self.export_button.setEnabled(False)
        self.export_button.setText("Сборка ролика...")
        self.project_combo.setEnabled(False)
        self.set_export_settings_enabled(False)
        self.new_project_button.setEnabled(False)
        self.rename_project_button.setEnabled(False)
        self.delete_project_button.setEnabled(False)

        self.process = QProcess(self.window)
        self.process.finished.connect(self.on_export_finished)
        self.process.errorOccurred.connect(self.on_export_error)
        self.process.start(str(FFMPEG_PATH), command)

    def build_command(self, paths, metadata_list, output_path, export_settings=None):
        options = export_settings or self.get_export_settings()
        width = int(options["width"])
        height = int(options["height"])
        fps = int(options["fps"])
        crf = int(options["crf"])
        framing = options.get("framing", "crop")
        crop_x = self._safe_crop_value(options.get("crop_x", 50)) / 100
        crop_y = self._safe_crop_value(options.get("crop_y", 50)) / 100

        if framing == "pad":
            video_filter = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            )
        else:
            video_filter = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}:"
                f"(iw-ow)*{crop_x:.3f}:(ih-oh)*{crop_y:.3f}"
            )

        command = ["-hide_banner", "-y", "-loglevel", "error"]
        for path in paths:
            command.extend(["-i", str(path)])

        silence_indexes = {}
        next_input_index = len(paths)
        for index, metadata in enumerate(metadata_list):
            has_audio = metadata.get("audio_codec", "—") != "—"
            if has_audio:
                continue
            duration = metadata["duration_ms"] / 1000
            silence_indexes[index] = next_input_index
            command.extend([
                "-f", "lavfi", "-t", f"{duration:.6f}", "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
            ])
            next_input_index += 1

        filters = []
        concat_inputs = []
        for index, metadata in enumerate(metadata_list):
            video_label = f"v{index}"
            audio_label = f"a{index}"
            filters.append(
                f"[{index}:v:0]"
                f"{video_filter},"
                f"fps={fps},setsar=1,format=yuv420p,setpts=PTS-STARTPTS"
                f"[{video_label}]"
            )

            has_audio = metadata.get("audio_codec", "—") != "—"
            audio_source = (
                f"[{index}:a:0]" if has_audio
                else f"[{silence_indexes[index]}:a:0]"
            )
            duration = metadata["duration_ms"] / 1000
            filters.append(
                f"{audio_source}aresample=48000,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"atrim=duration={duration:.6f},asetpts=PTS-STARTPTS"
                f"[{audio_label}]"
            )
            concat_inputs.append(f"[{video_label}][{audio_label}]")

        filters.append(
            "".join(concat_inputs)
            + f"concat=n={len(paths)}:v=1:a=1[outv][outa]"
        )
        command.extend([
            "-filter_complex", ";".join(filters),
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(output_path),
        ])
        return command

    def _restore_export_ui(self):
        self.export_button.setText("Экспортировать итоговый ролик")
        self.project_combo.setEnabled(True)
        self.set_export_settings_enabled(True)
        self.new_project_button.setEnabled(True)
        self.update_buttons()

    def on_export_finished(self, exit_code, exit_status):
        process = self.process
        self.process = None
        output_path = self.output_path
        self._restore_export_ui()

        if (
            exit_code == 0 and output_path is not None
            and output_path.is_file() and output_path.stat().st_size > 0
        ):
            self.window.add_exported_clip(str(output_path))
            self.window.show_message(
                "Сборка завершена",
                "Итоговый ролик успешно создан.\n\n"
                f"Файл:\n{output_path}\n\n"
                "Он также добавлен в библиотеку видеофрагментов.",
            )
        else:
            error_text = bytes(process.readAllStandardError()).decode(
                "utf-8", errors="replace"
            ) if process is not None else "Неизвестная ошибка FFmpeg."
            if output_path and output_path.exists():
                try:
                    output_path.unlink()
                except OSError:
                    pass
            self.window.show_message(
                "Ошибка сборки",
                "FFmpeg не смог собрать итоговый ролик.\n\n" + error_text[-3000:],
            )

        self.output_path = None

    def on_export_error(self, error):
        if error != QProcess.ProcessError.FailedToStart:
            return
        self.process = None
        self._restore_export_ui()
        self.window.show_message(
            "Ошибка запуска FFmpeg",
            "Не удалось запустить FFmpeg.\n\nПроверь наличие файла:\n"
            + str(FFMPEG_PATH),
        )
