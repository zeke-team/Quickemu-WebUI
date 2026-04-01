"""
Background download tracker for ISO images.

Provides non-blocking ISO downloads with real-time progress reporting
by monitoring the target file size against a known total size.

Architecture:
    1. start_iso_download(os_version) → task_id
       Spawns quickget in a subprocess and tracks the expected output path.

    2. get_download_progress(task_id) → {status, progress, speed, downloaded, total}
       Called by the frontend poll endpoint; reads current file size and
       computes a human-readable progress snapshot.
"""

from __future__ import annotations

import subprocess
import threading
import time
import os
import re
from pathlib import Path
from typing import Optional

# Known ISO sizes (in bytes) for progress percentage calculation.
# Sizes are approximate; a missing entry falls back to file-growth tracking.
KNOWN_SIZES: dict[str, int] = {
    "ubuntu-24.04": 5_500_000_000,
    "ubuntu-22.04": 4_500_000_000,
    "ubuntu-20.04": 3_500_000_000,
    "fedora-41":    2_200_000_000,
    "fedora-40":    2_000_000_000,
    "debian-12":    2_800_000_000,
    "debian-11":    3_700_000_000,
    "archlinux":      950_000_000,
    "linuxmint-21": 2_600_000_000,
    "opensuse-15":  1_800_000_000,
    "almalinux-9":  2_500_000_000,
    "rockylinux-9": 2_300_000_000,
    "windows-11":    7_000_000_000,
    "windows-10":    6_000_000_000,
}

# Active download tasks: task_id → dict
_tasks: dict[str, dict] = {}
_tasks_lock = threading.Lock()


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _monitor_file(task_id: str, file_path: Path, total_size: int, poll_interval: float = 1.0):
    """
    Monitor file_path growth and update the shared task dict.
    Runs in a background thread until the file reaches total_size
    or the task is marked cancelled/complete.
    """
    last_size = 0
    last_time = time.time()
    speed_bps = 0.0

    while True:
        time.sleep(poll_interval)

        with _tasks_lock:
            task = _tasks.get(task_id)
            if task is None or task.get("done") or task.get("cancelled"):
                break

        if not file_path.exists():
            continue

        try:
            current_size = file_path.stat().st_size
        except OSError:
            current_size = 0

        now = time.time()
        elapsed = now - last_time
        if elapsed > 0 and current_size > last_size:
            speed_bps = (current_size - last_size) / elapsed

        progress = min(int(current_size / total_size * 100), 100) if total_size else 0

        with _tasks_lock:
            if task_id in _tasks:
                _tasks[task_id].update(
                    {
                        "downloaded": current_size,
                        "total": total_size,
                        "progress": progress,
                        "speed": speed_bps,
                        "speed_human": f"{_human_size(int(speed_bps))}/s",
                    }
                )

        last_size = current_size
        last_time = now

        if current_size >= total_size:
            with _tasks_lock:
                if task_id in _tasks:
                    _tasks[task_id]["progress"] = 100
                    _tasks[task_id]["done"] = True
            break


def start_iso_download(os_category: str, os_version: str, iso_path: str, cwd: str) -> str:
    """
    Start a quickget download in a background thread and return a task_id.

    The subprocess runs ``quickget --download <os> <release>`` in cwd.
    A background monitor thread tracks the growing ISO file and updates
    progress in the shared _tasks dict.

    Returns:
        A short task_id string used to poll progress.
    """
    from .os_catalog import quickemu_os_release

    mapping = quickemu_os_release(os_version)
    if not mapping:
        raise ValueError(f"No quickemu download for: {os_version}")

    qemu_os, qemu_release = mapping

    cmd = ["quickget", "--download", qemu_os]
    if qemu_release:
        cmd.append(qemu_release)

    task_id = os_version  # simple: one active download per os_version at a time

    iso_file = Path(iso_path)
    total_size = KNOWN_SIZES.get(os_version, 0)

    with _tasks_lock:
        _tasks[task_id] = {
            "task_id": task_id,
            "status": "downloading",
            "progress": 0,
            "downloaded": 0,
            "total": total_size,
            "speed": 0.0,
            "speed_human": "0 B/s",
            "done": False,
            "cancelled": False,
            "iso_path": iso_path,
            "error": None,
        }

    def run():
        env = os.environ.copy()
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        with _tasks_lock:
            if task_id in _tasks:
                _tasks[task_id]["pid"] = proc.pid

        # Stream output to capture potential errors
        output_lines = []
        for line in proc.stdout:
            output_lines.append(line.rstrip())

        proc.wait()

        with _tasks_lock:
            if task_id in _tasks:
                if proc.returncode == 0:
                    # Scan ISO_DIR for the newest file matching this OS
                    from .config import ISO_DIR
                    isos = sorted(
                        (f for f in ISO_DIR.glob("*.iso") if f.is_file()),
                        key=lambda f: f.stat().st_mtime,
                        reverse=True,
                    )
                    if isos:
                        _tasks[task_id]["iso_path"] = str(isos[0])
                    _tasks[task_id]["done"] = True
                    _tasks[task_id]["status"] = "complete"
                else:
                    _tasks[task_id]["done"] = True
                    _tasks[task_id]["status"] = "error"
                    _tasks[task_id]["error"] = "\n".join(output_lines[-5:])

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    # Start file-size monitor if we know the total size
    if total_size:
        monitor = threading.Thread(
            target=_monitor_file,
            args=(task_id, iso_file, total_size),
            daemon=True,
        )
        monitor.start()

    return task_id


def get_download_progress(task_id: str) -> Optional[dict]:
    """Return the current progress dict for a task_id, or None if not found."""
    with _tasks_lock:
        task = _tasks.get(task_id)
        if not task:
            return None
        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "progress": task["progress"],
            "downloaded": task["downloaded"],
            "total": task["total"],
            "downloaded_human": _human_size(task["downloaded"]),
            "total_human": _human_size(task["total"]) if task["total"] else "unknown",
            "speed_human": task["speed_human"],
            "iso_path": task["iso_path"],
            "error": task.get("error"),
        }
