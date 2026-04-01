"""
VM lifecycle manager.

Provides high-level VM operations: create, delete, start, stop, reboot, list.
Manages VM configuration files (JSON) stored in ~/.webvm/vms/ and coordinates
with QEMURunner for process management.

Each VM has:
    <name>.json   — VM configuration
    <name>.qcow2  — VM disk image
    <name>.pid    — QEMU daemon PID (only while running)
    <name>-qmp.sock — QMP control socket (only while running)
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional

from .config import VM_DIR, ISO_DIR, QEMU_IMG_BIN, VNC_BASE_PORT
from .qemu_runner import QEMURunner
from .os_catalog import quickemu_os_release


class VMManager:
    """
    Manages the full lifecycle of VMs: creation, deletion, start, stop, reboot.

    VM configurations are stored as individual JSON files in VM_DIR, one per VM.
    This flat-file approach avoids a database dependency and makes it easy to
    inspect or edit VM configs manually.
    """

    def __init__(self):
        """Ensure VM and ISO storage directories exist."""
        VM_DIR.mkdir(parents=True, exist_ok=True)
        ISO_DIR.mkdir(parents=True, exist_ok=True)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _vm_path(self, name: str) -> Path:
        """Path to the VM configuration JSON file."""
        return VM_DIR / f"{name}.json"

    def _disk_path(self, name: str) -> Path:
        """Path to the VM's qcow2 disk image."""
        return VM_DIR / f"{name}.qcow2"

    def _get_vnc_port(self) -> int:
        """
        Allocate an unused VNC port.

        Scans existing VM configs to find the highest used port, then returns
        the next available one starting from VNC_BASE_PORT (5930).
        This avoids port conflicts when many VMs are running simultaneously.
        """
        used = set()
        for f in VM_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if port := data.get("vnc_port"):
                    used.add(port)
            except Exception:
                pass
        port = VNC_BASE_PORT
        while port in used:
            port += 1
        return port

    # ── ISO downloading via quickemu quickget ─────────────────────────────

    def download_iso(self, os_category: str, os_version: str) -> str:
        """
        Download an OS ISO image using quickemu's quickget.

        Runs ``quickget --download <os> <release>`` in the ISO_DIR directory
        and waits for the download to complete.

        Args:
            os_category: OS family (e.g. "linux", "windows", "macos").
            os_version:   OS version ID (e.g. "ubuntu-24.04").

        Returns:
            Absolute path to the downloaded ISO file.

        Raises:
            RuntimeError: If quickget fails or the OS is not supported.
        """
        mapping = quickemu_os_release(os_version)
        if not mapping:
            raise RuntimeError(
                f"No quickemu download available for OS version: {os_version}"
            )
        qemu_os, qemu_release = mapping

        cmd = ["quickget", "--download", qemu_os]
        if qemu_release:
            cmd.append(qemu_release)

        result = subprocess.run(
            cmd,
            cwd=str(ISO_DIR),
            capture_output=True,
            text=True,
            timeout=3600,  # up to 1 hour for large downloads
        )
        if result.returncode != 0:
            raise RuntimeError(f"quickget failed: {result.stderr.strip()}")

        # quickget prints "Downloading <OS>..." and saves the ISO in CWD.
        # Heuristic: find the newest .iso file in ISO_DIR that is older than
        # this invocation (avoids matching ISOs from previous downloads).
        isos = sorted(
            (f for f in ISO_DIR.glob("*.iso") if f.is_file()),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not isos:
            raise RuntimeError(
                f"quickget completed but no .iso found in {ISO_DIR}"
            )
        return str(isos[0])

    # ── CRUD ───────────────────────────────────────────────────────────────

    def list_vms(self) -> list[dict]:
        """
        List all VMs with their current status.

        Returns:
            List of VM config dicts, each augmented with a "status" field:
            "running" | "stopped".
        """
        vms = []
        for f in sorted(VM_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                runner = QEMURunner(data["name"], data)
                data["status"] = "running" if runner.is_running() else "stopped"
                data["vnc_ws_port"] = runner.get_vnc_websocket_port()
                vms.append(data)
            except Exception:
                pass
        return vms

    def get_vm(self, name: str) -> Optional[dict]:
        """
        Get a single VM's configuration and current status.

        Args:
            name: VM name.

        Returns:
            VM config dict with "status" field, or None if not found.
        """
        path = self._vm_path(name)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        runner = QEMURunner(name, data)
        data["status"] = "running" if runner.is_running() else "stopped"
        data["vnc_ws_port"] = runner.get_vnc_websocket_port()
        return data

    def create_vm(
        self,
        name: str,
        os_category: str,
        os_version: str,
        iso_path: str = "",
        disk_size: str = "64G",
        ram: str = "4096",
        vcpu: int = 2,
        boot: str = "cd",
    ) -> dict:
        """
        Create a new VM definition and allocate its disk image.

        Creates a qcow2 disk image using qemu-img, writes the JSON config,
        and stores everything in VM_DIR.  If no ISO path is provided, the OS
        image is automatically downloaded via ``quickget --download``.

        The download runs asynchronously in the background and can be polled
        via get_download_progress(). The VM config is written immediately so it
        appears in the dashboard; its iso_path is updated in-place once the
        download finishes.

        Args:
            name: Unique VM identifier.
            os_category: OS family (linux, windows, macos, other).
            os_version: Specific release (e.g. ubuntu-24.04, windows-11).
            iso_path: Path to installation ISO (optional; downloaded if empty).
            disk_size: Disk image size (e.g. "64G", "128G").
            ram: RAM in MB.
            vcpu: Number of virtual CPUs.
            boot: Boot device — "cd" (from ISO) or "disk".

        Returns:
            A dict with the VM config plus a "download_task_id" field when
            an ISO download was started.

        Raises:
            FileExistsError: If a VM with this name already exists.
            RuntimeError: If qemu-img fails.
        """
        if self._vm_path(name).exists():
            raise FileExistsError(f"VM '{name}' already exists")

        vnc_port = self._get_vnc_port()
        disk = str(self._disk_path(name))

        # Allocate qcow2 disk image with specified size
        result = subprocess.run(
            [QEMU_IMG_BIN, "create", "-f", "qcow2", disk, disk_size],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"qemu-img failed: {result.stderr}")

        # Determine ISO path: use provided path, or start background download
        download_task_id = None
        actual_iso_path = iso_path

        if not iso_path:
            # Write config with empty iso for now; iso_path is updated post-download
            config = {
                "name": name,
                "os_category": os_category,
                "os_version": os_version,
                "iso": "",
                "disk": disk,
                "disk_size": disk_size,
                "ram": ram,
                "vcpu": vcpu,
                "boot": boot,
                "vnc_port": vnc_port,
                "status": "stopped",
            }
            self._vm_path(name).write_text(json.dumps(config, indent=2))

            # Start background download (updates VM config on completion)
            from . import downloads
            downloads.start_iso_download(
                os_category=os_category,
                os_version=os_version,
                iso_path=str(ISO_DIR / f"{os_version}.iso"),
                cwd=str(ISO_DIR),
            )
            download_task_id = os_version

            # Return immediately with download_task_id so frontend can poll
            return {
                **config,
                "iso": None,  # signal that download is in progress
                "download_task_id": download_task_id,
            }

        # ISO provided explicitly — write config synchronously
        config = {
            "name": name,
            "os_category": os_category,
            "os_version": os_version,
            "iso": iso_path,
            "disk": disk,
            "disk_size": disk_size,
            "ram": ram,
            "vcpu": vcpu,
            "boot": boot,
            "vnc_port": vnc_port,
            "status": "stopped",
        }

        self._vm_path(name).write_text(json.dumps(config, indent=2))
        return config

    def delete_vm(self, name: str) -> bool:
        """
        Delete a VM permanently.

        The VM must be stopped before deletion (disk image is destroyed).
        Removes: config JSON, disk qcow2, PID file, QMP socket.

        Args:
            name: VM name.

        Returns:
            True if deleted, False if VM didn't exist.
        """
        config = self.get_vm(name)
        if not config:
            return False

        runner = QEMURunner(name, config)
        if runner.is_running():
            runner.stop()

        # Remove disk image
        disk = self._disk_path(name)
        if disk.exists():
            disk.unlink()

        # Remove configuration
        self._vm_path(name).unlink()
        return True

    # ── Lifecycle operations ───────────────────────────────────────────────

    def start_vm(self, name: str) -> bool:
        """
        Start a stopped VM.

        Args:
            name: VM name.

        Returns:
            True if started successfully, False if not found or already running.
        """
        config = self.get_vm(name)
        if not config:
            return False

        runner = QEMURunner(name, config)
        if runner.is_running():
            return False
        return runner.start()

    def stop_vm(self, name: str) -> bool:
        """
        Stop a running VM gracefully.

        Args:
            name: VM name.

        Returns:
            True if stopped successfully, False if not found.
        """
        config = self.get_vm(name)
        if not config:
            return False
        runner = QEMURunner(name, config)
        return runner.stop()

    def reboot_vm(self, name: str) -> bool:
        """
        Reboot a running VM via QMP system_reset (no disk I/O, immediate reboot).

        Args:
            name: VM name.

        Returns:
            True if reboot signal sent, False if not found or not running.
        """
        from .qmp_client import QMPClient

        config = self.get_vm(name)
        if not config:
            return False

        runner = QEMURunner(name, config)
        if not runner.is_running():
            return False

        qmp_sock = str(VM_DIR / f"{name}-qmp.sock")
        try:
            with QMPClient(qmp_sock) as client:
                client.system_reset()
            return True
        except Exception:
            return False

    def get_status(self, name: str) -> str:
        """
        Get the current status of a VM.

        Args:
            name: VM name.

        Returns:
            "running" | "stopped" | "not_found"
        """
        config = self.get_vm(name)
        if not config:
            return "not_found"
        runner = QEMURunner(name, config)
        return "running" if runner.is_running() else "stopped"
