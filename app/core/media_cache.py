
import json
from pathlib import Path


def load_metadata_cache(cache_path):
    cache_path = Path(cache_path)

    if not cache_path.exists():
        return {}

    try:
        with open(
            cache_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except (OSError, json.JSONDecodeError) as error:
        print(f"Ошибка чтения кэша: {error}")

    return {}


def save_metadata_cache(cache_path, metadata_cache):
    cache_path = Path(cache_path)

    try:
        with open(
            cache_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                metadata_cache,
                file,
                ensure_ascii=False,
                indent=4
            )

    except OSError as error:
        print(f"Ошибка сохранения кэша: {error}")
