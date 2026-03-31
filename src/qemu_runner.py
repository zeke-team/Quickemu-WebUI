"""
QEMU process runner.

Responsible for building the full QEMU command-line from a VM config dict
and spawning the QEMU process as a daemon. Also handles process termination
and status checking.

Key features:
- Builds QEMU args from VM config
- Uses KVM for hardware acceleration when available
- Enables native WebSocket VNC (no websockify needed, QEMU 8.0+)
- Exposes QMP control socket for VM management
- Runs QEMU as a daemon (-daemonize)
"""

import subprocess
import os
import signal
from pathlib import Path

from .config import QEMU_BIN, QEMU_IMG_BIN, VM_DIR


class QEMURunner:
    """
    Encapsulates a single QEMU VM process.

    Attributes:
        name: VM identifier, used in filenames and QEMU -name flag.
        config: VM configuration dict (ram, vcpu, vnc_port, iso, disk, boot, etc.).
        pid_file: Path to the file containing the QEMU daemon PID.
        qmp_sock: Path to the QMP Unix socket for VM control.
        vnc_port: TCP port for VNC (and WebSocket VNC — same port in QEMU 8.0+).
    """

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.process: subprocess.Popen | None = None

        # Files are stored alongside the VM config in VM_DIR
        self.pid_file = VM_DIR / f"{name}.pid"
        self.qmp_sock = VM_DIR / f"{name}-qmp.sock"
        self.vnc_port = config.get("vnc_port", 5930)
        self.qemu_bin = QEMU_BIN

    def build_args(self) -> list[str]:
        """
        Build the complete QEMU command-line argument list from self.config.

        Returns:
            List of command-line arguments suitable for subprocess.Popen.

        Key QEMU flags used:
            -display vnc=0.0.0.0:N    — VNC server bound to all interfaces
            -vnc websocket=on,port=N   — Enables WebSocket VNC on the same port
            -qmp unix:SOCK,server=on   — QMP control socket
            -enable-kvm                — Use KVM for hardware acceleration
            -daemonize                — Run in background (required for PID tracking)
        """
        is_macos = self.config.get("os_category") == "macos"

        args = [
            self.qemu_bin,
            "-name", self.name,
            # Machine type q35 is modern UEFI-capable x86_64 platform
            "-machine", "q35",
            # Memory and CPU
            "-m", str(self.config.get("ram", "4096")),
            "-smp", str(self.config.get("vcpu", 2)),
            # KVM hardware acceleration — critical for performance
            "-enable-kvm",
            # VNC display: WebSocket VNC on display N (port = 5900 + N)
            # Correct format: -vnc :N,websocket=on (e.g. :30 for port 5930)
            # e.g. vnc_port=5930 → display :30
            "-vnc", f":{self.vnc_port - 5900},websocket=on",
            # QMP control socket for management commands
            "-qmp", f"unix:{self.qmp_sock},server=on,wait=off",
            # PID file so we can track the daemonized process
            "-pidfile", str(self.pid_file),
            # Run in background
            "-daemonize",
        ]

        # ── macOS-specific configuration ──────────────────────────────────
        # macOS VMs require: UEFI firmware, OpenCore bootloader, AHCI disk bus,
        # nec-usb-xhci controller, and virtio-gpu-pci display.
        if is_macos:
            efi_code = self.config.get("efi_code")
            efi_vars = self.config.get("efi_vars")
            if efi_code and efi_vars:
                import shutil as _shutil
                vm_efi_vars = VM_DIR / f"{self.name}-ovmf-vars.fd"
                if not vm_efi_vars.exists():
                    _shutil.copy(efi_vars, vm_efi_vars)
                args += [
                    "-global", "driver=cfi.pflash01,property=secure,value=on",
                    "-drive", f"if=pflash,format=raw,unit=0,file={efi_code},readonly=on",
                    "-drive", f"if=pflash,format=raw,unit=1,file={vm_efi_vars}",
                ]
            # AHCI controller for up to 6 SATA ports
            args += ["-device", "ahci,id=ahci"]

            # Bootloader: OpenCore on AHCI port 0 (bootindex=0)
            bootloader = self.config.get("bootloader")
            if bootloader:
                args += [
                    "-device", "ide-hd,bus=ahci.0,drive=BootLoader,bootindex=0",
                    "-drive", f"id=BootLoader,if=none,format=qcow2,file={bootloader}",
                ]

            # Recovery Image on AHCI port 1
            recovery_img = self.config.get("recovery_image")
            if recovery_img:
                args += [
                    "-device", "ide-hd,bus=ahci.1,drive=RecoveryImage",
                    "-drive", f"id=RecoveryImage,if=none,format=raw,file={recovery_img}",
                ]

            # System disk on AHCI port 2
            disk = self.config.get("disk")
            if disk:
                args += [
                    "-device", "ide-hd,bus=ahci.2,drive=SystemDisk",
                    "-drive", f"id=SystemDisk,if=none,format=qcow2,file={disk},cache=writeback",
                ]

            # USB 3.0 controller (required for macOS input devices)
            args += [
                "-device", "nec-usb-xhci,id=xhci",
                "-global", "nec-usb-xhci.msi=off",
            ]

        else:
            # ── Standard (non-macOS) configuration ──────────────────────────
            iso = self.config.get("iso")
            if iso:
                args += ["-cdrom", iso]

            disk = self.config.get("disk")
            if disk:
                args += [
                    "-drive",
                    f"file={disk},format=qcow2,cache=writeback"
                ]

            # Boot device order
            boot_dev = self.config.get("boot", "cd")
            if boot_dev == "cd" and iso:
                args += ["-boot", "d"]
            elif boot_dev == "disk" and disk:
                args += ["-boot", "c"]

        # Extra QEMU arguments from config
        extra = self.config.get("extra_args", "")
        if extra:
            args += extra.split()

        return args

    def start(self) -> bool:
        """
        Spawn the QEMU process. Returns True on success, False if already running.

        Raises:
            RuntimeError: If the QEMU binary is not found.
        """
        if self.is_running():
            return False

        # Clean up stale files from previous runs
        for f in (self.qmp_sock, self.pid_file):
            if f.exists():
                f.unlink()

        args = self.build_args()
        try:
            # stdout/stderr suppressed; QEMU -daemonize handles backgrounding
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            raise RuntimeError(
                f"QEMU binary not found at {self.qemu_bin}. "
                "Install with: sudo apt install qemu-system-x86"
            )

    def stop(self) -> bool:
        """
        Stop the QEMU VM gracefully, then forcefully if needed.

        Tries graceful shutdown via QMP first, then falls back to SIGTERM,
        and finally SIGKILL if the process is still alive.
        """
        if self.is_running():
            # Try graceful shutdown via QMP
            try:
                from .qmp_client import QMPClient
                with QMPClient(str(self.qmp_sock)) as client:
                    client.shutdown()
            except Exception:
                pass  # Fall through to kill

        # Kill by PID file
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass
            self.pid_file.unlink()

        # Fallback: kill any QEMU process matching this VM name
        try:
            subprocess.run(
                ["pkill", "-f", f"qemu-system-x86_64.*{self.name}"],
                capture_output=True,
            )
        except Exception:
            pass

        self.process = None
        return True

    def is_running(self) -> bool:
        """
        Check whether the VM process is currently running.

        Checks the PID file exists and the process is alive.
        Cleans up stale PID file if the process is dead.
        """
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
            os.kill(pid, 0)   # Signal 0 — checks if process exists without sending signal
            return True
        except ProcessLookupError:
            # PID file exists but process is dead — clean up
            self.pid_file.unlink()
            return False
        except ValueError:
            self.pid_file.unlink()
            return False

    def get_vnc_websocket_port(self) -> int:
        """
        Return the WebSocket VNC port.

        In QEMU 8.0+, WebSocket VNC uses the same TCP port as regular VNC.
        The browser connects directly to ws://host:port with no intermediate proxy.
        """
        return self.vnc_port
