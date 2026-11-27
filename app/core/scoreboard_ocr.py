import csv
import re
from collections import Counter, deque
import subprocess
from pathlib import Path

from app.core.media_probe import FFMPEG_PATH, PROJECT_ROOT


TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

SCORE_PATTERN = re.compile(r"\d{1,2}")


def _read_score_debug(frame_path):
    """Возвращает распознанный счёт и полный текстовый ответ Tesseract."""
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
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, "", str(error)

    raw_text = (result.stdout or "").strip()
    if result.returncode != 0:
        error_text = (result.stderr or "").strip()
        return None, raw_text, error_text or f"Tesseract exit code {result.returncode}"

    # Сохраняем исходный текст отдельно в диагностике. Парсер пока оставляем
    # прежним, чтобы сначала увидеть фактическое поведение OCR.
    numbers = []
    for line in raw_text.splitlines():
        matches = SCORE_PATTERN.findall(line)
        if matches:
            numbers.append(matches[0])

    if len(numbers) != 2:
        return None, raw_text, ""

    score = (int(numbers[0]), int(numbers[1]))
    if score[0] > 20 or score[1] > 20:
        return None, raw_text, ""

    return score, raw_text, ""


def _read_score(frame_path):
    score, _, _ = _read_score_debug(frame_path)
    return score


