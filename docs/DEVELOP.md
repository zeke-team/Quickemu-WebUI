# Developer's Guide

> How to set up a development environment and understand the codebase.

## Prerequisites

```bash
# Ubuntu / Debian
sudo apt install python3-flask qemu-system-x86 qemu-utils git

# Clone the repository
git clone https://github.com/<your-username>/webvm.git
cd webvm

# Initialize noVNC submodule
git submodule update --init --recursive
```

## Running Locally

```bash
# Development (with auto-reload)
python3 -m flask --app src.app run --host 0.0.0.0 --port 5000 --debug

# Or directly
cd src
python3 app.py
```

Visit `http://localhost:5000` in your browser.

## Project Structure

```
webvm/
├── src/                      # Python package
│   ├── app.py                 # Flask application + all HTTP routes
│   ├── config.py             # Path and runtime configuration
│   ├── os_catalog.py          # OS category and version definitions
│   ├── qmp_client.py          # QEMU Monitor Protocol (QMP) client
│   ├── qemu_runner.py          # QEMU process spawner and manager
│   └── vm_manager.py          # VM CRUD + lifecycle operations
├── web/
│   ├── static/
│   │   ├── css/style.css      # Dark-theme UI styles
│   │   ├── js/
│   │   │   ├── app.js         # Dashboard AJAX + VM card rendering
│   │   │   └── novnc/         # noVNC library (git submodule)
│   └── templates/
│       ├── base.html          # Page skeleton with nav
│       ├── index.html         # VM list dashboard
│       ├── create.html        # New VM creation form
│       └── vm.html            # VM detail + embedded noVNC screen
├── tests/
├── docs/
│   ├── API.md                 # REST API reference
│   ├── DEVELOP.md              # This file
│   ├── INSTALL.md              # Installation guide
│   └── USAGE.md               # User guide
└── SPEC.md                    # Feature specification
```

## Key Design Decisions

### Why QEMU native WebSocket VNC?

QEMU 8.0+ supports `-vnc websocket=on,port=N` which exposes VNC directly over WebSocket.
No `websockify` proxy is needed. The browser connects to `ws://host:port` and noVNC
handles the protocol translation to canvas drawing.

### Why QMP over libvirt?

libvirt adds significant overhead and requires a running libvirtd daemon.
QMP (QEMU Monitor Protocol) communicates directly with the QEMU process via a Unix socket,
giving us fine-grained control with minimal dependencies.

### VM Storage Layout

```
~/.webvm/               # WebVM root
├── vms/
│   ├── my-vm.json     # VM configuration (JSON)
│   ├── my-vm.qcow2    # VM disk image
│   ├── my-vm.pid      # QEMU process ID
│   └── my-vm-qmp.sock # QMP control socket
└── isos/              # Uploaded ISO files
```

### noVNC Integration

noVNC is included as a git submodule from `https://github.com/novnc/noVNC`.
The `vm.html` template loads it as an ES6 module:

```javascript
import RFB from "/static/js/novnc/core/rfb.js";
const rfb = new RFB(canvasElement, "ws://host:port");
```

## Adding a New OS to the Catalog

Edit `src/os_catalog.py`. Add a new `OSVersion` entry to the appropriate category:

```python
"linux": OSCategory(
    id="linux",
    name="Linux",
    versions=[
        # ... existing versions ...
        OSVersion("my-distro-24", "My Distro 24 LTS"),
    ],
),
```

## Adding a New REST Endpoint

1. Add the route in `src/app.py` under the `REST API` section
2. Add tests in `tests/`
3. Document in `docs/API.md`
4. Update `SPEC.md` if it introduces new behavior

## Code Style

- Python: PEP 8, type hints where helpful
- JS: ES6+, no framework (vanilla)
- CSS: CSS custom properties (variables), dark theme

## Testing

```bash
# Run all tests
python3 -m pytest tests/

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

## Debugging QEMU Issues

```bash
# See QEMU command for a VM
cat ~/.webvm/vms/<vm-name>.conf

# View QEMU logs (if logging enabled)
cat ~/.webvm/vms/<vm-name>.log

# Manually connect to QMP socket
echo '{"execute":"qmp-capabilities"}' | nc -U ~/.webvm/vms/<vm-name>-qmp.sock

# Check if QEMU process is running
cat ~/.webvm/vms/<vm-name>.pid
ps aux | grep qemu
```
