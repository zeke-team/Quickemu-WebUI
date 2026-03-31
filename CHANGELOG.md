# Changelog

All notable changes to WebVM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — YYYY-MM-DD

### Added

- **VM Dashboard** (`/`) — Grid of VM cards showing name, OS, status, RAM, vCPU, and action buttons
- **VM Creation Form** (`/create`) — Full form with cascading OS category → version dropdown
- **VM Detail Page** (`/vm/:name`) — VM info + embedded noVNC screen when running
- **REST API** — Full CRUD for VMs (`/api/vm`, `/api/vms`) plus start/stop/reboot/status
- **OS Catalog API** — `/api/os/categories` and `/api/os/versions/:id` for dynamic dropdown population
- **QEMU native WebSocket VNC** — QEMU 8.0+ `-vnc websocket=on` with no websockify proxy
- **noVNC integration** — ES6 module import of noVNC core for zero-plugin browser VNC
- **QMP client** — Unix socket JSON client for graceful VM shutdown and control
- **QEMU process runner** — KVM-accelerated daemonized QEMU with PID tracking
- **Flat-file VM storage** — JSON configs in `~/.webvm/vms/`, one file per VM
- **ISO upload endpoint** — `POST /api/iso/upload` for uploading installation ISOs
- **Comprehensive documentation** — README, SPEC.md, DEVELOP.md, INSTALL.md, USAGE.md, API.md
- **Code comments** — All Python modules documented with docstrings

### Features not yet implemented (see SPEC.md)

- [ ] Real-time VM status polling on dashboard
- [ ] VM snapshot support
- [ ] Live migration
- [ ] User authentication
- [ ] VM resource usage display (CPU/RAM while running)
- [ ] Desktop shortcut creation (quickemu-style)
