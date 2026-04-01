# WebVM Installation Guide

## Prerequisites

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Host OS | Ubuntu 20.04+, Debian 11+, Fedora 38+ | Ubuntu 22.04 / 24.04 LTS |
| CPU | x86_64 with VT-x / AMD-V (KVM support) | Modern multi-core (e.g. i5-1240P, Ryzen 7 5800H) |
| RAM | 4 GB | 16 GB+ |
| Disk | 20 GB free | SSD, 100 GB+ |
| QEMU | 8.0+ | 8.2+ |
| Python | 3.10+ | 3.12+ |
| Browser | Chrome 90+, Firefox 88+, Edge 90+ | Chrome / Firefox (latest) |

### Check KVM availability

KVM hardware acceleration is required for acceptable VM performance.

```bash
# Check if KVM is available
ls /dev/kvm

# If not found, enable in BIOS/UEFI, then install:
sudo apt install qemu-kvm

# Add your user to the kvm group (avoids permission errors)
sudo usermod -aG kvm $USER
# Then log out and back in for group membership to take effect
```

### Check QEMU version

```bash
qemu-system-x86_64 --version
# Must be ≥ 8.0.0 for native WebSocket VNC support
```

---

## Quick Start (One-Click Installer)

The fastest way to get running:

```bash
git clone https://github.com/<your-username>/webvm.git
cd webvm
chmod +x setup.sh
./setup.sh
```

The installer will:
1. Install all system dependencies (apt)
2. Install Python dependencies
3. Initialize the noVNC submodule
4. Enable the per-user systemd service (auto-start on login)
5. Start WebVM immediately

Then open **http://\<your-server-ip\>:5000** in your browser.

---

## Manual Installation

### Step 1 — Install System Dependencies

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install -y \
    python3 \
    python3-flask \
    python3-venv \
    qemu-system-x86 \
    qemu-utils \
    git \
    curl \
    socat
```

**Fedora:**

```bash
sudo dnf install -y \
    python3 \
    python3-flask \
    qemu-system-x86 \
    qemu-img \
    git \
    curl \
    socat
```

### Step 2 — Clone the Repository

```bash
git clone https://github.com/<your-username>/webvm.git
cd webvm
```

### Step 3 — Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

**requirements.txt contents:**
```
flask>=3.0.0
```

Flask is the only runtime Python dependency. All other modules are from the Python standard library.

### Step 4 — Initialize noVNC Submodule

```bash
git submodule update --init --recursive
```

To update noVNC later:
```bash
cd web/static/js/novnc
git checkout master
git pull
cd ../..
```

### Step 5 — Create Required Directories

WebVM creates its data directories automatically on first run. For reference:

```
~/.webvm/
├── vms/    # VM configs and disk images
└── isos/   # ISO files
```

### Step 6 — Start WebVM

```bash
# From the webvm directory
python3 -m flask --app src.app run --host 0.0.0.0 --port 5000
```

Or with the virtual environment activated:
```bash
source venv/bin/activate
flask --app src.app run --host 0.0.0.0 --port 5000
```

Open **http://\<your-server-ip\>:5000** in your browser.

---

## Running as a Systemd Service (Recommended)

Running as a systemd user service gives you:
- **Auto-start on login** — WebVM starts when you log in
- **Auto-restart on crash** — Failed unexpectedly? systemd brings it back within 5 seconds
- **No root required** — Runs in your user session

### Per-User Service (no root required)

```bash
# Create the service directory if it doesn't exist
mkdir -p ~/.config/systemd/user

# Copy the service file
cp contrib/webvm.service ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Enable and start (starts on every login)
systemctl --user enable --now webvm

# Check status
systemctl --user status webvm
```

### System-Wide Service (starts before login, root required)

```bash
sudo cp contrib/webvm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webvm
sudo systemctl start webvm
sudo systemctl status webvm
```

### Service Logs

```bash
# Per-user service logs
journalctl --user -u webvm -f

# System-wide service logs
sudo journalctl -u webvm -f
```

---

## Quickemu Integration (Auto-Download OS Images)

WebVM can automatically download OS installation ISOs using [quickemu](https://github.com/quickemu-project/quickemu), eliminating the need to manually find and upload ISO files.

### Install Quickemu

```bash
# Ubuntu / Debian
sudo apt install quickemu

# Or via upstream installer (works on any Linux)
git clone https://github.com/quickemu-project/quickemu.git
cd quickemu
sudo ./quickemu --install
```

Verify:
```bash
quickget --version
quickget --list | head -20
```

When quickemu is installed, the VM creation form will offer a "Download" option for each supported OS. WebVM will:
1. Run `quickget --download <os> <release>` in the background
2. Track download progress by monitoring the ISO file size
3. Display real-time progress (percentage, downloaded/total, speed)
4. Auto-attach the ISO to the VM once download completes

---

## Firewall Configuration

WebVM listens on port **5000** by default. To access from other devices on your LAN, ensure the port is allowed:

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 5000/tcp

# Firewalld (Fedora)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

To use a non-default port, edit `src/config.py` and change `PORT = 5000`.

---

## Production Deployment

The built-in Flask development server is not suitable for production. For a homelab single-user deployment, the systemd service approach is sufficient. For higher concurrency, use gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 src.app:app
```

For HTTPS (required if accessing over the internet), place behind a reverse proxy:

```
Browser ──HTTPS──► nginx ──HTTP──► gunicorn:5000
```

Or use Cloudflare Tunnel / Tailscale to avoid exposing port 5000 to the internet entirely.

---

## Troubleshooting

### `qemu-system-x86_64: command not found`

```bash
sudo apt install qemu-system-x86 qemu-utils
```

### KVM permission denied

```bash
# Check if your user is in the kvm group
groups $USER

# Add if missing
sudo usermod -aG kvm $USER
# Then log out and back in
```

### Port 5000 already in use

```bash
# Find the conflicting process
sudo lsof -i :5000

# Change WebVM to use a different port
# Edit src/config.py: PORT = 8080
```

### noVNC shows "Disconnected" immediately

The VM likely failed to start. Check:
```bash
ps aux | grep qemu
journalctl --user -u webvm -n 50
```

### VM is very slow (KVM not working)

```bash
# Verify KVM is actually being used
ps aux | grep qemu | grep kvm
# Should show "-enable-kvm" in the QEMU args

# If not, check /dev/kvm permissions
ls -la /dev/kvm
```

### WebVM dashboard shows VMs but status is always "stopped"

The VM process may have crashed. Check:
```bash
ls -la ~/.webvm/vms/*.pid
cat ~/.webvm/vms/*.pid  # Check if PID exists
kill -0 $(cat ~/.webvm/vms/vmname.pid)  # Check if process alive
```

### ISO download progress not updating

The background download task may have been lost after a Flask restart. Downloads are tracked via marker files in `~/.webvm/isos/.download_*.start`. If the marker is gone but curl is still running, the frontend will show 0% until the download completes.

---

## Uninstall

```bash
# Stop and disable the service
systemctl --user stop webvm
systemctl --user disable webvm

# Remove service file
rm ~/.config/systemd/user/webvm.service

# Optionally remove data
rm -rf ~/.webvm

# Optionally remove the repository
cd .. && rm -rf webvm
```
