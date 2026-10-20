from __future__ import annotations

import math
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import (
    CPU_ENCODER, DEFAULT_MODE, GPU_ENCODERS, MF_ENCODERS, PARAM_BY_KEY,
)
from .ffmpeg_utils import MediaInfo

AUDIO_RATE = 44100
MIN_DURATION = 0.3


_US_DEVICES = [
    ("Apple", "iPhone 17 Pro Max", "26.0"),
    ("Apple", "iPhone 17 Pro", "26.0.1"),
    ("Apple", "iPhone 17", "26.0"),
    ("Apple", "iPhone Air", "26.0.1"),
    ("Apple", "iPhone 16 Pro Max", "18.5"),
    ("Apple", "iPhone 16 Pro", "18.4.1"),
    ("Apple", "iPhone 16 Plus", "18.5"),
    ("Apple", "iPhone 16", "18.3.2"),
    ("Apple", "iPhone 16e", "18.4"),
    ("Apple", "iPhone 15 Pro", "17.6.1"),
    ("samsung", "SM-S938U", "Android 16"),
    ("samsung", "SM-S931U", "Android 16"),
    ("samsung", "SM-S928U", "Android 15"),
    ("Google", "Pixel 10 Pro", "Android 16"),
    ("Google", "Pixel 9 Pro XL", "Android 15"),
    ("Xiaomi", "24129PN74G", "Android 15"),
    ("OnePlus", "CPH2653", "Android 15"),
]

_US_LOCATIONS = [
    (40.7128, -74.0060, 10),
    (34.0522, -118.2437, 87),
    (41.8781, -87.6298, 181),
    (29.7604, -95.3698, 13),
    (33.4484, -112.0740, 331),
    (25.7617, -80.1918, 2),
    (47.6062, -122.3321, 53),
    (30.2672, -97.7431, 149),
    (39.7392, -104.9903, 1609),
    (36.1699, -115.1398, 610),
]

_TIMESCALES = [600, 15360, 30000, 24000, 90000]


def _iso6709(lat: float, lon: float, alt: int) -> str:
    return f"{lat:+08.4f}{lon:+09.4f}{alt:+.3f}/"


def _us_metadata(rnd: random.Random) -> dict[str, str]:
    make, model, software = rnd.choice(_US_DEVICES)
    lat, lon, alt = rnd.choice(_US_LOCATIONS)
    lat += rnd.uniform(-0.01, 0.01)
    lon += rnd.uniform(-0.01, 0.01)
    shot_at = datetime.now(timezone.utc) - timedelta(
        days=rnd.randint(0, 45), hours=rnd.randint(0, 23), minutes=rnd.randint(0, 59)
    )
    return {
        "creation_time": shot_at.strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
        "com.apple.quicktime.make": make,
        "com.apple.quicktime.model": model,
        "com.apple.quicktime.software": software,
        "com.apple.quicktime.creationdate": shot_at.strftime("%Y-%m-%dT%H:%M:%S-0500"),
        "com.apple.quicktime.location.ISO6709": _iso6709(lat, lon, alt),
        "location": _iso6709(lat, lon, alt),
        "location-eng": _iso6709(lat, lon, alt),
        "make": make,
        "model": model,
        "encoder": software,
        "comment": uuid.uuid4().hex[:16],
    }


def _legacy_mode(data: dict) -> str:
    """Пресеты старого формата: три поля encoder/x264_preset/cpu_load → режим."""
    if data.get("cpu_load", "max") != "max":
        return "background"
    if data.get("encoder") in GPU_ENCODERS:
        return "fast"
    return "quality" if "encoder" in data else DEFAULT_MODE


