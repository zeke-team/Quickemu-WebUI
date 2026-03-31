# Installation Guide

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Linux (Ubuntu 20.04+, Debian 11+) | Ubuntu 22.04 / 24.04 LTS |
| CPU | x86_64 with VT-x / AMD-V | Modern multi-core CPU |
| RAM | 4 GB | 16 GB+ |
| Disk | 20 GB free | SSD, 100 GB+ |
| QEMU | 8.0+ | 8.2+ |
| Python | 3.10+ | 3.12+ |
| Browser | Any modern browser | Chrome / Firefox / Edge |

> **KVM** (Kernel-based Virtual Machine) is required for hardware-accelerated virtualization. Check with: `ls /dev/kvm`

## Ubuntu / Debian

```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3-flask qemu-system-x86 qemu-utils git

# Clone the repository
git clone https://github.com/<your-username>/webvm.git
cd webvm

# Initialize noVNC submodule
git submodule update --init --recursive

# Start WebVM
python3 -m flask --app src.app run --host 0.0.0.0 --port 5000
```

Open `http://<your-ip>:5000` in your browser.

## Start on Boot (systemd)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/webvm.service
```

```
[Unit]
Description=WebVM — Browser-based VM management
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/webvm
ExecStart=/usr/bin/python3 -m flask --app src.app run --host 0.0.0.0 --port 5000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable webvm
sudo systemctl start webvm
```

Check status:
```bash
sudo systemctl status webvm
```

## Firewall

Allow WebVM port (default 5000):

```bash
# UFW
sudo ufw allow 5000/tcp

# or firewalld
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

## noVNC Submodule

The project uses noVNC as a git submodule for browser-based VNC access.
After cloning, always run:

```bash
git submodule update --init --recursive
```

To update noVNC to the latest version later:

```bash
cd web/static/js/novnc
git checkout master
git pull
```

## Production Deployment

The built-in Flask development server is **not** suitable for production.
Use a proper WSGI server:

```bash
# Install gunicorn
pip3 install gunicorn

# Run with gunicorn (4 workers)
gunicorn -w 4 -b 0.0.0.0:5000 src.app:app
```

Or behind a reverse proxy (nginx + gunicorn) for HTTPS support.

## Troubleshooting

### `qemu-system-x86_64: command not found`
```bash
sudo apt install qemu-system-x86
```

### KVM not available
```bash
# Check if KVM is available
ls /dev/kvm

# If not, enable in BIOS/UEFI, then:
sudo apt install qemu-kvm
```

### Permission denied on `/dev/kvm`
```bash
sudo usermod -aG kvm $USER
# Then log out and back in
```

### Port 5000 already in use
```bash
# Find and kill the process using port 5000
sudo lsof -i :5000
# or change port with --port 8080
```
