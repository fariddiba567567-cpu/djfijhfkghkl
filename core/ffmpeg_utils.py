from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import MF_ENCODERS

APP_DIR = Path(__file__).resolve().parent.parent

_WINDOWS_HINTS = [
    APP_DIR / "ffmpeg" / "bin",
    APP_DIR / "bin",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links",
    Path("C:/ffmpeg/bin"),
    Path("C:/Program Files/ffmpeg/bin"),
]

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _find(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    exe = name + (".exe" if sys.platform == "win32" else "")
    for hint in _WINDOWS_HINTS:
        candidate = hint / exe
        if candidate.exists():
            return str(candidate)
    packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if packages.is_dir():
        for match in packages.glob(f"*FFmpeg*/**/{exe}"):
            return str(match)
    return None


def ffmpeg_path() -> str | None:
    return _find("ffmpeg")


def ffprobe_path() -> str | None:
    return _find("ffprobe")


def run_quiet(args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


@dataclass
class MediaInfo:
    path: str
    width: int
    height: int
    duration: float
    fps: float
    has_audio: bool

    @property
    def is_vertical(self) -> bool:
        return self.height >= self.width


def probe(path: str) -> MediaInfo:
    exe = ffprobe_path()
    if not exe:
        raise RuntimeError("ffprobe не найден. Установите FFmpeg и добавьте его в PATH.")

    result = run_quiet([
        exe, "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ], timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe не смог прочитать файл: {result.stderr.strip()[:300]}")

    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError("В файле нет видеопотока.")
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    duration = 0.0
    for source in (data.get("format", {}).get("duration"), video.get("duration")):
        try:
            duration = float(source)
            break
        except (TypeError, ValueError):
            continue

    fps = 30.0
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/0"
    try:
        num, _, den = rate.partition("/")
        if float(den or 1) > 0 and float(num) > 0:
            fps = float(num) / float(den or 1)
    except ValueError:
        pass

    width, height = int(video.get("width", 0)), int(video.get("height", 0))
    rotation = 0
    try:
        rotation = abs(int(float(video.get("side_data_list", [{}])[0].get("rotation", 0))))
    except (ValueError, TypeError, IndexError, AttributeError):
        try:
            rotation = abs(int(video.get("tags", {}).get("rotate", 0)))
        except (ValueError, TypeError):
            rotation = 0
    if rotation in (90, 270):
        width, height = height, width

    return MediaInfo(path, width, height, duration, fps, has_audio)


_encoder_cache: dict[str, bool] = {}


def encoder_available(ffmpeg: str, encoder: str) -> bool:
    if encoder in _encoder_cache:
        return _encoder_cache[encoder]
    extra = ["-hw_encoding", "true", "-pix_fmt", "nv12"] if encoder in MF_ENCODERS else []
    try:
        result = run_quiet([
            ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=320x320:d=0.2",
            "-c:v", encoder, *extra, "-frames:v", "3", "-f", "null", "-",
        ], timeout=30)
        ok = result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    _encoder_cache[encoder] = ok
    return ok


VIDEO_EXTENSIONS = (
    "*.mp4", "*.mov", "*.mkv", "*.avi", "*.webm", "*.m4v", "*.mpg", "*.mpeg", "*.wmv", "*.flv",
)
