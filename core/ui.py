from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from . import presets as presets_store
from . import theme
from .config import (
    APP_NAME, APP_VERSION, CPU_ENCODER, DEFAULT_MODE, GPU_ENCODERS, MODE_HINTS,
    PARAM_SPECS, PROCESSING_MODES,
)
from .ffmpeg_utils import (
    VIDEO_EXTENSIONS, encoder_available, ffmpeg_path, ffprobe_path,
)
from .pipeline import Settings
from .worker import BatchRequest, BatchWorker


class _NoWheel:

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class SpinBox(_NoWheel, QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


class DoubleSpinBox(_NoWheel, QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


class ComboBox(_NoWheel, QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


class ParamCard(QFrame):

    def __init__(self, spec: dict, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.key = spec["key"]
        self.kind = spec["kind"]
        self.setObjectName("Card")
        self.setProperty("on", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 9)
        layout.setSpacing(5)

        self.checkbox = QCheckBox(spec["title"])
        self.checkbox.setToolTip(spec["hint"])
        self.checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self.checkbox)

        hint = QLabel(spec["hint"])
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        hint.setMinimumHeight(24)
        layout.addWidget(hint)

        self.fields: list[QWidget] = []
        row = QHBoxLayout()
        row.setSpacing(6)

        if self.kind in ("range_f", "range_i"):
            self.lo_field = self._make_number(spec, spec["min"])
            self.hi_field = self._make_number(spec, spec["max"])
            row.addWidget(self._tag("min"))
            row.addWidget(self.lo_field, 1)
            row.addWidget(self._tag("max"))
            row.addWidget(self.hi_field, 1)
            self.fields += [self.lo_field, self.hi_field]
        elif self.kind == "dims":
            self.w_field = SpinBox()
            self.w_field.setRange(16, 7680)
            self.w_field.setValue(spec["width"])
            self.h_field = SpinBox()
            self.h_field.setRange(16, 7680)
            self.h_field.setValue(spec["height"])
            row.addWidget(self.w_field, 1)
            row.addWidget(self._tag("×"))
            row.addWidget(self.h_field, 1)
            self.fields += [self.w_field, self.h_field]
        else:
            placeholder = QLabel("вкл / выкл")
            placeholder.setObjectName("Hint")
            row.addWidget(placeholder)

        layout.addLayout(row)
        self._on_toggled(False)


    @staticmethod
    def _tag(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Hint")
        return label

    @staticmethod
    def _make_number(spec: dict, value: float) -> QWidget:
        if spec["kind"] == "range_i":
            box = SpinBox()
            box.setRange(int(spec["lo"]), int(spec["hi"]))
            box.setSingleStep(int(spec.get("step", 1)))
            box.setValue(int(value))
        else:
            box = DoubleSpinBox()
            box.setDecimals(int(spec.get("dec", 2)))
            box.setRange(float(spec["lo"]), float(spec["hi"]))
            box.setSingleStep(float(spec.get("step", 0.01)))
            box.setValue(float(value))
        if spec.get("suffix"):
            box.setSuffix(spec["suffix"])
        box.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        return box

    def _on_toggled(self, checked: bool) -> None:
        for field in self.fields:
            field.setEnabled(checked)
        self.setProperty("on", bool(checked))
        self.style().unpolish(self)
        self.style().polish(self)


    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, value: bool) -> None:
        self.checkbox.setChecked(bool(value))

    def get_values(self) -> dict:
        if self.kind in ("range_f", "range_i"):
            return {"min": self.lo_field.value(), "max": self.hi_field.value()}
        if self.kind == "dims":
            return {"width": self.w_field.value(), "height": self.h_field.value()}
        return {}

    def set_values(self, data: dict) -> None:
        if not data:
            return
        if self.kind in ("range_f", "range_i") and "min" in data:
            self.lo_field.setValue(type(self.lo_field.value())(data["min"]))
            self.hi_field.setValue(type(self.hi_field.value())(data["max"]))
        elif self.kind == "dims" and "width" in data:
            self.w_field.setValue(int(data["width"]))
            self.h_field.setValue(int(data["height"]))


class EncoderProbe(QThread):

    done = Signal(dict)

    def __init__(self, ffmpeg: str, encoders: list[str], parent=None):
        super().__init__(parent)
        self.ffmpeg = ffmpeg
        self.encoders = encoders

    def run(self) -> None:
        self.done.emit({e: encoder_available(self.ffmpeg, e) for e in self.encoders})


class FileList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(84)
        self.setMaximumHeight(118)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths: list[str] = []
        extensions = tuple(ext.lstrip("*") for ext in VIDEO_EXTENSIONS)
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                paths += [
                    str(child) for child in sorted(path.iterdir())
                    if child.suffix.lower() in extensions
                ]
            elif path.suffix.lower() in extensions:
                paths.append(str(path))
        window = self.window()
        if paths and hasattr(window, "add_files"):
            window.add_files(paths)
        event.acceptProposedAction()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(_app_icon())
        self.resize(1160, 820)
        self.setMinimumSize(920, 640)

        self.cards: dict[str, ParamCard] = {}
        self.worker: BatchWorker | None = None
        self._columns = 0
        self._status_text = "Готов к работе."
        self._percent = 0
        self._probe: EncoderProbe | None = None
        self._encoder_ok: dict[str, bool] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        root.addLayout(self._build_header())
        root.addWidget(self._build_notice())
        root.addWidget(self._build_files_panel())
        root.addWidget(self._build_params_toolbar())
        root.addWidget(self._build_params_area(), 1)
        root.addWidget(self._build_footer())

        self._apply_settings(presets_store.default_settings())
        self._check_ffmpeg()
        self._start_encoder_probe()


    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        column = QVBoxLayout()
        column.setSpacing(1)
        title = QLabel(APP_NAME)
        title.setObjectName("Title")
        subtitle = QLabel("Пакетная уникализация видео для TikTok, Reels и Shorts")
        subtitle.setObjectName("Subtitle")
        column.addWidget(title)
        column.addWidget(subtitle)
        row.addLayout(column)
        row.addStretch(1)

        self.ffmpeg_badge = QLabel()
        self.ffmpeg_badge.setObjectName("Badge")
        self.ffmpeg_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.ffmpeg_badge)
        return row

    def _build_notice(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Notice")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(11, 7, 11, 7)
        text = QLabel(
            "Каждая копия получает свой случайный набор значений из заданных диапазонов. "
            "Держите диапазоны узкими — тогда отличия остаются незаметными для зрителя."
        )
        text.setObjectName("NoticeText")
        text.setWordWrap(True)
        layout.addWidget(text)
        return frame

    def _build_files_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QLabel("Исходные видео")
        header.setObjectName("SectionTitle")
        layout.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(10)
        self.file_list = FileList()
        body.addWidget(self.file_list, 1)

        buttons = QVBoxLayout()
        buttons.setSpacing(6)
        for text, slot in (
            ("Добавить файлы", self._browse_files),
            ("Добавить папку", self._browse_folder),
            ("Убрать выбранные", self._remove_selected),
            ("Очистить список", self.file_list.clear),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            button.setMinimumWidth(130)
            buttons.addWidget(button)
        buttons.addStretch(1)
        body.addLayout(buttons)
        layout.addLayout(body)

        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        label = QLabel("Папка результата")
        label.setObjectName("SectionTitle")
        label.setMinimumWidth(112)
        self.output_field = QLineEdit()
        self.output_field.setPlaceholderText(r"например C:\Users\User\Downloads\output")
        self.output_field.setText(str(Path.home() / "Downloads" / "output"))
        browse = QPushButton("Обзор")
        browse.clicked.connect(self._browse_output)
        open_folder = QPushButton("Открыть")
        open_folder.clicked.connect(self._open_output)
        out_row.addWidget(label)
        out_row.addWidget(self.output_field, 1)
        out_row.addWidget(browse)
        out_row.addWidget(open_folder)
        layout.addLayout(out_row)
        return panel

    def _build_params_toolbar(self) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(8)

        title = QLabel("Параметры уникализации")
        title.setObjectName("SectionTitle")
        row.addWidget(title)
        row.addStretch(1)

        self.preset_combo = ComboBox()
        self.preset_combo.setMinimumWidth(220)
        self.preset_combo.activated.connect(self._apply_preset)
        self._reload_presets()
        row.addWidget(QLabel("Пресет:"))
        row.addWidget(self.preset_combo)

        save_preset = QPushButton("Сохранить пресет")
        save_preset.clicked.connect(self._save_preset)
        delete_preset = QPushButton("Удалить")
        delete_preset.clicked.connect(self._delete_preset)
        select_all = QPushButton("Отметить всё")
        select_all.clicked.connect(lambda: self._set_all(True))
        clear_all = QPushButton("Снять всё")
        clear_all.clicked.connect(lambda: self._set_all(False))
        for button in (save_preset, delete_preset, select_all, clear_all):
            row.addWidget(button)
        return widget

    def _build_params_area(self) -> QScrollArea:
        self.params_host = QWidget()
        self.params_grid = QGridLayout(self.params_host)
        self.params_grid.setContentsMargins(2, 2, 2, 2)
        self.params_grid.setHorizontalSpacing(8)
        self.params_grid.setVerticalSpacing(8)

        for spec in PARAM_SPECS:
            card = ParamCard(spec)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.cards[spec["key"]] = card

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(self.params_host)
        self._relayout_cards(3)
        return area

    def _build_footer(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(9)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(QLabel("Копий на видео:"))
        self.copies_spin = SpinBox()
        self.copies_spin.setRange(1, 999)
        self.copies_spin.setValue(10)
        self.copies_spin.setFixedWidth(80)
        row.addWidget(self.copies_spin)

        row.addSpacing(12)
        row.addWidget(QLabel("Режим:"))
        self.mode_combo = ComboBox()
        for label, value, _ in PROCESSING_MODES:
            self.mode_combo.addItem(label, value)
        self.mode_combo.setMinimumWidth(260)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        row.addWidget(self.mode_combo)

        self.mode_hint = QLabel()
        self.mode_hint.setObjectName("Hint")
        row.addWidget(self.mode_hint)

        row.addStretch(1)
        self.log_toggle = QPushButton("Показать лог")
        self.log_toggle.setObjectName("Ghost")
        self.log_toggle.setCheckable(True)
        self.log_toggle.toggled.connect(self._toggle_log)
        row.addWidget(self.log_toggle)
        layout.addLayout(row)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("Log")
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(118)
        self.log_view.hide()
        layout.addWidget(self.log_view)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.status_label = QLabel("Готов к работе.")
        self.status_label.setObjectName("Subtitle")
        actions.addWidget(self.status_label, 1)

        self.cancel_button = QPushButton("Стоп")
        self.cancel_button.setObjectName("Danger")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.setFixedWidth(84)
        actions.addWidget(self.cancel_button)

        self.generate_button = QPushButton("Сгенерировать копии")
        self.generate_button.setObjectName("Primary")
        self.generate_button.clicked.connect(self._start)
        self.generate_button.setMinimumWidth(190)
        actions.addWidget(self.generate_button)
        layout.addLayout(actions)
        return panel


    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.width()
        columns = 2 if width < 1050 else (3 if width < 1450 else 4)
        if columns != self._columns:
            self._relayout_cards(columns)

    def _relayout_cards(self, columns: int) -> None:
        self._columns = columns
        while self.params_grid.count():
            self.params_grid.takeAt(0)
        for index, spec in enumerate(PARAM_SPECS):
            self.params_grid.addWidget(
                self.cards[spec["key"]], index // columns, index % columns
            )
        for column in range(columns):
            self.params_grid.setColumnStretch(column, 1)


    def add_files(self, paths: list[str]) -> None:
        existing = {self.file_list.item(i).text() for i in range(self.file_list.count())}
        added = 0
        for path in paths:
            if path not in existing:
                self.file_list.addItem(path)
                existing.add(path)
                added += 1
        if added:
            self._log(f"[+] Добавлено файлов: {added}")

    def _browse_files(self) -> None:
        mask = "Видео (" + " ".join(VIDEO_EXTENSIONS) + ");;Все файлы (*.*)"
        paths, _ = QFileDialog.getOpenFileNames(self, "Выберите видео", str(Path.home()), mask)
        if paths:
            self.add_files(paths)

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Папка с видео", str(Path.home()))
        if not folder:
            return
        extensions = tuple(ext.lstrip("*") for ext in VIDEO_EXTENSIONS)
        found = [
            str(child) for child in sorted(Path(folder).iterdir())
            if child.is_file() and child.suffix.lower() in extensions
        ]
        if found:
            self.add_files(found)
        else:
            QMessageBox.information(self, APP_NAME, "В папке нет видеофайлов.")

    def _remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Папка для готовых копий", self.output_field.text() or str(Path.home())
        )
        if folder:
            self.output_field.setText(folder)

    def _open_output(self) -> None:
        folder = self.output_field.text().strip()
        if not folder:
            return
        Path(folder).mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open" if sys.platform != "darwin" else "open", folder])


    def _reload_presets(self) -> None:
        current = self.preset_combo.currentText()
        self.preset_combo.clear()
        self.preset_combo.addItem("— выбрать пресет —", None)
        for name in presets_store.BUILTIN_PRESETS:
            self.preset_combo.addItem(name, ("builtin", name))
        for name in sorted(presets_store.load_all()):
            self.preset_combo.addItem(f"★ {name}", ("user", name))
        index = self.preset_combo.findText(current)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)

    def _apply_preset(self) -> None:
        data = self.preset_combo.currentData()
        if not data:
            return
        kind, name = data
        if kind == "builtin":
            self._apply_settings(presets_store.builtin(name))
        else:
            stored = presets_store.load_all().get(name)
            if stored:
                self._apply_settings(Settings.from_dict(stored))
        self._log(f"[пресет] применён: {name}")

    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Сохранить пресет", "Название:")
        name = name.strip()
        if not ok or not name:
            return
        presets_store.save(name, self._collect_settings())
        self._reload_presets()
        self.preset_combo.setCurrentText(f"★ {name}")
        self._log(f"[пресет] сохранён: {name}")

    def _delete_preset(self) -> None:
        data = self.preset_combo.currentData()
        if not data or data[0] != "user":
            QMessageBox.information(
                self, APP_NAME, "Удалять можно только собственные пресеты (отмечены ★)."
            )
            return
        presets_store.delete(data[1])
        self._reload_presets()
        self._log(f"[пресет] удалён: {data[1]}")


    def _collect_settings(self) -> Settings:
        settings = Settings()
        for key, card in self.cards.items():
            settings.enabled[key] = card.is_checked()
            values = card.get_values()
            if values:
                settings.values[key] = values
        settings.mode = self.mode_combo.currentData() or DEFAULT_MODE
        settings.encoder = self._encoder_for_mode(settings.mode)
        return settings

    def _apply_settings(self, settings: Settings) -> None:
        for key, card in self.cards.items():
            card.set_values(settings.values.get(key, {}))
            card.set_checked(settings.enabled.get(key, False))
        index = self.mode_combo.findData(settings.mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
        self._on_mode_changed()

    def _encoder_for_mode(self, mode: str) -> str:
        """«Быстро» — лучший доступный кодировщик видеокарты, иначе процессор."""
        if mode != "fast":
            return CPU_ENCODER
        best = next((e for e in GPU_ENCODERS if self._encoder_ok.get(e)), None)
        return best or CPU_ENCODER

    def _on_mode_changed(self) -> None:
        mode = self.mode_combo.currentData() or DEFAULT_MODE
        hint = MODE_HINTS.get(mode, "")
        self.mode_combo.setToolTip(hint)
        self.mode_hint.setToolTip(hint)
        self.mode_hint.setText(self._mode_note(mode))

    def _mode_note(self, mode: str) -> str:
        if mode != "fast":
            return "процессор, libx264"
        if not self._encoder_ok:
            return "проверяю видеокарту…"
        encoder = self._encoder_for_mode(mode)
        if encoder == CPU_ENCODER:
            return "видеокарта недоступна — процессор"
        return f"видеокарта, {encoder}"

    def _set_all(self, value: bool) -> None:
        for card in self.cards.values():
            card.set_checked(value)


    def _check_ffmpeg(self) -> bool:
        exe, probe_exe = ffmpeg_path(), ffprobe_path()
        if exe and probe_exe:
            self.ffmpeg_badge.setText("● FFmpeg: найден")
            self.ffmpeg_badge.setToolTip(exe)
            return True
        self.ffmpeg_badge.setText("● FFmpeg: НЕ НАЙДЕН")
        self.ffmpeg_badge.setToolTip("Установите: winget install Gyan.FFmpeg")
        return False

    def _start_encoder_probe(self) -> None:
        exe = ffmpeg_path()
        if not exe:
            return
        self._probe = EncoderProbe(exe, list(GPU_ENCODERS), self)
        self._probe.done.connect(self._on_encoders_probed)
        self._probe.start()

    def _on_encoders_probed(self, availability: dict) -> None:
        self._encoder_ok = availability
        self._on_mode_changed()
        best = self._encoder_for_mode("fast")
        if best == CPU_ENCODER:
            self._log(
                "[режим] аппаратный кодировщик недоступен — «Быстро» будет "
                "работать на процессоре"
            )
        else:
            self._log(f"[режим] «Быстро» кодирует видеокартой ({best})")

    def _start(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        if not self._check_ffmpeg():
            QMessageBox.critical(
                self, APP_NAME,
                "FFmpeg не найден.\n\nУстановите его командой\n"
                "    winget install Gyan.FFmpeg\n\n"
                "либо положите ffmpeg.exe и ffprobe.exe в папку ffmpeg\\bin "
                "рядом с приложением и перезапустите программу.",
            )
            return

        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not files:
            QMessageBox.warning(self, APP_NAME, "Добавьте хотя бы одно видео.")
            return

        output_dir = self.output_field.text().strip()
        if not output_dir:
            QMessageBox.warning(self, APP_NAME, "Укажите папку для результата.")
            return
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, f"Не удалось создать папку:\n{exc}")
            return

        settings = self._collect_settings()
        if not any(settings.enabled.values()):
            QMessageBox.warning(self, APP_NAME, "Отметьте хотя бы один параметр уникализации.")
            return

        if not self._ensure_encoder(settings):
            return

        copies = self.copies_spin.value()
        request = BatchRequest(
            files=files, output_dir=output_dir, copies=copies,
            settings=settings, ffmpeg=ffmpeg_path(),
        )

        self.progress.setValue(0)
        self._log(f"=== Старт: {len(files)} файл(ов) × {copies} копий ===")

        self.worker = BatchWorker(request, self)
        self.worker.log.connect(self._log)
        self.worker.status.connect(self._set_status)
        self.worker.progress.connect(self._set_progress)
        self.worker.finished_batch.connect(self._on_finished)
        self.worker.start()

        self.generate_button.setEnabled(False)
        self.generate_button.setText("Обработка…")
        self.cancel_button.setEnabled(True)

    def _set_status(self, text: str) -> None:
        self._status_text = text
        self._refresh_status()

    def _set_progress(self, percent: int) -> None:
        self.progress.setValue(percent)
        self._percent = percent
        self._refresh_status()

    def _refresh_status(self) -> None:
        running = bool(self.worker and self.worker.isRunning())
        prefix = f"{self._percent}%  ·  " if running else ""
        self.status_label.setText(prefix + self._status_text)

    def _ensure_encoder(self, settings: Settings) -> bool:
        """Кодировщик видеокарты мог отвалиться после смены драйвера."""
        encoder = settings.encoder
        if encoder == CPU_ENCODER or encoder_available(ffmpeg_path(), encoder):
            return True
        self._encoder_ok[encoder] = False
        settings.encoder = self._encoder_for_mode(settings.mode)
        self._on_mode_changed()
        self._log(f"[режим] {encoder} недоступен, кодирую на процессоре")
        return True

    def _cancel(self) -> None:
        if self.worker and self.worker.isRunning():
            self.status_label.setText("Останавливаю…")
            self.worker.cancel()

    def _on_finished(self, ok: int, failed: int) -> None:
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Сгенерировать копии")
        self.cancel_button.setEnabled(False)
        self._refresh_status()
        self._log(f"=== Завершено. Успешно: {ok}, ошибок: {failed} ===")

    def _toggle_log(self, shown: bool) -> None:
        self.log_view.setVisible(shown)
        self.log_toggle.setText("Скрыть лог" if shown else "Показать лог")

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            answer = QMessageBox.question(
                self, APP_NAME, "Обработка ещё идёт. Прервать и закрыть?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(4000)
        if self._probe and self._probe.isRunning():
            self._probe.wait(15000)
        event.accept()


def _app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(theme.ACCENT))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
    font = painter.font()
    font.setPointSize(28)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "У")
    painter.end()
    return QIcon(pixmap)
