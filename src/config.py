"""WebVM configuration and paths."""
import os
from pathlib import Path

# Base directories
HOME = Path.home()
WEBVM_DIR = HOME / ".webvm"
VM_DIR = WEBVM_DIR / "vms"
ISO_DIR = WEBVM_DIR / "isos"

# Ensure directories exist
VM_DIR.mkdir(parents=True, exist_ok=True)
ISO_DIR.mkdir(parents=True, exist_ok=True)

# QEMU settings
QEMU_BIN = "qemu-system-x86_64"
QEMU_IMG_BIN = "qemu-img"

# VNC base port (VMs get base_port + index)
VNC_BASE_PORT = 5930

# Flask settings
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True
