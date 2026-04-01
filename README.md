# WebVM

**Browser-based QEMU virtual machine management — no client install needed.**

Create, start, stop, and access VMs through any modern browser. Uses noVNC for direct VNC access and QEMU's native WebSocket VNC support (QEMU 8.0+), eliminating the need for any proxy daemons, VNC viewers, or client-side software.

```
browser (noVNC) ──WebSocket──► QEMU VNC (port 5930+)
                         │
              Flask API (port 5000)
```

## Features

- 🌐 **Full browser access** — VM desktop in any browser via noVNC, no plugins
- 🔧 **VM lifecycle management** — Create, start, stop, reboot, delete
- 📡 **Native WebSocket VNC** — QEMU 8.0+ built-in, no websockify needed
- 📊 **Multi-VM dashboard** — Status overview of all VMs at a glance
- 🪟 **OS version hierarchy** — Cascading dropdown (Linux → Ubuntu 24.04, etc.)
- 🤖 **Auto-download ISOs** — Integrates with quickemu/quickget for automatic OS image download
- 📥 **Download progress** — Real-time progress bar with speed and percentage
- 🗣️ **Bilingual UI** — English and Simplified Chinese
- 🔄 **Auto-start** — systemd user service with crash recovery

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 20.04+, Debian 11+ | Ubuntu 22.04 / 24.04 LTS |
| CPU | x86_64 with VT-x / AMD-V | Modern multi-core |
| RAM | 4 GB | 16 GB+ |
| QEMU | 8.0+ | 8.2+ |
| Python | 3.10+ | 3.12+ |
| Browser | Chrome 90+, Firefox 88+ | Chrome / Firefox |

> **KVM is required** for acceptable VM performance. Check with: `ls /dev/kvm`

## Quick Start

```bash
git clone https://github.com/<your-username>/webvm.git
cd webvm
chmod +x setup.sh
./setup.sh
```

Open **http://\<your-ip\>:5000** in your browser.

## Manual Start

```bash
# Install dependencies
sudo apt install python3-flask qemu-system-x86 qemu-utils git

# Install quickemu (optional, enables ISO auto-download)
sudo apt install quickemu

# Start WebVM
python3 -m flask --app src.app run --host 0.0.0.0 --port 5000
```

## Documentation

| Document | Description |
|----------|-------------|
| [SPEC.md](./SPEC.md) | Product specification and architecture |
| [docs/INSTALL.md](./docs/INSTALL.md) | Detailed installation guide |
| [docs/USAGE.md](./docs/USAGE.md) | End-user guide |
| [docs/DEVELOP.md](./docs/DEVELOP.md) | Development setup |

## Architecture

```
browser ──HTTP──► Flask API (5000)
         ──WS────► QEMU VNC (WebSocket, e.g. 5730)
```

- **Flask** — REST API, session management, i18n
- **QEMU** — VM hypervisor with native WebSocket VNC (no websockify)
- **noVNC** — Pure JavaScript VNC client in the browser
- **quickemu/quickget** — Optional ISO auto-download

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/vms` | List all VMs |
| `POST` | `/api/vm` | Create VM |
| `GET` | `/api/vm/<name>` | Get VM details |
| `DELETE` | `/api/vm/<name>` | Delete VM |
| `POST` | `/api/vm/<name>/start` | Start VM |
| `POST` | `/api/vm/<name>/stop` | Stop VM |
| `POST` | `/api/vm/<name>/reboot` | Reboot VM |
| `GET` | `/api/download/<task_id>/status` | ISO download progress |

## License

MIT
