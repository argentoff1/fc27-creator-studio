
import json
import subprocess

from pathlib import Path
from fractions import Fraction

from app.core.time_format import format_media_time


# Корень проекта FC27_BLOG
PROJECT_ROOT = Path(__file__).resolve().parents[2]


# Пути к FFmpeg и FFprobe
FFPROBE_PATH = (
    PROJECT_ROOT
    / "tools"
    / "ffmpeg"
    / "bin"
    / "ffprobe.exe"
)

FFMPEG_PATH = (
    PROJECT_ROOT
    / "tools"
    / "ffmpeg"
    / "bin"
    / "ffmpeg.exe"
)


# Папка для миниатюр
THUMBNAIL_FOLDER = (
    PROJECT_ROOT
    / "media"
    / "cache"
    / "thumbnails"
)


def probe_video(file_path):
    command = [
        str(FFPROBE_PATH),
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-of", "json",
        str(file_path)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        video_stream = next(
            (
                stream for stream in data.get("streams", [])
                if stream.get("codec_type") == "video"
            ),
            None
        )

        audio_stream = next(
            (
                stream for stream in data.get("streams", [])
                if stream.get("codec_type") == "audio"
            ),
            None
        )

        if not video_stream:
            return None

        duration = float(
            data.get("format", {}).get("duration", 0)
        )

        duration_ms = round(duration * 1000)

        total_seconds = int(duration)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        duration_text = (
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )

        avg_frame_rate_text = video_stream.get(
            "avg_frame_rate",
            "0/1"
        )

        r_frame_rate_text = video_stream.get(
            "r_frame_rate",
            "0/1"
        )

        time_base_text = video_stream.get(
            "time_base",
            "0/1"
        )

        try:
            avg_frame_rate = Fraction(avg_frame_rate_text)
            r_frame_rate = Fraction(r_frame_rate_text)
            time_base = Fraction(time_base_text)

            fps = float(avg_frame_rate)

            fps_text = (
                f"{fps:.2f}".rstrip("0").rstrip(".")
            )

            frame_rate_num = avg_frame_rate.numerator
            frame_rate_den = avg_frame_rate.denominator

        except (ValueError, ZeroDivisionError):
            avg_frame_rate = Fraction(0, 1)
            r_frame_rate = Fraction(0, 1)
            time_base = Fraction(0, 1)

            fps = 0
            fps_text = "Неизвестно"

            frame_rate_num = 0
            frame_rate_den = 1

        raw_frame_count = video_stream.get("nb_frames")

        try:
            frame_count = int(raw_frame_count)
        except (TypeError, ValueError):
            frame_count = 0

        if frame_count <= 0 and fps > 0 and duration > 0:
            frame_count = round(duration * fps)

        # Это предварительная проверка CFR, а не полное
        # исследование временных меток каждого кадра.
        rates_match = (
            avg_frame_rate > 0
            and avg_frame_rate == r_frame_rate
        )

        duration_matches_frame_count = (
            frame_count > 0
            and fps > 0
            and abs(duration * fps - frame_count) <= 1.5
        )

        is_cfr = (
            rates_match
            and duration_matches_frame_count
        )

        return {
            "duration": duration_text,
            "duration_ms": duration_ms,
            "resolution": (
                f"{video_stream.get('width', 0)}"
                f"×{video_stream.get('height', 0)}"
            ),
            "fps": fps_text,
            "frame_rate_num": frame_rate_num,
            "frame_rate_den": frame_rate_den,
            "avg_frame_rate": str(avg_frame_rate),
            "r_frame_rate": str(r_frame_rate),
            "time_base": str(time_base),
            "frame_count": frame_count,
            "is_cfr": is_cfr,
            "video_codec": video_stream.get(
                "codec_name", "Неизвестно"
            ).upper(),
            "audio_codec": (
                audio_stream.get("codec_name", "—").upper()
                if audio_stream else "—"
            )
        }

    except (
        subprocess.TimeoutExpired,
        subprocess.SubprocessError,
        OSError,
        json.JSONDecodeError,
        ValueError
    ) as error:
        print(f"Ошибка анализа видео {file_path}: {error}")
        return None


def generate_thumbnail(file_path, thumbnail_path):
    file_path = Path(file_path)
    thumbnail_path = Path(thumbnail_path)

    thumbnail_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    command = [
        str(FFMPEG_PATH),
        "-y",
        "-ss", "5",
        "-i", str(file_path),
        "-frames:v", "1",
        "-vf", "scale=320:-2",
        "-q:v", "3",
        str(thumbnail_path)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )

        if result.returncode != 0:
            print(
                f"Ошибка создания миниатюры: {result.stderr}"
            )
            return False

        return thumbnail_path.is_file()

    except (
        subprocess.TimeoutExpired,
        subprocess.SubprocessError,
        OSError
    ) as error:
        print(
            f"Ошибка генерации миниатюры {file_path}: {error}"
        )
        return False
