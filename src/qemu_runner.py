"""QEMU process runner — spawns and manages QEMU VM processes."""
import subprocess
import os
import signal
from pathlib import Path

from .config import QEMU_BIN, QEMU_IMG_BIN, VM_DIR


class QEMURunner:
    """Spawn and manage a QEMU virtual machine process."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.process: subprocess.Popen | None = None
        self.pid_file = VM_DIR / f"{name}.pid"
        self.qmp_sock = VM_DIR / f"{name}-qmp.sock"
        self.vnc_port = config.get("vnc_port", 5930)
        self.qemu_bin = QEMU_BIN

    def build_args(self) -> list[str]:
        """Build the full QEMU command-line arguments."""
        args = [
            self.qemu_bin,
            "-name", self.name,
            "-machine", "q35",
            "-m", str(self.config.get("ram", "4096")),
            "-smp", str(self.config.get("vcpu", 2)),
            "-enable-kvm",          # KVM acceleration
            "-display", f"vnc=0.0.0.0:{self.vnc_port}",
            "-vnc", f"websocket=on,port={self.vnc_port}",
            "-qmp", f"unix:{self.qmp_sock},server=on,wait=off",
            "-pidfile", str(self.pid_file),
            "-daemonize",
        ]

        iso = self.config.get("iso")
        if iso:
            args += ["-cdrom", iso]

        disk = self.config.get("disk")
        if disk:
            args += ["-drive", f"file={disk},format=qcow2,cache=writeback"]

        boot_dev = self.config.get("boot", "cd")
        if boot_dev == "cd" and iso:
            args += ["-boot", "d"]
        elif boot_dev == "disk" and disk:
            args += ["-boot", "c"]

        # Additional args
        extra = self.config.get("extra_args", "")
        if extra:
            args += extra.split()

        return args

    def start(self) -> bool:
        """Start the QEMU process. Returns True on success."""
        if self.is_running():
            return False

        # Remove stale socket and pid file
        for f in (self.qmp_sock, self.pid_file):
            if f.exists():
                f.unlink()

        args = self.build_args()
        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            raise RuntimeError(f"QEMU binary not found: {self.qemu_bin}")

    def stop(self) -> bool:
        """Stop the QEMU process gracefully via QMP, then kill if needed."""
        from .qmp_client import QMPClient

        if self.is_running():
            try:
                with QMPClient(str(self.qmp_sock)) as client:
                    client.shutdown()
            except Exception:
                pass

        # Kill by PID file
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass
            self.pid_file.unlink()

        # Kill stale QEMU process by name pattern
        try:
            subprocess.run(
                ["pkill", "-f", f"qemu-system-x86_64.*{self.name}"],
                capture_output=True,
            )
        except Exception:
            pass

        return True

    def is_running(self) -> bool:
        """Check if VM is running by testing PID file and QMP socket."""
        if not self.pid_file.exists():
            return False

        pid = int(self.pid_file.read_text().strip())
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            self.pid_file.unlink()
            return False

    def get_vnc_websocket_port(self) -> int:
        """Return the WebSocket port for VNC (same as VNC port in QEMU 8.2+)."""
        return self.vnc_port
