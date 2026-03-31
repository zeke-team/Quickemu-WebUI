"""VM lifecycle manager — CRUD operations for virtual machines."""
import json
import subprocess
import os
from pathlib import Path
from typing import Optional

from .config import VM_DIR, ISO_DIR, QEMU_IMG_BIN, VNC_BASE_PORT
from .qemu_runner import QEMURunner


class VMManager:
    """Manages VM definitions and their lifecycle."""

    def __init__(self):
        VM_DIR.mkdir(parents=True, exist_ok=True)
        ISO_DIR.mkdir(parents=True, exist_ok=True)

    def _vm_path(self, name: str) -> Path:
        return VM_DIR / f"{name}.json"

    def _disk_path(self, name: str) -> Path:
        return VM_DIR / f"{name}.qcow2"

    def _get_vnc_port(self) -> int:
        """Allocate an available VNC port."""
        used = set()
        for f in VM_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if "vnc_port" in data:
                    used.add(data["vnc_port"])
            except Exception:
                pass
        port = VNC_BASE_PORT
        while port in used:
            port += 1
        return port

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list_vms(self) -> list[dict]:
        """Return all VMs with status."""
        vms = []
        for f in sorted(VM_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                runner = QEMURunner(data["name"], data)
                data["status"] = "running" if runner.is_running() else "stopped"
                vms.append(data)
            except Exception:
                pass
        return vms

    def get_vm(self, name: str) -> Optional[dict]:
        """Get a single VM config."""
        path = self._vm_path(name)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        runner = QEMURunner(name, data)
        data["status"] = "running" if runner.is_running() else "stopped"
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
        """Create a new VM definition and optionally allocate disk."""
        if self._vm_path(name).exists():
            raise FileExistsError(f"VM '{name}' already exists")

        vnc_port = self._get_vnc_port()
        disk = str(self._disk_path(name))

        # Create qcow2 disk image
        result = subprocess.run(
            [QEMU_IMG_BIN, "create", "-f", "qcow2", disk, disk_size],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"qemu-img failed: {result.stderr}")

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
        """Delete a VM (must be stopped first)."""
        config = self.get_vm(name)
        if not config:
            return False

        runner = QEMURunner(name, config)
        if runner.is_running():
            runner.stop()

        # Remove disk
        disk = self._disk_path(name)
        if disk.exists():
            disk.unlink()

        # Remove config
        self._vm_path(name).unlink()
        return True

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_vm(self, name: str) -> bool:
        """Start a VM."""
        config = self.get_vm(name)
        if not config:
            return False

        runner = QEMURunner(name, config)
        if runner.is_running():
            return False  # Already running

        return runner.start()

    def stop_vm(self, name: str) -> bool:
        """Stop a VM."""
        config = self.get_vm(name)
        if not config:
            return False

        runner = QEMURunner(name, config)
        return runner.stop()

    def reboot_vm(self, name: str) -> bool:
        """Reboot a VM via QMP."""
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
        """Get current VM status."""
        config = self.get_vm(name)
        if not config:
            return "not_found"
        runner = QEMURunner(name, config)
        return "running" if runner.is_running() else "stopped"
