import re
import subprocess
import tempfile
from pathlib import Path

from app.core.media_probe import FFMPEG_PATH


TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

SCORE_PATTERN = re.compile(r"\d{1,2}")


def _read_score(frame_path):
    """Читает две цифры счёта из подготовленного фрагмента табло."""
    command = [
        str(TESSERACT_PATH),
        str(frame_path),
        "stdout",
        "--psm", "6",
        "-c", "tessedit_char_whitelist=0123456789",
        "-c", "classify_bln_numeric_mode=1",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    # Цифры должны распознаться как две отдельные строки:
    # первая — ARG, вторая — MOR. Игровые часы в область не попадают.
    numbers = []
    for line in (result.stdout or "").splitlines():
        matches = SCORE_PATTERN.findall(line)
        if matches:
            numbers.append(matches[0])

    if len(numbers) != 2:
        return None

    score = (int(numbers[0]), int(numbers[1]))
    if score[0] > 20 or score[1] > 20:
        return None

    return score


def find_score_changes(video_path, duration_seconds):
    """Распознаёт изменение счёта ARG:MOR по табло в левом верхнем углу."""
    if not TESSERACT_PATH.is_file():
        return [], (
            "Tesseract не найден по пути "
            f"{TESSERACT_PATH}. Проверь установку OCR."
        )

    if not FFMPEG_PATH.is_file():
        return [], "Не найден FFmpeg. Проверь папку tools/ffmpeg/bin."

    video_path = Path(video_path)
    candidates = []

    # По присланному кадру цифры счёта расположены примерно в области:
    # X: 13–16% ширины, Y: 5–11% высоты.
    # Вырезаем только две строки счёта, не захватывая игровые часы,
    # заставку гола в центре экрана и другие числа интерфейса.
    with tempfile.TemporaryDirectory(prefix="fc27_score_") as temp_dir:
        frame_pattern = str(Path(temp_dir) / "frame_%06d.png")
        filter_chain = (
            "fps=0.5,"
            "crop=trunc(iw*0.03/2)*2:"
            "trunc(ih*0.06/2)*2:"
            "trunc(iw*0.13/2)*2:"
            "trunc(ih*0.05/2)*2,"
            "scale=iw*8:ih*8:flags=neighbor,"
            "format=gray,"
            "eq=contrast=1.8:brightness=0.04"
        )
        command = [
            str(FFMPEG_PATH),
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(video_path),
            "-vf", filter_chain,
            "-an",
            "-y",
            frame_pattern,
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
            return [], f"Не удалось извлечь кадры для OCR: {error}"

        if result.returncode != 0:
            details = (result.stderr or "").strip()[-1000:]
            return [], "FFmpeg не смог подготовить фрагмент табло." + (
                f"\n{details}" if details else ""
            )

        frame_paths = sorted(Path(temp_dir).glob("frame_*.png"))
        if not frame_paths:
            return [], "Не удалось извлечь кадры для распознавания табло."

        confirmed_score = None
        pending_score = None
        pending_time = None
        pending_count = 0

        for frame_index, frame_path in enumerate(frame_paths):
            timestamp = float(frame_index * 2)
            if timestamp >= duration_seconds:
                break

            score = _read_score(frame_path)
            if score is None:
                pending_score = None
                pending_time = None
                pending_count = 0
                continue

            if score == pending_score and timestamp - pending_time <= 4.0:
                pending_count += 1
            else:
                pending_score = score
                pending_time = timestamp
                pending_count = 1

            # Два одинаковых чтения подряд подтверждают значение табло.
            if pending_count < 2:
                continue

            if confirmed_score is None:
                confirmed_score = score
            elif score != confirmed_score:
                arg_delta = score[0] - confirmed_score[0]
                opponent_delta = score[1] - confirmed_score[1]

                # Гол — увеличение счёта ровно на один у одной команды.
                if (
                    (arg_delta == 1 and opponent_delta == 0)
                    or (arg_delta == 0 and opponent_delta == 1)
                ):
                    old_text = f"{confirmed_score[0]}:{confirmed_score[1]}"
                    new_text = f"{score[0]}:{score[1]}"
                    candidates.append({
                        "timestamp": pending_time,
                        "duration": duration_seconds,
                        "kind": f"Изменение счёта ARG {old_text} → {new_text}",
                        "start": max(0.0, pending_time - 18.0),
                        "end": min(duration_seconds, pending_time + 18.0),
                        "source": "scoreboard",
                    })

                # Новое подтверждённое значение становится точкой отсчёта.
                confirmed_score = score

            pending_score = None
            pending_time = None
            pending_count = 0

    return candidates, None
