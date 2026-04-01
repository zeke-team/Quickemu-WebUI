# WebVM — Product Specification

> **Last updated:** 2026-04-01
> **Version:** 1.0.0
> **Status:** In Development

---

## 1. Overview

**Name:** WebVM
**Type:** Self-hosted browser-based virtual machine management platform
**Summary:** A lightweight alternative to Proxmox, VirtualBox, or VMware ESXi. WebVM lets you create, start, stop, and access QEMU virtual machines entirely through a modern browser — no client software, plugins, or RDP clients required.

**Target users:**
- Homelab enthusiasts running Linux on a server/NUC/mini PC
- Developers who need quick VM access from any device
- Anyone who wants a simple, local VM management UI without the complexity of libvirt/VirtualBox

**Key differentiator:** No websockify, no TigerVNC, no libvirt daemon. QEMU's native WebSocket VNC (QEMU 8.0+) and a single Flask process are the only runtime dependencies.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Browser                                │
│   ┌──────────────────┐           ┌─────────────────────────┐    │
│   │  WebVM Dashboard │           │   noVNC (pure JS)      │    │
│   │  (Flask/Jinja2)  │           │   VM Screen Display     │    │
│   └────────┬─────────┘           └───────────┬─────────────┘    │
│            │                                  │                  │
│            │        HTTP / WebSocket          │                  │
└────────────┼──────────────────────────────────┼──────────────────┘
             │                                  │
             │  Flask (port 5000)               │  ws://host:5730
             │                                  │
┌────────────┼──────────────────────────────────┼──────────────────┐
│            │  REST API (JSON)                 │                  │
│     ┌─────▼─────────────────────────────────▼──────┐           │
│     │              WebVM Flask Backend               │           │
│     │  • VM CRUD + lifecycle (vm_manager.py)       │           │
│     │  • QEMU process runner  (qemu_runner.py)    │           │
│     │  • QMP client (qmp_client.py)               │           │
│     │  • ISO download tracker (downloads.py)      │           │
│     │  • OS catalog / i18n                        │           │
│     └──────────────────┬──────────────────────────┘           │
│                         │                                       │
│     ┌──────────────────▼──────────────────────────┐            │
│     │           QEMU Virtual Machines              │            │
│     │  • VNC over WebSocket (native, QEMU 8.0+)  │            │
│     │  • QMP Unix socket (JSON control)          │            │
│     │  • KVM hardware acceleration               │            │
│     └──────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web UI | Jinja2 + vanilla JS | Server-rendered HTML, no frontend build |
| Backend | Flask (Python 3.10+) | REST API + session management |
| VM Hypervisor | QEMU 8.0+ (system-x86) | Hardware virtualization |
| Acceleration | KVM (Kernel-based VM) | CPU hardware acceleration |
| Display | noVNC (pure JS) | Browser-native VNC client |
| Auto-ISO | quickemu/quickget | OS ISO download and config |
| VM Config Storage | JSON files (~/.webvm/vms/) | No database required |

---

## 3. Feature List

### 3.1 VM Dashboard
- Grid/list of all VMs with live status (running / stopped / error)
- Resource display (RAM, vCPU, OS type, version)
- One-click Start / Stop / Reboot / Delete per VM
- Real-time status polling (5-second interval)

### 3.2 VM Creation
- Cascading dropdown: OS Category → OS Version
- Configurable: VM name, RAM, vCPU, disk size, boot device
- ISO upload via web form (or manual path entry)
- **Auto-download ISO via quickemu/quickget** (no manual ISO needed)
- Progress bar with real-time speed/size display during download

### 3.3 VM Detail Page
- Embedded noVNC full-screen console
- Control bar: Start / Stop / Reboot / Delete
- VM configuration display (read-only)
- Connection status indicator

### 3.4 noVNC Console
- Pure JavaScript VNC client, zero client installation
- Full keyboard/mouse passthrough
- Clipboard copy-paste (text only)
- Fullscreen toggle, reconnect, settings menu

### 3.5 VM Lifecycle
- **Start:** Spawn QEMU daemon, allocate VNC port, set up QMP socket
- **Stop:** Graceful shutdown via QMP → SIGTERM → SIGKILL
- **Reboot:** QMP `system_reset` command (immediate, no disk I/O)
- **Delete:** Stop VM, remove disk image, remove config

### 3.6 ISO Download Progress
- Background download via quickemu/quickget
- Progress tracked by file-size polling
- Survives Flask restarts (marker-file based)
- Duplicate download guard (prevents concurrent same-OS downloads)

### 3.7 Internationalization
- English (en) and Simplified Chinese (zh_CN) supported
- Language switcher in navigation bar
- All UI strings externalized in JSON translation files
- Persistent language preference via cookie

