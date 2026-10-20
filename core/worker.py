from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .ffmpeg_utils import CREATE_NO_WINDOW, MediaInfo, probe
from .pipeline import Job, Settings, build_job, describe, output_name


if sys.platform == "win32":
    _BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
else:
    _BELOW_NORMAL_PRIORITY_CLASS = 0


def priority_flag(mode: str) -> int:
    return _BELOW_NORMAL_PRIORITY_CLASS if mode == "background" else 0


@dataclass
class BatchRequest:
    files: list[str]
    output_dir: str
    copies: int
    settings: Settings
    ffmpeg: str


class BatchWorker(QThread):

    log = Signal(str)
    status = Signal(str)
    progress = Signal(int)
    copy_done = Signal(str)
    finished_batch = Signal(int, int)

    def __init__(self, request: BatchRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self._cancelled = False
        self._process: subprocess.Popen | None = None

    def cancel(self) -> None:
        self._cancelled = True
        process = self._process
        if process and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass


    def run(self) -> None:
        req = self.request
        total_jobs = max(1, len(req.files) * req.copies)
        done_jobs = 0
        ok = failed = 0
        started = time.monotonic()

        for path in req.files:
            if self._cancelled:
                break
            try:
                media: MediaInfo = probe(path)
            except Exception as exc:
                failed += req.copies
                done_jobs += req.copies
                self.log.emit(f"[ОШИБКА] {path}: {exc}")
                self.progress.emit(int(done_jobs / total_jobs * 100))
                continue

            self.log.emit(
                f"[ФАЙЛ] {path}  ({media.width}x{media.height}, "
                f"{media.duration:.1f} с, звук: {'есть' if media.has_audio else 'нет'})"
            )

            for index in range(1, req.copies + 1):
                if self._cancelled:
                    break
                target = output_name(path, index, req.copies, req.output_dir)
                seed = hash((path, index, time.time_ns())) & 0xFFFFFFFF
                job = build_job(media, req.settings, target, req.ffmpeg, seed=seed)

                self.status.emit(f"Копия {index}/{req.copies} — {Path(target).name}")
                self.log.emit(f"  #{index}: {describe(job.picked)}")

                success, message = self._run_job(job, done_jobs, total_jobs)
                done_jobs += 1
                if success:
                    ok += 1
                    self.copy_done.emit(job.output)
                else:
                    failed += 1
                    self.log.emit(f"  [ОШИБКА] копия #{index}: {message}")
                self.progress.emit(int(done_jobs / total_jobs * 100))

        elapsed = time.monotonic() - started
        if self._cancelled:
            self.status.emit(f"Остановлено. Готово: {ok}, ошибок: {failed}.")
        else:
            self.progress.emit(100)
            self.status.emit(
                f"Готово: {ok} из {total_jobs} за {elapsed:.0f} с"
                + (f", ошибок: {failed}" if failed else "")
            )
        self.finished_batch.emit(ok, failed)


    def _run_job(self, job: Job, done_jobs: int, total_jobs: int) -> tuple[bool, str]:
        args = list(job.args)
        args[1:1] = ["-nostats", "-loglevel", "error", "-progress", "pipe:1"]

        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_NO_WINDOW | priority_flag(self.request.settings.mode),
            )
        except OSError as exc:
            return False, str(exc)

        assert self._process.stdout is not None
        for line in self._process.stdout:
            if self._cancelled:
                break
            if line.startswith("out_time_ms=") and job.duration > 0:
                try:
                    seconds = int(line.split("=", 1)[1]) / 1_000_000
                except ValueError:
                    continue
                share = min(1.0, max(0.0, seconds / job.duration))
                overall = (done_jobs + share) / total_jobs * 100
                self.progress.emit(int(overall))

        self._process.wait()
        stderr = (self._process.stderr.read() if self._process.stderr else "") or ""
        code = self._process.returncode
        self._process = None

        if self._cancelled:
            return False, "отменено пользователем"
        if code != 0:
            tail = " ".join(stderr.strip().splitlines()[-3:])
            return False, tail or f"ffmpeg завершился с кодом {code}"
        return True, ""
