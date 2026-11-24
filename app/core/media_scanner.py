
import hashlib

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.media_probe import (
    THUMBNAIL_FOLDER,
    probe_video,
    generate_thumbnail
)


class MediaScanWorker(QThread):
    scan_completed = Signal(list, dict)
    progress_changed = Signal(int, int)

    def __init__(self, media_folders, metadata_cache):
        super().__init__()

        self.media_folders = media_folders
        self.metadata_cache = metadata_cache.copy()

    def run(self):
        supported_formats = {
            ".mp4", ".webm", ".mkv", ".mov", ".m4v"
        }

        found_files = set()
        files_to_process = []
        results = []

        # Фаза 1. Собираем список всех подходящих видео.

        for folder in self.media_folders:
            folder_path = Path(folder)

            if not folder_path.is_dir():
                continue

            try:
                for file_path in folder_path.rglob("*"):
                    try:
                        if not file_path.is_file():
                            continue

                        if file_path.suffix.lower() not in supported_formats:
                            continue

                        normalized_path = str(
                            file_path.resolve()
                        ).casefold()

                        if normalized_path in found_files:
                            continue

                        found_files.add(normalized_path)

                        file_stat = file_path.stat()

                        files_to_process.append((
                            file_path,
                            normalized_path,
                            file_stat
                        ))

                    except (PermissionError, OSError) as error:
                        print(
                            f"Не удалось обработать файл {file_path}: {error}"
                        )

            except (PermissionError, OSError) as error:
                print(
                    f"Не удалось прочитать папку {folder}: {error}"
                )

        # Фаза 2. Обрабатываем видео и передаём прогресс.

        total = len(files_to_process)
        self.progress_changed.emit(0, total)

        for position, item in enumerate(files_to_process, start=1):
            file_path, cache_key, file_stat = item

            cached = self.metadata_cache.get(cache_key)

            source_unchanged = (
                cached
                and cached.get("size") == file_stat.st_size
                and cached.get("modified") == file_stat.st_mtime_ns
            )

            if source_unchanged:
                metadata = cached.get("metadata")
            else:
                metadata = probe_video(file_path)

                if metadata is not None:
                    self.metadata_cache[cache_key] = {
                        "size": file_stat.st_size,
                        "modified": file_stat.st_mtime_ns,
                        "metadata": metadata
                    }

            thumbnail_name = (
                hashlib.sha256(
                    cache_key.encode("utf-8")
                ).hexdigest() + ".jpg"
            )

            thumbnail_path = THUMBNAIL_FOLDER / thumbnail_name

            if (
                not source_unchanged
                or not thumbnail_path.is_file()
            ):
                thumbnail_created = generate_thumbnail(
                    file_path,
                    thumbnail_path
                )
            else:
                thumbnail_created = True

            thumbnail = (
                str(thumbnail_path)
                if thumbnail_created
                else ""
            )

            results.append({
                "name": file_path.name,
                "path": str(file_path.resolve()),
                "thumbnail": thumbnail,
                "format": file_path.suffix[1:].upper(),
                "duration": metadata["duration"],
                "resolution": metadata["resolution"],
                "fps": metadata["fps"],
                "video_codec": metadata["video_codec"],
                "audio_codec": metadata["audio_codec"],
                "size": f"{file_stat.st_size / (1024 * 1024):.1f} МБ",
                "size_bytes": file_stat.st_size,
                "folder": str(file_path.parent)
            })

            self.progress_changed.emit(position, total)

        self.scan_completed.emit(results, self.metadata_cache)
