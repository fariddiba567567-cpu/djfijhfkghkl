from __future__ import annotations

APP_NAME = "Уникализатор видео"
APP_VERSION = "1.0.0"

PARAM_SPECS: list[dict] = [
    {
        "key": "framerate",
        "title": "Framerate",
        "kind": "range_i",
        "min": 25, "max": 50, "lo": 20, "hi": 120, "suffix": " fps",
        "hint": "Частота кадров итогового файла",
    },
    {
        "key": "vbitrate",
        "title": "Video Bitrate",
        "kind": "range_i",
        "min": 8000, "max": 14000, "lo": 500, "hi": 60000, "step": 500,
        "suffix": " kbps",
        "hint": "Целевой битрейт видеопотока",
    },
    {
        "key": "abitrate",
        "title": "Audio Bitrate",
        "kind": "range_i",
        "min": 128, "max": 320, "lo": 32, "hi": 512, "step": 16,
        "suffix": " kbps",
        "hint": "Битрейт аудиодорожки AAC",
    },
    {
        "key": "saturation",
        "title": "Saturation",
        "kind": "range_f",
        "min": 0.95, "max": 0.98, "lo": 0.0, "hi": 3.0, "step": 0.01, "dec": 3,
        "hint": "Насыщенность (eq=saturation)",
    },
    {
        "key": "crop",
        "title": "Random Crop",
        "kind": "range_f",
        "min": 1.0, "max": 5.0, "lo": 0.0, "hi": 25.0, "step": 0.5, "dec": 2,
        "suffix": " %",
        "hint": "Случайная обрезка краёв в процентах",
    },
    {
        "key": "contrast",
        "title": "Contrast",
        "kind": "range_f",
        "min": 1.10, "max": 1.50, "lo": 0.0, "hi": 3.0, "step": 0.01, "dec": 3,
        "hint": "Контраст (eq=contrast)",
    },
    {
        "key": "brightness",
        "title": "Brightness",
        "kind": "range_f",
        "min": 0.04, "max": 0.07, "lo": -1.0, "hi": 1.0, "step": 0.01, "dec": 3,
        "hint": "Смещение яркости (eq=brightness)",
    },
    {
        "key": "vignette",
        "title": "Vignette",
        "kind": "range_f",
        "min": 0.25, "max": 0.60, "lo": 0.0, "hi": 1.5, "step": 0.05, "dec": 3,
        "hint": "Угол виньетирования в радианах",
    },
    {
        "key": "gamma",
        "title": "Gamma",
        "kind": "range_f",
        "min": 1.10, "max": 1.30, "lo": 0.1, "hi": 3.0, "step": 0.01, "dec": 3,
        "hint": "Гамма-коррекция (eq=gamma)",
    },
    {
        "key": "lens",
        "title": "Lens Correction",
        "kind": "range_f",
        "min": 0.008, "max": 0.019, "lo": -0.2, "hi": 0.2, "step": 0.001, "dec": 4,
        "hint": "Дисторсия объектива (lenscorrection k1)",
    },
    {
        "key": "speed",
        "title": "Speed",
        "kind": "range_f",
        "min": 1.03, "max": 1.15, "lo": 0.5, "hi": 2.0, "step": 0.01, "dec": 3,
        "suffix": " x",
        "hint": "Скорость воспроизведения (видео + аудио)",
    },
    {
        "key": "zoom",
        "title": "Zoom",
        "kind": "range_f",
        "min": 1.03, "max": 1.10, "lo": 1.0, "hi": 2.0, "step": 0.01, "dec": 3,
        "suffix": " x",
        "hint": "Приближение кадра с сохранением размера",
    },
    {
        "key": "noise",
        "title": "Noise",
        "kind": "range_i",
        "min": 5, "max": 7, "lo": 0, "hi": 60,
        "hint": "Зернистость (noise=alls)",
    },
    {
        "key": "wave_shift",
        "title": "Waveform Shift",
        "kind": "range_f",
        "min": 6.0, "max": 7.0, "lo": 0.0, "hi": 60.0, "step": 0.5, "dec": 2,
        "suffix": " ‰",
        "hint": "Сдвиг тона аудио в промилле (длительность сохраняется)",
    },
    {
        "key": "pixel_shift",
        "title": "Pixel Shift",
        "kind": "range_f",
        "min": 3.5, "max": 5.2, "lo": 0.0, "hi": 40.0, "step": 0.1, "dec": 2,
        "suffix": " px",
        "hint": "Смещение содержимого кадра на несколько пикселей",
    },
    {
        "key": "volume",
        "title": "Volume",
        "kind": "range_f",
        "min": 1.30, "max": 1.50, "lo": 0.0, "hi": 4.0, "step": 0.05, "dec": 3,
        "suffix": " x",
        "hint": "Усиление громкости",
    },
    {
        "key": "dimensions",
        "title": "Dimensions",
        "kind": "dims",
        "width": 1080, "height": 1920,
        "hint": "Фиксированное разрешение на выходе",
    },
    {
        "key": "random_size",
        "title": "Random Pixel Size",
        "kind": "toggle",
        "hint": "Случайное разрешение в пределах 9:16 (перебивает Dimensions)",
    },
    {
        "key": "cut_start",
        "title": "Cut Video",
        "kind": "range_f",
        "min": 0.1, "max": 1.0, "lo": 0.0, "hi": 30.0, "step": 0.1, "dec": 2,
        "suffix": " с",
        "hint": "Обрезка с начала ролика",
    },
    {
        "key": "cut_end",
        "title": "Cut End Video",
        "kind": "range_f",
        "min": 0.2, "max": 1.0, "lo": 0.0, "hi": 30.0, "step": 0.1, "dec": 2,
        "suffix": " с",
        "hint": "Обрезка с конца ролика",
    },
    {
        "key": "rotation",
        "title": "Rotation",
        "kind": "range_f",
        "min": 0.9, "max": 1.6, "lo": -15.0, "hi": 15.0, "step": 0.1, "dec": 2,
        "suffix": " °",
        "hint": "Поворот кадра с автообрезкой чёрных углов",
    },
    {
        "key": "flip",
        "title": "Flip",
        "kind": "toggle",
        "hint": "Горизонтальное отражение кадра",
    },
    {
        "key": "us_metadata",
        "title": "US Metadata",
        "kind": "toggle",
        "hint": "Очистка метаданных и подстановка случайных US-тегов",
    },
    {
        "key": "blur_border",
        "title": "Blurred Border",
        "kind": "range_i",
        "min": 120, "max": 200, "lo": 0, "hi": 600, "step": 10, "suffix": " px",
        "hint": "Размытая подложка сверху и снизу",
    },
    {
        "key": "black_border",
        "title": "Black Border",
        "kind": "range_i",
        "min": 10, "max": 35, "lo": 0, "hi": 300, "suffix": " px",
        "hint": "Чёрная рамка по периметру",
    },
]

