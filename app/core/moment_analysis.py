import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.media_probe import FFMPEG_PATH, probe_video


SCENE_TIME_PATTERN = re.compile(r"pts_time:([0-9]+(?:\\.[0-9]+)?)")


class MomentAnalysisWorker(QThread):
    """Ищет резкие смены сцен в видео с помощью FFmpeg."""

    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, video_path, sensitivity=0.25, parent=None):
        super().__init__(parent)
        self.video_path = str(Path(video_path))
        self.sensitivity = float(sensitivity)

    def run(self):
        path = Path(self.video_path)

        if not path.is_file():
            self.failed.emit("Исходный видеофайл не найден.")
            return

        if not FFMPEG_PATH.is_file():
            self.failed.emit(
                "Не найден FFmpeg. Проверь папку tools/ffmpeg/bin."
            )
            return

        metadata = probe_video(path)
        if not metadata:
            self.failed.emit("Не удалось прочитать параметры видео.")
            return

        duration_ms = int(metadata.get("duration_ms", 0))
        duration_seconds = duration_ms / 1000

        command = [
            str(FFMPEG_PATH),
            "-hide_banner",
            "-nostats",
            "-i", str(path),
            "-vf", f"select='gt(scene,{self.sensitivity:.2f})',showinfo",
            "-an",
            "-f", "null",
            "NUL" if __import__("os").name == "nt" else "/dev/null",
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError as error:
            self.failed.emit(f"Не удалось запустить FFmpeg: {error}")
            return

        if result.returncode != 0:
            details = (result.stderr or "").strip()[-1200:]
            self.failed.emit(
                "FFmpeg завершил анализ с ошибкой."
                + (f"\n\n{details}" if details else "")
            )
            return

        timestamps = []
        for match in SCENE_TIME_PATTERN.finditer(result.stderr or ""):
            timestamp = float(match.group(1))
            if timestamp < 0 or timestamp >= duration_seconds:
                continue
            if not timestamps or timestamp - timestamps[-1] >= 2.0:
                timestamps.append(timestamp)

        candidates = []
        for timestamp in timestamps:
            candidates.append({
                "timestamp": timestamp,
                "duration": duration_seconds,
                "kind": "Резкая смена сцены",
                "start": max(0.0, timestamp - 6.0),
                "end": min(duration_seconds, timestamp + 8.0),
            })

        self.completed.emit(candidates)
