from fractions import Fraction


def build_clip_export_command(
    source_path,
    start_frame,
    end_frame,
    frame_rate,
    output_path,
    has_audio=True,
):
    """Создаёт команду FFmpeg с границами видеофрагмента по номерам кадров."""
    if not isinstance(frame_rate, Fraction):
        frame_rate = Fraction(str(frame_rate))

    start_seconds = Fraction(start_frame, 1) / frame_rate
    end_seconds = Fraction(end_frame, 1) / frame_rate

    command = [
        "-hide_banner",
        "-y",
        "-i", str(source_path),
        "-map", "0:v:0",
        "-vf",
        f"trim=start_frame={start_frame}:end_frame={end_frame},"
        "setpts=PTS-STARTPTS",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
    ]

    if has_audio:
        command.extend([
            "-map", "0:a:0?",
            "-af",
            f"atrim=start={float(start_seconds):.9f}:"
            f"end={float(end_seconds):.9f},asetpts=PTS-STARTPTS",
            "-c:a", "aac",
            "-b:a", "192k",
        ])

    command.extend([
        "-movflags", "+faststart",
        str(output_path),
    ])

    return command