def find_score_changes(video_path, duration_seconds):
    """Распознаёт изменение счёта и сохраняет диагностику каждого OCR-кадра."""
    if not TESSERACT_PATH.is_file():
        return [], (
            "Tesseract не найден по пути "
            f"{TESSERACT_PATH}. Проверь установку OCR."
        )

    if not FFMPEG_PATH.is_file():
        return [], "Не найден FFmpeg. Проверь папку tools/ffmpeg/bin."

    video_path = Path(video_path)
    candidates = []

    # По скриншотам пользователя табло занимает приблизительно X=5–16.5%,
    # Y=5–13% кадра. Для OCR берём правую часть табло с обеими цифрами счёта,
    # оставляя запас по краям, чтобы не обрезать контуры цифр.
    diagnostic_dir = (
        PROJECT_ROOT / "reports" / "scoreboard_diagnostics" / video_path.stem
    )
    try:
        diagnostic_dir.mkdir(parents=True, exist_ok=True)
        for old_file in diagnostic_dir.glob("score_*.png"):
            old_file.unlink()
        for old_file in diagnostic_dir.glob("ocr_results.csv"):
            old_file.unlink()
    except OSError as error:
        return [], f"Не удалось создать папку диагностики OCR: {error}"

    frame_pattern = str(diagnostic_dir / "score_%06d.png")
    filter_chain = (
        "fps=1,"
        "crop=trunc(iw*0.045/2)*2:"
        "trunc(ih*0.08/2)*2:"
        "trunc(iw*0.12/2)*2:"
        "trunc(ih*0.048/2)*2,"
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

    frame_paths = sorted(diagnostic_dir.glob("score_*.png"))
    if not frame_paths:
        return [], "Не удалось извлечь кадры для распознавания табло."

    confirmed_score = None
    confirmed_time = None
    recent_reads = deque(maxlen=5)
    last_voted_score = None
    diagnostic_rows = []
    decision_rows = []

    for frame_index, frame_path in enumerate(frame_paths):
        timestamp = float(frame_index)
        if timestamp >= duration_seconds:
            break

        score, raw_text, ocr_error = _read_score_debug(frame_path)
        diagnostic_rows.append([
            f"{timestamp:.1f}",
            str(frame_path.name),
            raw_text.replace("\n", " | "),
            "" if score is None else f"{score[0]}:{score[1]}",
            ocr_error,
        ])

        previous_confirmed = (
            "" if confirmed_score is None
            else f"{confirmed_score[0]}:{confirmed_score[1]}"
        )
        decision = "не распознано" if score is None else "ожидает подтверждения"
        decision_detail = ocr_error

        # Голосуем по пяти последним секундам. Один-два неудачных или
        # ошибочных OCR-кадра больше не сбрасывают накопленное подтверждение.
        recent_reads.append((timestamp, score))
        valid_reads = [item for item in recent_reads if item[1] is not None]
        counts = Counter(item[1] for item in valid_reads)
        voted_score, vote_count = (None, 0)
        if counts:
            voted_score, vote_count = counts.most_common(1)[0]

        if voted_score is None or vote_count < 3:
            decision = "ожидание большинства"
            decision_detail = f"Совпадений в окне: {vote_count}/5"
        elif voted_score == last_voted_score:
            decision = "большинство уже обработано"
            decision_detail = f"Устойчивое значение {voted_score[0]}:{voted_score[1]}"
        else:
            last_voted_score = voted_score
            supporting_times = [
                item[0] for item in valid_reads if item[1] == voted_score
            ]
            vote_time = supporting_times[0]

            if confirmed_score is None:
                confirmed_score = voted_score
                confirmed_time = vote_time
                decision = "подтверждено начальное значение"
                decision_detail = f"Голосование 3 из 5: {voted_score[0]}:{voted_score[1]}"
            elif voted_score == confirmed_score:
                confirmed_time = vote_time
                decision = "подтверждён прежний счёт"
                decision_detail = f"Голосование 3 из 5: {voted_score[0]}:{voted_score[1]}"
            else:
                arg_delta = voted_score[0] - confirmed_score[0]
                opponent_delta = voted_score[1] - confirmed_score[1]
                total_delta = arg_delta + opponent_delta

                valid_increase = (
                    0 <= arg_delta <= 3
                    and 0 <= opponent_delta <= 3
                    and 1 <= total_delta <= 4
                )

                if valid_increase:
                    decision = "ПЕРЕХОД ПРИНЯТ"
                    decision_detail = (
                        f"Изменение {confirmed_score[0]}:{confirmed_score[1]} "
                        f"→ {voted_score[0]}:{voted_score[1]}; голосование "
                        f"{vote_count}/5"
                    )
                    old_text = f"{confirmed_score[0]}:{confirmed_score[1]}"
                    new_text = f"{voted_score[0]}:{voted_score[1]}"
                    interval_start = confirmed_time or 0.0
                    interval_end = vote_time
                    interval_text = (
                        f"; интервал подтверждения "
                        f"{int(interval_start // 60):02d}:"
                        f"{int(interval_start % 60):02d}–"
                        f"{int(interval_end // 60):02d}:"
                        f"{int(interval_end % 60):02d}"
                    )
                    last_two = total_delta % 100
                    last_digit = total_delta % 10
                    if 11 <= last_two <= 14:
                        goal_word = "голов"
                    elif last_digit == 1:
                        goal_word = "гол"
                    elif 2 <= last_digit <= 4:
                        goal_word = "гола"
                    else:
                        goal_word = "голов"

                    candidates.append({
                        "timestamp": vote_time,
                        "duration": duration_seconds,
                        "kind": (
                            f"Изменение счёта ARG {old_text} → {new_text} "
                            f"(+{total_delta} {goal_word}{interval_text})"
                        ),
                        "start": max(0.0, vote_time - 18.0),
                        "end": min(duration_seconds, vote_time + 18.0),
                        "source": "scoreboard",
                        "goal_count": total_delta,
                        "score_interval_start": interval_start,
                        "score_interval_end": interval_end,
                    })
                    confirmed_score = voted_score
                    confirmed_time = vote_time
                else:
                    decision = "переход отклонён"
                    decision_detail = (
                        f"Недопустимый скачок: {arg_delta:+d}:{opponent_delta:+d}"
                    )

        decision_rows.append([
            f"{timestamp:.1f}", raw_text.replace("\n", " | "),
            previous_confirmed,
            "" if score is None else f"{score[0]}:{score[1]}",
            decision, decision_detail,
        ])

    try:
        with (diagnostic_dir / "ocr_results.csv").open(
            "w", newline="", encoding="utf-8-sig"
        ) as csv_file:
            writer = csv.writer(csv_file, delimiter=";")
            writer.writerow([
                "Время видео, сек",
                "Изображение",
                "Ответ Tesseract",
                "Распознанный счёт",
                "Ошибка OCR",
            ])
            writer.writerows(diagnostic_rows)
    except OSError as error:
        return candidates, (
            "Распознавание завершено, но не удалось сохранить журнал OCR: "
            f"{error}"
        )

    try:
        with (diagnostic_dir / "scoreboard_events.csv").open(
            "w", newline="", encoding="utf-8-sig"
        ) as csv_file:
            writer = csv.writer(csv_file, delimiter=";")
            writer.writerow([
                "Время видео, сек",
                "Ответ Tesseract",
                "Счёт до проверки",
                "Текущий счёт",
                "Решение алгоритма",
                "Пояснение",
            ])
            writer.writerows(decision_rows)

        with (diagnostic_dir / "scoreboard_candidates.csv").open(
            "w", newline="", encoding="utf-8-sig"
        ) as csv_file:
            writer = csv.writer(csv_file, delimiter=";")
            writer.writerow([
                "Время события, сек",
                "Тип события",
                "Начало фрагмента, сек",
                "Конец фрагмента, сек",
                "Количество голов",
            ])
            for candidate in candidates:
                writer.writerow([
                    f"{candidate['timestamp']:.1f}",
                    candidate["kind"],
                    f"{candidate['start']:.1f}",
                    f"{candidate['end']:.1f}",
                    candidate["goal_count"],
                ])
    except OSError as error:
        return candidates, (
            "Распознавание завершено, но не удалось сохранить "
            f"журнал решений OCR: {error}"
        )

    return candidates, None
