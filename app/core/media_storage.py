
from pathlib import Path

from PySide6.QtCore import QSettings

from app.core.media_cache import load_metadata_cache
from app.core.media_settings import load_media_folders


def setup_media_storage(window):
    window.settings = QSettings(
        "FC27 Creator Studio",
        "Creator Studio"
    )

    window.media_folders = load_media_folders(
        window.settings
    )

    window.cache_folder = (
        Path(__file__).resolve().parents[2]
        / "media"
        / "cache"
    )

    window.cache_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    window.metadata_cache_path = (
        window.cache_folder / "video_metadata.json"
    )

    window.metadata_cache = load_metadata_cache(
        window.metadata_cache_path
    )