---

## 4. Data Model

### 4.1 VM Configuration (stored as JSON in `~/.webvm/vms/<name>.json`)

```json
{
  "name": "my-ubuntu",
  "os_category": "linux",
  "os_version": "ubuntu-24.04",
  "iso": "/home/user/.webvm/isos/ubuntu-24.04.4-desktop-amd64.iso",
  "disk": "/home/user/.webvm/vms/my-ubuntu.qcow2",
  "disk_size": "64G",
  "ram": "4096",
  "vcpu": 2,
  "boot": "cd",
  "vnc_port": 5930,
  "status": "stopped"
}
```

### 4.2 Runtime Files (per VM, in `~/.webvm/vms/`)

| File | Purpose | Lifetime |
|------|---------|----------|
| `<name>.json` | VM configuration | Until VM deleted |
| `<name>.qcow2` | Disk image | Until VM deleted |
| `<name>.pid` | QEMU daemon PID | Only while running |
| `<name>-qmp.sock` | QMP control socket | Only while running |

### 4.3 Storage Layout

```
~/.webvm/              # Root data directory
├── vms/               # VM configs, disks, runtime files
│   ├── my-vm.json
│   ├── my-vm.qcow2
│   └── ...
└── isos/              # ISO images (uploaded or quickemu-downloaded)
    └── ubuntu-24.04.4-desktop-amd64.iso
```

---

## 5. QEMU Integration

### 5.1 QEMU Version Requirement

**Minimum: QEMU 8.0** (for native WebSocket VNC without websockify)
**Recommended: QEMU 8.2+**

Check version: `qemu-system-x86_64 --version`

### 5.2 VNC and WebSocket Ports

QEMU allocates two ports per VM:

| Port | Protocol | Use |
|------|---------|-----|
| `vnc_port` (e.g. 5930) | TCP VNC | noVNC proxy fallback |
| `vnc_port - 200` (e.g. 5730) | WebSocket | Browser connection |

The browser connects directly to `ws://host:5730` with no intermediate proxy.

### 5.3 QEMU Command Template (non-macOS)

```bash
qemu-system-x86_64 \
  -name <name> \
  -machine q35 \
  -m <ram> \
  -smp <vcpu> \
  -enable-kvm \
  -cdrom <iso> \
  -drive file=<disk>,format=qcow2,cache=writeback \
  -vnc :<display>,websocket=on \
  -qmp unix:<vms-dir>/<name>-qmp.sock,server=on,wait=off \
  -pidfile <vms-dir>/<name>.pid \
  -daemonize
```

### 5.4 macOS Configuration

macOS VMs require additional configuration due to Apple's hardware requirements:
- OVMF UEFI firmware + OpenCore bootloader
- AHCI SATA controller (not virtio-blk)
- NEC USB 3.0 xHCI controller
- VMware SVGA display adapter (macOS has no virtio-gpu driver)

---

## 6. REST API

All endpoints return JSON. UI routes return rendered HTML.

### VM Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/vms` | List all VMs with status |
| `GET` | `/api/vm/<name>` | Get single VM config + status |
| `POST` | `/api/vm` | Create new VM |
| `DELETE` | `/api/vm/<name>` | Delete VM |
| `POST` | `/api/vm/<name>/start` | Start VM |
| `POST` | `/api/vm/<name>/stop` | Stop VM |
| `POST` | `/api/vm/<name>/reboot` | Reboot VM |
| `GET` | `/api/vm/<name>/status` | Get current status |

