"""
Background download tracker for ISO images.

Provides non-blocking ISO downloads with real-time progress reporting.
Uses directory scanning (not in-memory state) so progress survives Flask restarts.
"""

from __future__ import annotations

import subprocess
import threading
import time
import os
from pathlib import Path
from typing import Optional

# Known ISO sizes (in bytes) for progress percentage calculation.
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


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def start_iso_download(os_category: str, os_version: str, iso_path: str, cwd: str) -> str:
    """
    Start a quickget download in a background thread and return a task_id.
    The download is identified by os_version (e.g. 'ubuntu-24.04').
    """
    from .os_catalog import quickemu_os_release

    mapping = quickemu_os_release(os_version)
    if not mapping:
        raise ValueError(f"No quickemu download for: {os_version}")

    qemu_os, qemu_release = mapping

    cmd = ["quickget", "--download", qemu_os]
    if qemu_release:
        cmd.append(qemu_release)

    task_id = os_version
    total_size = KNOWN_SIZES.get(os_version, 0)
    start_time = time.time()

    # Record start time in a marker file so we can re-detect after Flask restart
    marker = Path(cwd) / f".download_{task_id}.start"

    # Guard against duplicate downloads: if a marker already exists and curl
    # for this ISO is still running, skip launching a second quickget.
    if marker.exists():
        existing_start = float(marker.read_text())
        # Check if the download is still active (curl running with same ISO name)
        iso_basename = Path(iso_path).name
        running = os.popen(f"ps aux | grep '[c]url.*{iso_basename}'").read().strip()
        if running:
            return task_id  # already downloading, reuse existing task
        # Stale marker from a previous crashed session — remove it
        marker.unlink(missing_ok=True)

    marker.write_text(str(start_time))

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
        proc.wait()
        marker.unlink(missing_ok=True)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return task_id


def get_download_progress(task_id: str) -> Optional[dict]:
    """
    Return the current progress for a download task.

    Detects progress by:
    1. Looking for a marker file left by start_iso_download, OR
    2. Scanning the ISO_DIR for any recently-modified .iso file

    This approach works even after Flask restarts.
    """
    from .config import ISO_DIR

    # Try to find a start-time marker for this task
    marker = Path(ISO_DIR) / f".download_{task_id}.start"
    start_time: float
    if marker.exists():
        start_time = float(marker.read_text())
        status = "downloading"
    else:
        # No marker — check if there's a recently modified .iso file
        # that might belong to this task (within last 2 hours)
        two_hours_ago = time.time() - 7200
        candidates = []
        for f in Path(ISO_DIR).glob("*.iso"):
            if f.stat().st_mtime >= two_hours_ago:
                candidates.append(f)
        if candidates:
            # Use the oldest candidate as the one we're tracking
            start_time = min(f.stat().st_mtime for f in candidates)
            status = "downloading"
        else:
            return None

    total_size = KNOWN_SIZES.get(task_id, 0)

    # Find the newest .iso file modified at or after start_time
    isos = sorted(
        (f for f in Path(ISO_DIR).glob("*.iso") if f.stat().st_mtime >= start_time - 1),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    current_size = 0
    actual_path = None
    if isos:
        actual_path = str(isos[0])
        current_size = isos[0].stat().st_size

    progress = min(int(current_size / total_size * 100), 100) if total_size else 0

    # Check if curl is still running for this ISO
    curl_running = False
    if actual_path:
        for line in os.popen(f"ps aux | grep curl | grep '{os.path.basename(actual_path)}' | grep -v grep"):
            curl_running = True
            break

    if not curl_running and current_size > 0:
        # curl finished; check if we have a complete file
        if total_size == 0 or current_size >= total_size * 0.99:
            status = "complete"
            progress = 100
        else:
            status = "error"
    else:
        status = "downloading"

    return {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "downloaded": current_size,
        "total": total_size,
        "downloaded_human": _human_size(current_size),
        "total_human": _human_size(total_size) if total_size else "unknown",
        "iso_path": actual_path,
    }
