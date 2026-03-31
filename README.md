# WebVM

**Browser-based QEMU virtual machine management — no client install needed.**

Create, start, stop, and access VMs through any modern browser. Uses noVNC for direct VNC access and QEMU's native WebSocket VNC support (QEMU 8.0+), eliminating the need for any proxy daemons or client-side software.

```
browser (noVNC) ──WebSocket──► QEMU VNC (port 5930+)
                         │
Flask API (port 5000) ──┘
```

## Features

- 🌐 **Full browser access** — VM desktop in any browser via noVNC, no plugins
- 🔧 **VM lifecycle management** — Create, start, stop, reboot, delete
- 📡 **Native WebSocket VNC** — QEMU 8.0+ built-in, no websockify needed
- 📊 **Multi-VM dashboard** — Status overview of all VMs at a glance
- 🖥️ **OS version hierarchy** — Cascading dropdown (Linux → Ubuntu 24.04, etc.)
- 🛠️ **QMP control** — Direct QEMU management via JSON protocol
- 📁 **Flat-file config** — Each VM is a JSON file, no database needed

## Requirements

| Component | Version |
|-----------|---------|
| Linux | Ubuntu 20.04+ / Debian 11+ |
| QEMU | 8.0+ (8.2 recommended) |
| Python | 3.10+ |
| Browser | Chrome / Firefox / Safari / Edge (latest) |

**KVM strongly recommended** for hardware acceleration:
```bash
ls /dev/kvm   # should list device files
sudo apt install qemu-system-x86 qemu-utils
```

## Quick Start

```bash
# 1. Install dependencies
sudo apt install python3-flask qemu-system-x86 qemu-utils git
git clone https://github.com/<you>/webvm.git
cd webvm
git submodule update --init --recursive

# 2. Start the server
python3 -m flask --app src.app run --host 0.0.0.0 --port 5000

# 3. Open in browser
http://localhost:5000        # local
http://<your-ip>:5000        # other devices on LAN
```

## Creating Your First VM

1. Click **+ New VM**
2. Choose OS Category (e.g. Linux) and Version (e.g. Ubuntu 24.04)
3. Set RAM, vCPUs, and disk size
4. Optionally provide an ISO path for installation
5. Click **Create VM**, then click **View** → **Start**

The noVNC screen will appear and show the VM booting.

## Documentation

| Document | Purpose |
|----------|---------|
| [USAGE.md](docs/USAGE.md) | End-user guide — how to use WebVM |
| [INSTALL.md](docs/INSTALL.md) | Installation on Ubuntu/Debian |
| [DEVELOP.md](docs/DEVELOP.md) | Development setup and code architecture |
| [API.md](docs/API.md) | REST API reference |
| [SPEC.md](SPEC.md) | Feature specification and design decisions |

## Project Structure

```
webvm/
├── src/
│   ├── app.py           # Flask app + all HTTP routes
│   ├── config.py        # Path and runtime settings
│   ├── os_catalog.py    # OS category/version definitions
│   ├── qmp_client.py   # QEMU QMP protocol client
│   ├── qemu_runner.py   # QEMU process spawner
│   └── vm_manager.py    # VM CRUD and lifecycle
├── web/
│   ├── static/
│   │   ├── css/style.css
│   │   ├── js/app.js
│   │   └── js/novnc/    # noVNC (submodule)
│   └── templates/
│       ├── base.html
│       ├── index.html   # Dashboard
│       ├── create.html  # New VM form
│       └── vm.html      # VM detail + noVNC
└── docs/
    ├── API.md
    ├── DEVELOP.md
    ├── INSTALL.md
    └── USAGE.md
```

## REST API

```bash
GET    /api/vms                     # List all VMs
GET    /api/vm/:name                # Get VM details
POST   /api/vm                      # Create VM
DELETE /api/vm/:name                # Delete VM
POST   /api/vm/:name/start          # Start VM
POST   /api/vm/:name/stop           # Stop VM
POST   /api/vm/:name/reboot         # Reboot VM
GET    /api/vm/:name/status         # Get status
GET    /api/os/categories           # List OS categories
GET    /api/os/versions/:category   # List OS versions
GET    /api/isos                    # List ISOs
POST   /api/iso/upload              # Upload ISO
```

## Architecture Notes

**Why QEMU native WebSocket VNC?**  
QEMU 8.0+ accepts `-vnc websocket=on,port=N` — the browser connects directly via WebSocket with no websockify intermediary. One less daemon to manage.

**Why QMP instead of libvirt?**  
QMP communicates directly with the QEMU process via a Unix socket, no daemon required, minimal dependencies.

**Why flat-file VM configs?**  
One JSON per VM in `~/.webvm/vms/` — inspectable, editable, and git-backup-able without a database.

## License

MIT — see [LICENSE](LICENSE).
