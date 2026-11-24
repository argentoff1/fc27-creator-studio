import array
import math
import re
import subprocess
import statistics
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.media_probe import FFMPEG_PATH, probe_video


SCENE_TIME_PATTERN = re.compile(r"pts_time:([0-9]+(?:\\.[0-9]+)?)")

AUDIO_SAMPLE_RATE = 8000
AUDIO_WINDOW_SECONDS = 0.5
AUDIO_SAMPLES_PER_WINDOW = int(AUDIO_SAMPLE_RATE * AUDIO_WINDOW_SECONDS)


class MomentAnalysisWorker(QThread):
    """Ищет смены сцен и заметные аудиовсплески в записи матча."""

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

        duration_seconds = int(metadata.get("duration_ms", 0)) / 1000
        if duration_seconds <= 0:
            self.failed.emit("Не удалось определить длительность видео.")
            return

        candidates = []
        errors = []

        scene_candidates, scene_error = self._find_scene_changes(
            path, duration_seconds
        )
        candidates.extend(scene_candidates)
        if scene_error:
            errors.append(scene_error)

        if metadata.get("audio_codec") and metadata["audio_codec"] != "—":
            audio_candidates, audio_error = self._find_audio_peaks(
                path, duration_seconds
            )
            candidates.extend(audio_candidates)
            if audio_error:
                errors.append(audio_error)

        if errors and not candidates:
            self.failed.emit("\n\n".join(errors))
            return

        candidates = self._merge_candidates(candidates)
        self.completed.emit(candidates)

    def _find_scene_changes(self, path, duration_seconds):
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
            return [], f"Не удалось запустить поиск смен сцен: {error}"

        if result.returncode != 0:
            details = (result.stderr or "").strip()[-1000:]
            return [], "Ошибка анализа видеоряда." + (
                f"\n{details}" if details else ""
            )

        timestamps = []
        for match in SCENE_TIME_PATTERN.finditer(result.stderr or ""):
            timestamp = float(match.group(1))
            if timestamp < 0 or timestamp >= duration_seconds:
                continue
            if not timestamps or timestamp - timestamps[-1] >= 2.0:
                timestamps.append(timestamp)

        return [
            {
                "timestamp": timestamp,
                "duration": duration_seconds,
                "kind": "Смена сцены",
                "start": max(0.0, timestamp - 6.0),
                "end": min(duration_seconds, timestamp + 8.0),
                "source": "scene",
            }
            for timestamp in timestamps
        ], None

    def _find_audio_peaks(self, path, duration_seconds):
        command = [
            str(FFMPEG_PATH),
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(path),
            "-vn",
            "-ac", "1",
            "-ar", str(AUDIO_SAMPLE_RATE),
            "-f", "s16le",
            "pipe:1",
        ]

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            return [], f"Не удалось запустить аудиоанализ: {error}"

        rms_values = []
        bytes_per_window = AUDIO_SAMPLES_PER_WINDOW * 2

        try:
            while True:
                chunk = process.stdout.read(bytes_per_window)
                if not chunk:
                    break

                samples = array.array("h")
                samples.frombytes(chunk[:len(chunk) - (len(chunk) % 2)])
                if not samples:
                    continue

                square_sum = sum(sample * sample for sample in samples)
                rms = math.sqrt(square_sum / len(samples))
                dbfs = 20 * math.log10(max(rms / 32768.0, 1e-8))
                rms_values.append(dbfs)

            stderr_text = process.stderr.read().decode(
                "utf-8", errors="replace"
            )
            return_code = process.wait()
        except Exception as error:
            process.kill()
            process.wait()
            return [], f"Ошибка чтения аудиодорожки: {error}"
        finally:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

        if return_code != 0:
            return [], "FFmpeg не смог прочитать аудиодорожку." + (
                f"\n{stderr_text[-1000:]}" if stderr_text else ""
            )

        if len(rms_values) < 12:
            return [], None

        # Чем выше чувствительность поиска, тем меньший перепад громкости
        # нужен для регистрации кандидата.
        delta_threshold = (
            5.0 if self.sensitivity <= 0.20
            else 6.5 if self.sensitivity <= 0.28
            else 8.0
        )

        radius = 60  # 30 секунд в каждую сторону, окна по 0,5 секунды.
        excluded_radius = 4
        raw_events = []

        for index, level in enumerate(rms_values):
            left = rms_values[max(0, index - radius):max(0, index - excluded_radius)]
            right = rms_values[
                min(len(rms_values), index + excluded_radius + 1):
                min(len(rms_values), index + radius + 1)
            ]
            baseline_values = left + right

            if len(baseline_values) < 8:
                continue

            baseline = statistics.median(baseline_values)
            increase = level - baseline

            # Отсекаем тихие фоновые колебания и оставляем выраженные пики.
            if level >= -34.0 and increase >= delta_threshold:
                raw_events.append((index * AUDIO_WINDOW_SECONDS, increase))

        # Соседние окна одного возгласа/комментаторской реакции — один эпизод.
        grouped = []
        for timestamp, increase in raw_events:
            if grouped and timestamp - grouped[-1][-1][0] <= 4.0:
                grouped[-1].append((timestamp, increase))
            else:
                grouped.append([(timestamp, increase)])

        candidates = []
        for group in grouped:
            peak_time, peak_increase = max(group, key=lambda item: item[1])
            if peak_time >= duration_seconds:
                continue

            candidates.append({
                "timestamp": peak_time,
                "duration": duration_seconds,
                "kind": f"Аудиовсплеск (+{peak_increase:.0f} дБ к фону)",
                "start": max(0.0, peak_time - 12.0),
                "end": min(duration_seconds, peak_time + 12.0),
                "source": "audio",
                "audio_increase": peak_increase,
            })

        return candidates, None

    @staticmethod
    def _merge_candidates(candidates):
        if not candidates:
            return []

        candidates.sort(key=lambda item: item["timestamp"])
        merged = []

        for candidate in candidates:
            if (
                merged
                and candidate["timestamp"] - merged[-1]["timestamp"] <= 8.0
            ):
                current = merged[-1]
                if candidate["kind"] not in current["kind"]:
                    current["kind"] += " + " + candidate["kind"]
                current["start"] = min(current["start"], candidate["start"])
                current["end"] = max(current["end"], candidate["end"])
                current["sources"] = sorted(
                    set(current.get("sources", [current.get("source")]))
                    | {candidate.get("source")}
                )
            else:
                item = dict(candidate)
                item["sources"] = [item.pop("source", "unknown")]
                merged.append(item)

        return merged
