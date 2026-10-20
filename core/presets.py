from __future__ import annotations

import json
from pathlib import Path

from .config import DEFAULT_ENABLED, PARAM_SPECS
from .pipeline import Settings

PRESETS_FILE = Path(__file__).resolve().parent.parent / "presets.json"


def default_settings() -> Settings:
    values: dict[str, dict] = {}
    for spec in PARAM_SPECS:
        if spec["kind"] == "dims":
            values[spec["key"]] = {"width": spec["width"], "height": spec["height"]}
        elif spec["kind"] != "toggle":
            values[spec["key"]] = {"min": spec["min"], "max": spec["max"]}
    enabled = {spec["key"]: spec["key"] in DEFAULT_ENABLED for spec in PARAM_SPECS}
    return Settings(enabled=enabled, values=values)


BUILTIN_PRESETS: dict[str, set[str]] = {
    "Мягкий (незаметно глазу)": {
        "framerate", "vbitrate", "abitrate", "saturation", "contrast",
        "brightness", "gamma", "noise", "us_metadata",
    },
    "Средний (рекомендуемый)": {
        "framerate", "vbitrate", "abitrate", "saturation", "contrast",
        "brightness", "gamma", "noise", "speed", "zoom", "crop",
        "pixel_shift", "wave_shift", "us_metadata",
    },
    "Жёсткий (максимум отличий)": {
        "framerate", "vbitrate", "abitrate", "saturation", "contrast",
        "brightness", "gamma", "noise", "speed", "zoom", "crop",
        "pixel_shift", "wave_shift", "volume", "vignette", "lens",
        "rotation", "cut_start", "cut_end", "random_size", "us_metadata",
    },
    "Только метаданные и кодек": {
        "framerate", "vbitrate", "abitrate", "us_metadata",
    },
}


def builtin(name: str) -> Settings:
    settings = default_settings()
    keys = BUILTIN_PRESETS[name]
    settings.enabled = {spec["key"]: spec["key"] in keys for spec in PARAM_SPECS}
    return settings


def load_all() -> dict[str, dict]:
    if not PRESETS_FILE.exists():
        return {}
    try:
        data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save(name: str, settings: Settings) -> None:
    data = load_all()
    data[name] = settings.to_dict()
    PRESETS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def delete(name: str) -> None:
    data = load_all()
    if data.pop(name, None) is not None:
        PRESETS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
