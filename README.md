# WebVM

> Browser-based virtual machine management platform. Create, control, and access VMs through any modern browser — no plugins required.

## Features

- **Web UI** — Full VM management dashboard, accessible from any browser
- **noVNC** — Direct VNC access via browser (WebSocket, no install needed)
- **VM Lifecycle** — Create, start, stop, delete virtual machines
- **Multi-VM** — Manage multiple VMs simultaneously
- **QEMU + QMP** — Powered by QEMU's native management protocol

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 / Flask |
| Frontend | Vanilla JS + noVNC |
| Virtualization | QEMU (qemu-system-x86_64) |
| Protocol | VNC over WebSocket |

## Architecture

```
browser (noVNC) <--WebSocket--> Flask backend <--> QEMU (VNC + QMP)
```

## Quick Start

```bash
# Install dependencies
pip install flask qemu-utils

# Start the server
cd webvm
python src/app.py

# Open http://localhost:5000 in your browser
```

## Requirements

- Python 3.10+
- QEMU 8.0+ (qemu-system-x86, qemu-img)
- Linux (KVM support recommended)
- Modern browser (Chrome, Firefox, Safari, Edge)

## License

MIT
