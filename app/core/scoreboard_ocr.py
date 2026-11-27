import csv
import re
import subprocess
from collections import Counter, deque
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

from app.core.media_probe import FFMPEG_PATH, PROJECT_ROOT


TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

DIGIT_PATTERN = re.compile(r"[0-9Oo]")


def _prepare_digit_crop(frame_path, row_name):
    """Готовит отдельную увеличенную область верхней или нижней цифры."""
    image = QImage(str(frame_path))
    if image.isNull():
        raise ValueError(f"Не удалось открыть изображение: {frame_path}")

    width = image.width()
    height = image.height()

    # Исходный кадр — квадратная вырезка табло, увеличенная FFmpeg в 8 раз.
    # Цифры находятся справа от эмблем, одна над другой.
    x = round(width * 0.36)
    crop_width = round(width * 0.25)
    if row_name == "top":
        y = round(height * 0.12)
        crop_height = round(height * 0.28)
    else:
        y = round(height * 0.40)
        crop_height = round(height * 0.30)

    digit_crop = image.copy(x, y, crop_width, crop_height)
    if digit_crop.isNull():
        raise ValueError(f"Не удалось вырезать {row_name} цифру")

    scaled = digit_crop.scaled(
        850,
        950,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    # Чёрные поля помогают Tesseract отделить цифру от границ табло.
    padded = QImage(
        1050,
        1150,
        QImage.Format.Format_Grayscale8,
    )
    padded.fill(0)
    painter = QPainter(padded)
    painter.drawImage(100, 100, scaled)
    painter.end()

    crop_path = frame_path.with_name(
        f"_{frame_path.stem}_{row_name}_ocr.png"
    )
    if not padded.save(str(crop_path), "PNG"):
        raise OSError(f"Не удалось сохранить временный кадр: {crop_path}")
    return crop_path


def _run_tesseract_digit(image_path, psm):
    command = [
        str(TESSERACT_PATH),
        str(image_path),
        "stdout",
        "--psm", str(psm),
        "-c", "tessedit_char_whitelist=0123456789Oo",
        "-c", "classify_bln_numeric_mode=1",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )
    if result.returncode != 0:
        error_text = (result.stderr or "").strip()
        raise RuntimeError(
            error_text or f"Tesseract exit code {result.returncode}"
        )

    raw = (result.stdout or "").strip().replace("\n", "")
    matches = DIGIT_PATTERN.findall(raw)
    if not matches:
        return None, raw

    # Иногда Tesseract захватывает соседний артефакт и выдаёт, например,
    # «41». Для одиночной цифры берём последний распознанный символ.
    character = matches[-1].lower()
    digit = 0 if character == "o" else int(character)
    return digit, raw


def _read_digit(frame_path, row_name):
    """Распознаёт одну цифру двумя режимами, третий использует при споре."""
    crop_path = None
    raw_parts = []
    try:
        crop_path = _prepare_digit_crop(frame_path, row_name)
        first, raw_first = _run_tesseract_digit(crop_path, 8)
        second, raw_second = _run_tesseract_digit(crop_path, 13)
        raw_parts.extend([f"psm8={raw_first}", f"psm13={raw_second}"])

        if first is not None and first == second:
            return first, "; ".join(raw_parts), ""

        third, raw_third = _run_tesseract_digit(crop_path, 10)
        raw_parts.append(f"psm10={raw_third}")
        votes = [value for value in (first, second, third) if value is not None]
        if not votes:
            return None, "; ".join(raw_parts), ""

        counts = Counter(votes)
        digit, count = counts.most_common(1)[0]
        if count >= 2:
            return digit, "; ".join(raw_parts), ""

        return None, "; ".join(raw_parts), ""
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        return None, "; ".join(raw_parts), str(error)
    finally:
        if crop_path is not None:
            try:
                crop_path.unlink(missing_ok=True)
            except OSError:
                pass


def _read_score_digits_debug(frame_path):
    """Распознаёт цифры команд независимо, сохраняя частичные результаты."""
    top, top_raw, top_error = _read_digit(frame_path, "top")
    bottom, bottom_raw, bottom_error = _read_digit(frame_path, "bottom")
    raw_text = f"Верх: [{top_raw}] | Низ: [{bottom_raw}]"

    errors = [error for error in (top_error, bottom_error) if error]
    error_text = " | ".join(errors)

    if top is not None and top > 20:
        top = None
    if bottom is not None and bottom > 20:
        bottom = None

    return top, bottom, raw_text, error_text


def _read_score_debug(frame_path):
    top, bottom, raw_text, error_text = _read_score_digits_debug(frame_path)
    if top is None or bottom is None:
        return None, raw_text, error_text
    return (top, bottom), raw_text, error_text


def _read_score(frame_path):
    score, _, _ = _read_score_debug(frame_path)
    return score


def _vote_digit(recent_reads, digit_index):
    """Голосует за одну цифру в скользящем временном окне."""
    valid_reads = [
        (timestamp, values[digit_index])
        for timestamp, values in recent_reads
        if values[digit_index] is not None
    ]
    if len(valid_reads) < 3:
        return None, [], 0, len(valid_reads)

    counts = Counter(value for _, value in valid_reads)
    digit, count = counts.most_common(1)[0]
    confidence = count / len(valid_reads)

    # Одного большинства недостаточно: цифра должна иметь минимум 3
    # подтверждения и занимать не менее 60% всех читаемых значений строки.
    if count < 3 or confidence < 0.60:
        return None, [], count, len(valid_reads)

    supporting_times = [
        timestamp for timestamp, value in valid_reads if value == digit
    ]
    return digit, supporting_times, count, len(valid_reads)


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

    diagnostic_dir = (
        PROJECT_ROOT / "reports" / "scoreboard_diagnostics" / video_path.stem
    )
    try:
        diagnostic_dir.mkdir(parents=True, exist_ok=True)
        for old_file in diagnostic_dir.glob("score_*.png"):
            old_file.unlink()
        for old_file in diagnostic_dir.glob("_score_*_ocr.png"):
            old_file.unlink()
        for old_file in diagnostic_dir.glob("ocr_results.csv"):
            old_file.unlink()
        for old_file in diagnostic_dir.glob("scoreboard_events.csv"):
            old_file.unlink()
        for old_file in diagnostic_dir.glob("scoreboard_candidates.csv"):
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
    # 15 секунд позволяют собрать редкие, но устойчивые OCR-чтения,
    # не смешивая их с показаниями, которые были значительно раньше.
    recent_reads = deque(maxlen=15)
    diagnostic_rows = []
    decision_rows = []

    for frame_index, frame_path in enumerate(frame_paths):
        timestamp = float(frame_index)
        if timestamp >= duration_seconds:
            break

        top_digit, bottom_digit, raw_text, ocr_error = (
            _read_score_digits_debug(frame_path)
        )
        score = (
            (top_digit, bottom_digit)
            if top_digit is not None and bottom_digit is not None
            else None
        )
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

        recent_reads.append((timestamp, (top_digit, bottom_digit)))
        top_vote, top_times, top_count, top_total = _vote_digit(
            recent_reads, 1
        )
        bottom_vote, bottom_times, bottom_count, bottom_total = _vote_digit(
            recent_reads, 2
        )

        voted_score = None
        vote_time = None
        if top_vote is not None and bottom_vote is not None:
            # Обе цифры должны подтверждаться свежими чтениями, иначе
            # алгоритм может случайно собрать счёт из разных моментов.
            latest_top = top_times[-1]
            latest_bottom = bottom_times[-1]
            if (
                timestamp - latest_top <= 3.0
                and timestamp - latest_bottom <= 3.0
                and abs(latest_top - latest_bottom) <= 2.0
            ):
                voted_score = (top_vote, bottom_vote)
                vote_time = max(top_times[0], bottom_times[0])

        vote_description = (
            f"Верх {top_vote if top_vote is not None else '—'} "
            f"({top_count}/{top_total}); низ "
            f"{bottom_vote if bottom_vote is not None else '—'} "
            f"({bottom_count}/{bottom_total})"
        )

        if voted_score is None:
            decision = "ожидание подтверждения цифр"
            decision_detail = (
                f"{vote_description}; требуется минимум 3 чтения "
                "и согласованность цифр по времени"
            )
        elif voted_score == confirmed_score:
            decision = "подтверждён прежний счёт"
            decision_detail = (
                f"Счёт {voted_score[0]}:{voted_score[1]} остаётся без изменений; "
                f"{vote_description}"
            )
            # confirmed_time намеренно не обновляем: это время последнего
            # изменения счёта, а не время последнего стабильного кадра.
        else:
            if confirmed_score is None:
                confirmed_score = voted_score
                confirmed_time = vote_time
                decision = "подтверждено начальное значение"
                decision_detail = (
                    f"Начальный счёт {voted_score[0]}:{voted_score[1]}; "
                    f"{vote_description}"
                )
            else:
                arg_delta = voted_score[0] - confirmed_score[0]
                opponent_delta = voted_score[1] - confirmed_score[1]
                total_delta = arg_delta + opponent_delta

                # В футбольном матче за одно событие счёт меняется ровно
                # на один гол одной из команд. Скачки OCR не меняют состояние.
                valid_increase = (
                    arg_delta >= 0
                    and opponent_delta >= 0
                    and total_delta == 1
                    and (
                        (arg_delta == 1 and opponent_delta == 0)
                        or (arg_delta == 0 and opponent_delta == 1)
                    )
                )

                if valid_increase:
                    decision = "ПЕРЕХОД ПРИНЯТ"
                    decision_detail = (
                        f"Изменение {confirmed_score[0]}:{confirmed_score[1]} "
                        f"→ {voted_score[0]}:{voted_score[1]}; "
                        f"{vote_description}"
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

                    candidates.append({
                        "timestamp": vote_time,
                        "duration": duration_seconds,
                        "kind": (
                            f"Гол: счёт ARG {old_text} → {new_text}"
                            f"{interval_text}"
                        ),
                        "start": max(0.0, vote_time - 18.0),
                        "end": min(duration_seconds, vote_time + 18.0),
                        "source": "scoreboard",
                        "goal_count": 1,
                        "score_interval_start": interval_start,
                        "score_interval_end": interval_end,
                    })
                    confirmed_score = voted_score
                    confirmed_time = vote_time
                else:
                    decision = "переход отклонён"
                    decision_detail = (
                        f"Недопустимый переход "
                        f"{confirmed_score[0]}:{confirmed_score[1]} → "
                        f"{voted_score[0]}:{voted_score[1]} "
                        f"(дельта {arg_delta:+d}:{opponent_delta:+d}); "
                        f"{vote_description}. Подтверждённый счёт сохранён."
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
                "Ответ Tesseract (отдельные цифры)",
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
