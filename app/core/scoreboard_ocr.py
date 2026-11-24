import re
import subprocess
import tempfile
from pathlib import Path

from app.core.media_probe import FFMPEG_PATH


TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

SCORE_PATTERN = re.compile(r"\d{1,2}")


def find_score_changes(video_path, duration_seconds):
    """Распознаёт изменение счёта по табло в левом верхнем углу."""
    if not TESSERACT_PATH.is_file():
        return [], (
            "Tesseract не найден по пути "
            f"{TESSERACT_PATH}. Проверь установку OCR."
        )

    video_path = Path(video_path)
    candidates = []

    # Берём верхнюю левую область кадра. Масштабирование помогает OCR
    # читать небольшие цифры табло на записи 1080p и 720p.
    with tempfile.TemporaryDirectory(prefix="fc27_score_") as temp_dir:
        frame_pattern = str(Path(temp_dir) / "frame_%06d.jpg")
        command = [
            str(FFMPEG_PATH),
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(video_path),
            "-vf",
            "fps=0.5,"
            "crop=trunc(iw*0.30/2)*2:trunc(ih*0.14/2)*2:0:0,"
            "scale=900:-1",
            "-q:v", "3",
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
            return [], "FFmpeg не смог подготовить кадры табло." + (
                f"\n{details}" if details else ""
            )

        frame_paths = sorted(Path(temp_dir).glob("frame_*.jpg"))
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

            ocr_command = [
                str(TESSERACT_PATH),
                str(frame_path),
                "stdout",
                "--psm", "6",
                "-c", "tessedit_char_whitelist=0123456789:",
            ]

            try:
                ocr_result = subprocess.run(
                    ocr_command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue

            if ocr_result.returncode != 0:
                continue

            numbers = SCORE_PATTERN.findall(ocr_result.stdout or "")
            if len(numbers) < 2:
                pending_score = None
                pending_count = 0
                continue

            score = (int(numbers[0]), int(numbers[1]))
            if score[0] > 20 or score[1] > 20:
                pending_score = None
                pending_count = 0
                continue

            if score == pending_score and timestamp - pending_time <= 3.0:
                pending_count += 1
            else:
                pending_score = score
                pending_time = timestamp
                pending_count = 1

            # Два последовательных чтения подтверждают показание.
            if pending_count < 2:
                continue

            if confirmed_score is None:
                confirmed_score = score
                pending_score = None
                pending_count = 0
                continue

            if score != confirmed_score:
                arg_delta = score[0] - confirmed_score[0]
                opponent_delta = score[1] - confirmed_score[1]

                # На первом этапе считаем голом только увеличение счёта
                # ровно на один у одной из команд.
                if (
                    (arg_delta == 1 and opponent_delta == 0)
                    or (arg_delta == 0 and opponent_delta == 1)
                ):
                    old_text = f"{confirmed_score[0]}:{confirmed_score[1]}"
                    new_text = f"{score[0]}:{score[1]}"
                    candidates.append({
                        "timestamp": pending_time,
                        "duration": duration_seconds,
                        "kind": (
                            f"Изменение счёта ARG {old_text} → {new_text}"
                        ),
                        "start": max(0.0, pending_time - 18.0),
                        "end": min(duration_seconds, pending_time + 18.0),
                        "source": "scoreboard",
                    })

                # Обновляем опорный счёт даже при нетипичном изменении,
                # чтобы последующие события сравнивались с актуальным HUD.
                confirmed_score = score

            pending_score = None
            pending_count = 0

    return candidates, None