@dataclass
class Settings:

    enabled: dict[str, bool] = field(default_factory=dict)
    values: dict[str, dict] = field(default_factory=dict)
    mode: str = DEFAULT_MODE
    encoder: str = CPU_ENCODER  # подставляется перед запуском, в пресет не пишется

    def to_dict(self) -> dict:
        return {
            "enabled": dict(self.enabled),
            "values": {k: dict(v) for k, v in self.values.items()},
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        return cls(
            enabled=dict(data.get("enabled", {})),
            values={k: dict(v) for k, v in data.get("values", {}).items()},
            mode=data.get("mode") or _legacy_mode(data),
        )

    @property
    def x264_preset(self) -> str:
        return "medium" if self.mode == "quality" else "veryfast"

    def thread_limit(self) -> int:
        if self.mode != "background":
            return 0
        return max(1, (os.cpu_count() or 4) // 2)

    def on(self, key: str) -> bool:
        return bool(self.enabled.get(key))

    def rng_pair(self, key: str) -> tuple[float, float]:
        spec = PARAM_BY_KEY[key]
        raw = self.values.get(key, {})
        lo = float(raw.get("min", spec.get("min", 0)))
        hi = float(raw.get("max", spec.get("max", 0)))
        return (lo, hi) if lo <= hi else (hi, lo)


@dataclass
class Job:
    args: list[str]
    output: str
    picked: dict[str, object]
    duration: float


def _even(value: float, minimum: int = 2) -> int:
    return max(minimum, int(round(value / 2)) * 2)


def _pick(rnd: random.Random, settings: Settings, key: str, integer: bool = False):
    lo, hi = settings.rng_pair(key)
    value = rnd.uniform(lo, hi)
    return int(round(value)) if integer else round(value, 5)


def build_job(
    media: MediaInfo,
    settings: Settings,
    output_path: str,
    ffmpeg: str,
    seed: int | None = None,
) -> Job:
    rnd = random.Random(seed)
    picked: dict[str, object] = {}

    src_w = _even(media.width or 1080)
    src_h = _even(media.height or 1920)

    if settings.on("random_size"):
        out_w = _even(rnd.randint(864, 1130))
        out_h = _even(out_w * 16 / 9)
        picked["random_size"] = f"{out_w}x{out_h}"
    elif settings.on("dimensions"):
        raw = settings.values.get("dimensions", {})
        out_w = _even(int(raw.get("width", PARAM_BY_KEY["dimensions"]["width"])))
        out_h = _even(int(raw.get("height", PARAM_BY_KEY["dimensions"]["height"])))
        picked["dimensions"] = f"{out_w}x{out_h}"
    else:
        out_w, out_h = src_w, src_h

    duration = media.duration if media.duration > 0 else 0.0
    start = 0.0
    if settings.on("cut_start"):
        start = _pick(rnd, settings, "cut_start")
        picked["cut_start"] = start
    tail = 0.0
    if settings.on("cut_end"):
        tail = _pick(rnd, settings, "cut_end")
        picked["cut_end"] = tail

    length = 0.0
    if duration > 0:
        length = duration - start - tail
        if length < MIN_DURATION:
            start = min(start, max(0.0, (duration - MIN_DURATION) / 2))
            length = max(MIN_DURATION, duration - start - tail)
            length = min(length, duration - start)

    chain: list[str] = []

    speed = None
    if settings.on("speed"):
        speed = max(0.5, min(2.0, _pick(rnd, settings, "speed")))
        picked["speed"] = speed
        chain.append(f"setpts=PTS/{speed:.5f}")

    if settings.on("rotation"):
        angle = _pick(rnd, settings, "rotation")
        picked["rotation"] = angle
        if abs(angle) > 1e-4:
            rad = math.radians(angle)
            chain.append(f"rotate={rad:.6f}:ow=iw:oh=ih:fillcolor=black")
            ratio = max(src_w, src_h) / max(1, min(src_w, src_h))
            keep = max(0.70, 1.0 - 2.2 * abs(math.sin(rad)) * ratio)
            chain.append(f"crop=iw*{keep:.5f}:ih*{keep:.5f}")

    if settings.on("zoom"):
        zoom = max(1.0, _pick(rnd, settings, "zoom"))
        picked["zoom"] = zoom
        if zoom > 1.0001:
            chain.append(f"crop=iw/{zoom:.5f}:ih/{zoom:.5f}")

    if settings.on("crop"):
        pct = max(0.0, min(40.0, _pick(rnd, settings, "crop"))) / 100.0
        picked["crop_%"] = round(pct * 100, 3)
        if pct > 0:
            keep = 1.0 - pct
            fx, fy = rnd.random(), rnd.random()
            chain.append(
                f"crop=iw*{keep:.5f}:ih*{keep:.5f}:"
                f"(iw-iw*{keep:.5f})*{fx:.4f}:(ih-ih*{keep:.5f})*{fy:.4f}"
            )

    if settings.on("pixel_shift"):
        amount = max(0.0, _pick(rnd, settings, "pixel_shift"))
        picked["pixel_shift"] = amount
        pad = max(1, int(math.ceil(amount)))
        dx = rnd.randint(-pad, pad)
        dy = rnd.randint(-pad, pad)
        chain.append(f"crop=iw-{2 * pad}:ih-{2 * pad}:{pad + dx}:{pad + dy}")

    if settings.on("flip"):
        picked["flip"] = True
        chain.append("hflip")

    if settings.on("lens"):
        k1 = _pick(rnd, settings, "lens")
        picked["lens"] = k1
        chain.append(f"lenscorrection=k1={k1:.5f}:k2={k1 / 2:.5f}")

    eq_parts: list[str] = []
    for key, name in (
        ("brightness", "brightness"),
        ("contrast", "contrast"),
        ("saturation", "saturation"),
        ("gamma", "gamma"),
    ):
        if settings.on(key):
            value = _pick(rnd, settings, key)
            picked[key] = value
            eq_parts.append(f"{name}={value:.5f}")
    if eq_parts:
        chain.append("eq=" + ":".join(eq_parts))

    if settings.on("vignette"):
        angle = max(0.0, _pick(rnd, settings, "vignette"))
        picked["vignette"] = angle
        chain.append(f"vignette=a={angle:.5f}")

    if settings.on("noise"):
        strength = max(0, _pick(rnd, settings, "noise", integer=True))
        picked["noise"] = strength
        if strength:
            chain.append(f"noise=alls={strength}:allf=t+u:all_seed={rnd.randint(1, 999999)}")

    black = 0
    if settings.on("black_border"):
        black = max(0, _pick(rnd, settings, "black_border", integer=True))
        picked["black_border"] = black
    inner_w = _even(out_w - 2 * black) if black else out_w
    inner_h = _even(out_h - 2 * black) if black else out_h

    pix_fmt = "nv12" if (settings.encoder or "") in MF_ENCODERS else "yuv420p"

    filter_complex: list[str] = []
    head = "[0:v]" + (",".join(chain) if chain else "null")

    if settings.on("blur_border"):
        depth = max(0, _pick(rnd, settings, "blur_border", integer=True))
        picked["blur_border"] = depth
        fg_h = _even(max(2, inner_h - 2 * depth))
        filter_complex.append(f"{head},split=2[bgsrc][fgsrc]")
        filter_complex.append(
            f"[bgsrc]scale={inner_w}:{inner_h}:force_original_aspect_ratio=increase,"
            f"crop={inner_w}:{inner_h},boxblur=luma_radius={max(2, depth // 4)}:luma_power=2[bg]"
        )
        filter_complex.append(
            f"[fgsrc]scale={inner_w}:{fg_h}:force_original_aspect_ratio=decrease[fg]"
        )
        filter_complex.append("[bg][fg]overlay=(W-w)/2:(H-h)/2[inner]")
    else:
        filter_complex.append(
            f"{head},scale={inner_w}:{inner_h}:force_original_aspect_ratio=decrease,"
            f"pad={inner_w}:{inner_h}:(ow-iw)/2:(oh-ih)/2:black[inner]"
        )

    if black:
        filter_complex.append(
            f"[inner]pad={out_w}:{out_h}:{black}:{black}:black,setsar=1,format={pix_fmt}[vout]"
        )
    else:
        filter_complex.append(f"[inner]setsar=1,format={pix_fmt}[vout]")

    audio_chain: list[str] = []
    if media.has_audio:
        audio_chain.append(f"aresample={AUDIO_RATE}")
        if settings.on("wave_shift"):
            permille = max(0.0, _pick(rnd, settings, "wave_shift"))
            picked["wave_shift"] = permille
            factor = 1.0 + permille / 1000.0
            if factor > 1.0001:
                audio_chain.append(f"asetrate={int(AUDIO_RATE * factor)}")
                audio_chain.append(f"aresample={AUDIO_RATE}")
                audio_chain.append(f"atempo={1 / factor:.6f}")
        if speed is not None:
            audio_chain.append(f"atempo={speed:.6f}")
        if settings.on("volume"):
            volume = max(0.0, _pick(rnd, settings, "volume"))
            picked["volume"] = volume
            audio_chain.append(f"volume={volume:.5f}")
        audio_chain.append(f"aformat=sample_rates={AUDIO_RATE}:channel_layouts=stereo")
        filter_complex.append("[0:a]" + ",".join(audio_chain) + "[aout]")

    args: list[str] = [ffmpeg, "-hide_banner", "-nostdin", "-y"]
    threads = settings.thread_limit()
    if threads:
        args += ["-threads", str(threads), "-filter_threads", str(threads)]
    if start > 0:
        args += ["-ss", f"{start:.3f}"]
    if length > 0:
        args += ["-t", f"{length:.3f}"]
    args += ["-i", media.path]

    args += ["-filter_complex", ";".join(filter_complex), "-map", "[vout]"]
    if media.has_audio:
        args += ["-map", "[aout]"]
    else:
        args += ["-an"]

    encoder = settings.encoder or "libx264"
    args += ["-c:v", encoder]
    args += _encoder_quality_args(encoder, settings.x264_preset)

    if settings.on("vbitrate"):
        kbps = max(200, _pick(rnd, settings, "vbitrate", integer=True))
        picked["vbitrate"] = kbps
        args += [
            "-b:v", f"{kbps}k",
            "-maxrate", f"{int(kbps * 1.3)}k",
            "-bufsize", f"{int(kbps * 2)}k",
        ]
    else:
        args += ["-crf", "20"] if encoder == CPU_ENCODER else ["-b:v", "10000k"]

    if settings.on("framerate"):
        fps = max(1, _pick(rnd, settings, "framerate", integer=True))
        picked["framerate"] = fps
        args += ["-r", str(fps)]

    args += ["-pix_fmt", pix_fmt]

    if media.has_audio:
        abitrate = 192
        if settings.on("abitrate"):
            abitrate = max(32, _pick(rnd, settings, "abitrate", integer=True))
            picked["abitrate"] = abitrate
        args += ["-c:a", "aac", "-b:a", f"{abitrate}k", "-ar", str(AUDIO_RATE), "-ac", "2"]

    args += ["-map_metadata", "-1", "-map_chapters", "-1"]
    if settings.on("us_metadata"):
        meta = _us_metadata(rnd)
        picked["us_metadata"] = f"{meta['make']} {meta['model']}"
        for key, value in meta.items():
            args += ["-metadata", f"{key}={value}"]
        args += ["-metadata:s:v:0", f"handler_name={rnd.choice(['Core Media Video', 'VideoHandler', 'ISO Media file'])}"]
        if media.has_audio:
            args += ["-metadata:s:a:0", f"handler_name={rnd.choice(['Core Media Audio', 'SoundHandler'])}"]
        args += ["-video_track_timescale", str(rnd.choice(_TIMESCALES))]

    movflags = "+faststart+use_metadata_tags" if settings.on("us_metadata") else "+faststart"
    args += ["-movflags", movflags, output_path]

    out_len = length if length > 0 else duration
    if speed:
        out_len = out_len / speed
    return Job(args=args, output=output_path, picked=picked, duration=max(0.0, out_len))


def _encoder_quality_args(encoder: str, preset: str) -> list[str]:
    if encoder == CPU_ENCODER:
        return ["-preset", preset]
    if encoder == "h264_nvenc":
        return ["-preset", "p5", "-rc", "vbr"]
    if encoder == "h264_qsv":
        return ["-preset", "medium"]
    if encoder == "h264_amf":
        return ["-quality", "balanced"]
    if encoder in MF_ENCODERS:
        return ["-hw_encoding", "true"]
    return []


def output_name(src: str, index: int, total: int, folder: str) -> str:
    stem = Path(src).stem
    width = max(2, len(str(total)))
    candidate = Path(folder) / f"{stem}_uq{index:0{width}d}.mp4"
    counter = 1
    while candidate.exists():
        candidate = Path(folder) / f"{stem}_uq{index:0{width}d}_{counter}.mp4"
        counter += 1
    return str(candidate)


def describe(picked: dict[str, object]) -> str:
    if not picked:
        return "без изменений"
    return "  ".join(f"{k}={v}" for k, v in picked.items())
