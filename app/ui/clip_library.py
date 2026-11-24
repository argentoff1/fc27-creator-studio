
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem


def create_clip_list_item(clip_path):
    clip_path = str(Path(clip_path).resolve())

    file_size = Path(clip_path).stat().st_size
    size_mb = file_size / (1024 * 1024)

    item = QListWidgetItem(
        f"{Path(clip_path).name}  |  {size_mb:.1f} МБ"
    )

    item.setData(
        Qt.ItemDataRole.UserRole,
        clip_path
    )

    item.setToolTip(clip_path)

    return item


def normalize_clip_paths(saved_clips):
    if isinstance(saved_clips, str):
        saved_clips = [saved_clips]

    return [
        str(clip_path)
        for clip_path in saved_clips
        if Path(str(clip_path)).is_file()
    ]
