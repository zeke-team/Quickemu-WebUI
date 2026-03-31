# WebVM — Project Specification

## 1. Overview

**Name:** WebVM
**Type:** Web-based VM management platform
**Summary:** A self-hosted platform for managing QEMU virtual machines through a browser, using noVNC for direct VM desktop access without any client-side software installation.

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser                              │
│    ┌──────────────┐        ┌────────────────────┐       │
│    │  WebVM UI    │        │   noVNC Client     │       │
│    │  (Dashboard) │        │  (VM Screen)       │       │
│    └──────┬───────┘        └─────────┬──────────┘       │
│           │                           │                  │
│           │         HTTP / WebSocket   │                  │
└───────────┼───────────────────────────┼──────────────────┘
            │                           │
            │  Flask Backend (port 5000) │
            │                           │
┌───────────┼───────────────────────────┼──────────────────┐
│           │                           │                  │
│    ┌──────▼───────────────────────────▼──────────┐       │
│    │            VM Manager Service               │       │
│    │  - REST API (Flask routes)                 │       │
│    │  - QMP Command Bridge                      │       │
│    │  - VM Process Manager                      │       │
│    └──────────────────┬──────────────────────────┘       │
│                      │                                  │
│    ┌──────────────────▼──────────────────────────┐       │
│    │           QEMU Virtual Machines             │       │
│    │  - VNC over WebSocket (native QEMU)        │       │
│    │  - QMP control socket (JSON)               │       │
│    └────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## 3. Features & User Stories

### 3.1 VM Dashboard (Home Page)
- List all VMs with status: running / stopped / error
- Show VM name, OS type, resource usage (CPU, RAM if running)
- Create new VM button
- Actions per VM: Start, Stop, Delete

### 3.2 VM Creation
- Form fields:
  - VM name (required, unique)
  - OS category: Linux / Windows / macOS / Other
  - OS version (cascading dropdown based on category, e.g., Ubuntu 24.04, Fedora 41, Windows 11, macOS Sequoia)
  - ISO file upload or path selection
  - Disk size (GB)
  - RAM size (MB)
  - vCPU count
- Generate QEMU command and create VM

### 3.3 VM Detail Page
- VM name, status, OS type
- noVNC screen embed (full area)
- Control bar: Start / Stop / Reboot / Delete
- Resource allocation display
- VM config display (read-only)

### 3.4 VNC Access
- Full-screen VM console via noVNC embedded in browser
- Keyboard/mouse passthrough
- Clipboard support (text only)
- Connection status indicator

### 3.5 REST API
All API endpoints return JSON.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vms` | List all VMs |
| GET | `/api/vm/<name>` | Get VM details |
| POST | `/api/vm` | Create new VM |
| DELETE | `/api/vm/<name>` | Delete VM |
| POST | `/api/vm/<name>/start` | Start VM |
| POST | `/api/vm/<name>/stop` | Stop VM |
| POST | `/api/vm/<name>/reboot` | Reboot VM |
| GET | `/api/vm/<name>/status` | Get VM status |

## 4. Data Model

### VM Configuration (stored as JSON)
```json
{
  "name": "my-ubuntu",
  "os_category": "linux",
  "os_version": "ubuntu-24.04",
  "iso": "/path/to/ubuntu.iso",
  "disk_size": "64G",
  "ram": "4096",
  "vcpu": 2,
  "status": "stopped",
  "vnc_port": 5930,
  "qmp_socket": "/path/to/my-ubuntu-qmp.sock",
  "pid_file": "/path/to/my-ubuntu.pid"
}
```

### Storage
- VM configs stored in `~/.webvm/vms/`
- Each VM has: `<name>.json` config + `<name>.qcow2` disk image
- ISO files stored in `~/.webvm/isos/`

## 5. QEMU Integration

### VM Start Command Template
```bash
qemu-system-x86_64 \
  -name vm-name \
  -machine q35 \
  -m 4096 \
  -smp 2 \
  -cdrom /path/to/iso \
  -drive file=/path/to/disk.qcow2,format=qcow2 \
  -display vnc=0.0.0.0:port \
  -vnc websocket=on,port=port \
  -qmp unix:/path/to/qmp.sock,server=on,wait=off \
  -pidfile /path/to/pid \
  -daemonize
```

### VNC WebSocket
- QEMU 8.2 supports native WebSocket VNC
- noVNC connects via `ws://host:port/websockify`
- noVNC is a pure JS VNC client, no browser plugin needed

## 6. File Structure

```
webvm/
├── README.md
├── LICENSE
├── SPEC.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── app.py              # Flask application entry
│   ├── vm_manager.py       # VM lifecycle management
│   ├── qemu_runner.py      # QEMU process spawning
│   ├── qmp_client.py       # QMP JSON protocol client
│   └── config.py           # Path and settings
├── web/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js
│   └── templates/
│       ├── base.html
│       ├── index.html      # VM dashboard
│       ├── vm.html         # VM detail + noVNC
│       └── create.html     # Create VM form
├── tests/
│   └── test_vm_manager.py
└── docs/
    └── API.md
```

## 7. Acceptance Criteria

- [ ] Dashboard shows list of VMs with correct status
- [ ] Can create a VM from form and see it in list
- [ ] Can start a VM and see it change to "running" status
- [ ] noVNC screen renders correctly in browser
- [ ] Can interact with VM desktop using mouse and keyboard in browser
- [ ] Can stop a VM from the UI
- [ ] Can delete a stopped VM
- [ ] All API endpoints return correct JSON responses
- [ ] Server starts with `python src/app.py`
- [ ] No external dependencies beyond Python + QEMU

## 8. Non-Goals (Out of Scope for v1)

- Live migration
- VM snapshots
- Multi-node/cluster management
- User authentication / multi-tenancy
- macOS on AMD hardware (due to Apple's restrictions)