### ISO / OS

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/os/categories` | List OS categories |
| `GET` | `/api/os/versions/<cat>` | List versions for category |
| `GET` | `/api/isos` | List local ISO files |
| `POST` | `/api/iso/upload` | Upload ISO file |
| `GET` | `/api/download/<task_id>/status` | Download progress |

### API Response: Create VM

```json
{
  "name": "my-ubuntu",
  "os_category": "linux",
  "os_version": "ubuntu-24.04",
  "iso": "/home/user/.webvm/isos/ubuntu-24.04.4-desktop-amd64.iso",
  "disk": "/home/user/.webvm/vms/my-ubuntu.qcow2",
  "disk_size": "64G",
  "ram": "4096",
  "vcpu": 2,
  "boot": "cd",
  "vnc_port": 5930,
  "status": "stopped"
}
```

When ISO is auto-downloaded:
```json
{
  "name": "my-ubuntu",
  "os_version": "ubuntu-24.04",
  "iso": null,
  "download_task_id": "ubuntu-24.04",
  ...
}
```

---

## 7. File Structure

```
webvm/
├── README.md               # Project overview (links to docs)
├── LICENSE                 # MIT License
├── SPEC.md                 # This document
├── requirements.txt        # Python dependencies
├── setup.sh                # One-click installer
│
├── src/                    # Python source code
│   ├── __init__.py
│   ├── app.py              # Flask app factory + all routes
│   ├── config.py           # Runtime paths, QEMU binary names, ports
│   ├── vm_manager.py       # VM lifecycle (create/delete/start/stop/reboot)
│   ├── qemu_runner.py      # QEMU process spawn/build_args/is_running
│   ├── qmp_client.py      # QMP Unix socket JSON protocol client
│   ├── os_catalog.py       # OS category/version definitions + quickemu map
│   ├── downloads.py        # Background ISO download tracker
│   └── i18n.py             # Language detection + translation system
│
├── web/                    # Frontend assets
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/
│   │       ├── app.js      # Dashboard + polling logic
│   │       └── novnc/      # noVNC library (git submodule)
│   │           ├── core/
│   │           └── app/
│   └── templates/
│       ├── base.html       # Base layout + nav + i18n
│       ├── index.html      # VM dashboard
│       ├── vm.html         # VM detail + noVNC embed
│       ├── vm_console.html  # Standalone noVNC page
│       └── create.html     # VM creation form + download progress
│
├── docs/
│   ├── INSTALL.md          # Installation guide
│   ├── USAGE.md             # User guide
│   └── DEVELOP.md          # Development setup
│
└── tests/
    └── test_vm_manager.py  # Unit tests
```

---

## 8. Supported Guest Operating Systems

### Linux
Ubuntu 24.04/22.04/20.04, Fedora 41/40, Debian 12/11, Arch Linux, Linux Mint 21, openSUSE Leap 15, AlmaLinux 9, Rocky Linux 9

### Windows
Windows 11, Windows 10, Windows Server 2022, Windows Server 2019

### macOS
Sequoia, Sonoma, Ventura, Monterey, Big Sur, Catalina, Mojave (requires macOS-appropriate hardware; AMD Vega/Radeon GPU recommended for GPU passthrough)

### Other
Generic ISO/CD-ROM for BSDs, minimal ISOs, live CDs

---

## 9. Deployment Options

### Option A: Per-user systemd service (recommended for single-user)
- Installs to `~/.config/systemd/user/webvm.service`
- Auto-starts on login
- Auto-restarts on crash
- No root required

### Option B: System-wide systemd service
- Installs to `/etc/systemd/system/webvm.service`
- Starts on boot (before user login)
- Requires root for installation

### Option C: Direct Python process
```bash
python3 -m flask --app src.app run --host 0.0.0.0 --port 5000
```

### Option D: Production (gunicorn + reverse proxy)
```bash
gunicorn -w 4 -b 0.0.0.0:5000 src.app:app
```
Behind nginx for HTTPS termination.

---

## 10. Acceptance Criteria

- [x] Dashboard displays all VMs with correct running/stopped status
- [x] Can create a VM from the form and see it in the dashboard
- [x] Can start a VM and see it transition to "running" status
- [x] noVNC screen renders in browser when VM is running
- [x] Can interact with VM desktop via mouse and keyboard in browser
- [x] Can stop a running VM from the UI
- [x] Can delete a stopped VM (disk image destroyed)
- [x] All REST API endpoints return correct JSON responses
- [x] OS category → version cascading dropdown works
- [x] ISO auto-download via quickemu with progress bar display
- [x] Language switcher works (English / Simplified Chinese)
- [x] systemd user service auto-starts and auto-restarts on crash
- [ ] VM resource usage (CPU/RAM) display while running
- [ ] VM snapshot support (QEMU snapshot Blaine)
- [ ] Multi-user authentication / access control

---

## 11. Non-Goals (Out of Scope)

- Live migration of VMs between hosts
- VM snapshots (though QEMU supports it, UI is not planned for v1)
- Multi-node / cluster management
- User authentication / multi-tenancy (single-user homelab focus)
- macOS on non-Apple hardware with full GPU passthrough (requires额外配置)
- Running on Windows or macOS as the host OS

---

## 12. Known Limitations

- **macOS GPU:** macOS guests do not have native virtio-gpu or virtio-vga drivers. The `vmware-svga` adapter is used as a compromise; for best results, AMD Radeon GPU passthrough is recommended.
- **macOS on non-Apple hardware:** Apple does not license macOS for non-Apple hardware. WebVM supports the technical capability but users must ensure they comply with Apple's licensing terms.
- **Network speed:** ISO downloads through quickemu are limited by the server's internet connection speed. Large ISOs (Windows 11 ≈ 7 GB, macOS Sequoia ≈ 14 GB) can take significant time.
- **VNC clipboard:** Only text clipboard is supported; file drag-and-drop is not available in noVNC.