PARAM_BY_KEY = {spec["key"]: spec for spec in PARAM_SPECS}

DEFAULT_ENABLED = {
    "framerate", "vbitrate", "abitrate", "saturation", "contrast",
    "brightness", "gamma", "noise", "speed", "zoom", "us_metadata",
}

CPU_ENCODER = "libx264"

MF_ENCODERS = ("h264_mf", "hevc_mf")

GPU_ENCODERS = ("h264_mf", "h264_nvenc", "h264_qsv", "h264_amf")

DEFAULT_MODE = "fast"

PROCESSING_MODES = [
    (
        "Быстро — кодирует видеокарта",
        "fast",
        "Кодирует встроенный чип видеокарты, процессор почти свободен.\n"
        "Обычно в 2 раза быстрее. Если аппаратного кодировщика нет,\n"
        "программа сама переключится на процессор.",
    ),
    (
        "Качество — кодирует процессор",
        "quality",
        "Кодек libx264 на процессоре: файл компактнее при той же картинке.\n"
        "Обработка дольше, процессор загружен полностью.",
    ),
    (
        "Фоновый — не мешает работать за ПК",
        "background",
        "Половина ядер и пониженный приоритет: обработка идёт дольше,\n"
        "зато компьютером можно спокойно пользоваться.",
    ),
]

MODE_HINTS = {value: hint for _, value, hint in PROCESSING_MODES}
