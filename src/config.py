"""
WebVM Configuration

All runtime paths and constants are centralized here.
This avoids hardcoded paths scattered across modules and makes
deployment on different systems straightforward.
"""

import os
from pathlib import Path

# ── Directory paths ────────────────────────────────────────────────────────────
# VM configs (*.json), disk images (*.qcow2), and runtime files (*.pid, *-qmp.sock)
# are stored in ~/.webvm/vms/ by default.
# ISO files uploaded via the web UI go into ~/.webvm/isos/

HOME     = Path.home()
WEBVM_DIR = HOME / ".webvm"          # Root of all WebVM data
VM_DIR    = WEBVM_DIR / "vms"        # VM configs, disks, sockets
ISO_DIR   = WEBVM_DIR / "isos"       # Uploaded ISO images

# Ensure directories exist on import
VM_DIR.mkdir(parents=True, exist_ok=True)
ISO_DIR.mkdir(parents=True, exist_ok=True)

# ── QEMU binary names ─────────────────────────────────────────────────────────
# These must be in PATH. qemu-system-x86_64 for x86_64 VMs.
# On ARM hosts, use qemu-system-aarch64 (separate install).

QEMU_BIN    = "qemu-system-x86_64"   # QEMU emulator for x86_64 VMs
QEMU_IMG_BIN = "qemu-img"             # QEMU disk image manipulation tool

# ── Network ───────────────────────────────────────────────────────────────────
# VNC base port. When a VM is created, it gets the next available port
# starting from this number. QEMU's VNC and WebSocket VNC share the same port.
# Port 5930 is the well-known VNC alt port (5900 + 30 offset to avoid conflict
# with display :0).

VNC_BASE_PORT = 5930

# ── Flask server ──────────────────────────────────────────────────────────────
# Bound to 0.0.0.0 so it's accessible from other devices on the LAN.
# Change PORT to run multiple instances on different ports.

HOST  = "0.0.0.0"    # Listen on all network interfaces
PORT  = 5000          # HTTP port
DEBUG = True          # Auto-reload on code changes (disable in production)
