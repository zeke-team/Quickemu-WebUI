# WebVM User Guide

> **Prerequisite:** WebVM must be installed and running. See [INSTALL.md](./INSTALL.md) for setup instructions.

---

## Accessing WebVM

Open a web browser and navigate to:

```
http://<server-ip>:5000
```

Example: `http://192.168.1.24:5000`

The server IP is the IP address of the machine running WebVM. Find it with:
```bash
ip addr show | grep "inet "     # Linux
```

---

## Dashboard

The dashboard (`/`) displays all your virtual machines as cards:

| Field | Description |
|-------|-------------|
| **Name** | VM identifier |
| **Status badge** | 🟢 Running (green) or ⚫ Stopped (gray) |
| **OS** | Category and version (e.g., "Linux / Ubuntu 24.04 LTS") |
| **Resources** | RAM and vCPU allocation |
| **Actions** | Start / Stop / Reboot / View / Delete |

The dashboard auto-refreshes every 5 seconds to update VM status without a page reload.

---

## Creating a VM

### Step 1 — Open the Create Form

Click **+ New VM** in the top navigation bar.

### Step 2 — Fill in VM Details

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| **VM Name** | Yes | Unique identifier, lowercase, no spaces | — |
| **OS Category** | Yes | Linux, Windows, macOS, Other | — |
| **OS Version** | Yes | Specific release (auto-loaded after category) | — |
| **RAM** | No | Memory in MB | 4096 |
| **vCPUs** | No | Number of virtual CPUs | 2 |
| **Disk Size** | No | Disk image size (e.g. `64G`, `128G`) | 64G |
| **Boot Device** | No | `CD/ISO` to boot from ISO, `Disk` to boot from disk | CD/ISO |
| **ISO File** | No | Path to an ISO on the server (leave blank to auto-download) | — |

### Step 3 — Auto-Download OS Image (Recommended)

Leave the **ISO File** field blank to let WebVM automatically download the OS installation image via quickemu/quickget.

When you submit the form:
1. The VM is created and appears in the dashboard immediately
2. A progress bar shows the download status in real time:
   - Progress percentage
   - Downloaded / Total size
   - Current download speed
3. Once the ISO download completes, the VM is ready to start

> **Note:** The first OS download may take several minutes depending on the ISO size and your internet speed. Ubuntu 24.04 Desktop is ~5.1 GB. Windows 11 is ~7 GB. macOS ISOs are typically 12–14 GB.

### Step 4 — Start the VM

Once the VM appears in "Stopped" state:
1. Click **View** on the VM card
2. Click **Start** — the VM boots up
3. The noVNC console appears and displays the VM's screen

---

## Using the noVNC Console

The noVNC console embeds a full VM desktop directly in your browser. It is a pure JavaScript VNC client — no plugins, no software installation needed.

### Mouse and Keyboard

- Click inside the console area to capture mouse and keyboard input
- Move the mouse and type as normal inside the VM
- Press **Ctrl+Alt+Del** to send the secure attention sequence (Ctrl+Alt+Backspace for Ctrl+Alt+Break)

### Releasing Mouse/Keyboard

Move the mouse cursor to the **noVNC toolbar** at the top of the screen, then click outside the console area to release input.

### noVNC Toolbar

The top toolbar provides:
- **Connection status** — shows connected/disconnected state
- **Clipboard** — copy and paste text between your host and the VM
- **Fullscreen** — toggle fullscreen mode
- **Disconnect** — disconnect from the VM (does not stop the VM)

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Alt+Del | Send Ctrl+Alt+Del to VM |
| Ctrl+Alt+Backspace | Send Ctrl+Alt+Backspace |
| Ctrl+Alt+F | Toggle fullscreen |
| Ctrl+Alt+End | Disconnect |

---

## Stopping a VM

From the VM detail page, click **Stop**.

WebVM first attempts a **graceful shutdown** via the QMP protocol (equivalent to pressing the power button). If the VM does not shut down within 10 seconds, it falls back to SIGTERM, then SIGKILL.

> **Tip:** For Linux VMs, logging in and running `sudo shutdown -h now` or `sudo poweroff` inside the VM performs a clean shutdown and is preferable to forcing it off.

---

## Rebooting a VM

Click **Reboot** to send an ACPI reset signal to the VM. This is equivalent to pressing the physical reset button — the VM shuts down immediately and restarts without disk check (for most OSes).

---

## Deleting a VM

> ⚠️ **Warning: This permanently deletes the VM and all its data. This cannot be undone.**

1. Click **Delete** on the VM card or detail page
2. Confirm in the dialog
3. The VM and its disk image are permanently removed

The VM must be **stopped** before it can be deleted. Delete is disabled while the VM is running.

---

## ISO Download Progress

When creating a VM without specifying an ISO, WebVM automatically downloads the OS image in the background. The progress is displayed directly on the VM creation page and in the dashboard.

### Progress Indicator (on Create page)

- **Progress bar** — visual percentage
- **Downloaded / Total** — bytes transferred and expected total
- **Speed** — current download speed in MB/s or GB/s

### VM State During Download

The VM card in the dashboard shows the VM as "Stopped" during the download. The ISO is automatically attached and the VM becomes startable once download completes.

### Canceling a Download

You cannot cancel a download through the UI. To stop it manually:
```bash
# Find and kill the curl download process
ps aux | grep "[c]url.*ubuntu"
kill <PID>
```

---

## Uploading ISO Files Manually

If you already have an ISO file:

### Option A — Server Path

Enter the full path to the ISO in the **ISO File** field when creating the VM:
```
/home/username/Downloads/ubuntu-24.04-desktop-amd64.iso
```

### Option B — Upload via Web Form

(Not yet implemented — place ISOs in `~/.webvm/isos/` on the server instead)

### Option C — Copy to ISO Directory

```bash
# Copy ISO to WebVM's ISO directory
cp /path/to/your.iso ~/.webvm/isos/

# Verify it's visible in WebVM
ls ~/.webvm/isos/
```

Then create the VM and enter the path manually, or browse the list of existing ISOs.

---

## Switching Language

Click the **Language** dropdown in the top navigation bar and select your preferred language.

Currently supported:
- **English** (en) — default
- **简体中文** (zh_CN)

Language preference is saved in a cookie and persists across sessions.

---

## Network Access

By default, WebVM binds to `0.0.0.0:5000`, making it accessible from any device on your local network:

```
http://<webvm-server-ip>:5000
```

To access from outside your LAN:
- **Recommended:** Use Tailscale or Cloudflare Tunnel to create a private tunnel (no port forwarding needed)
- **Alternative:** Configure your router to port-forward port 5000 (not recommended for internet exposure without HTTPS)

---

## Monitoring VM Status

### Dashboard Auto-Refresh

The VM list on the dashboard polls the server every 5 seconds and updates status badges automatically. You do not need to manually refresh the page.

### API Status Check

```bash
# Check a specific VM's status via the API
curl http://localhost:5000/api/vm/my-ubuntu/status
# Returns: {"name": "my-ubuntu", "status": "running"}
```

### List All VMs via API

```bash
curl http://localhost:5000/api/vms | python3 -m json.tool
```

---

## Troubleshooting

### VM screen is completely black after starting

1. **Wait 10–30 seconds** — most OSes take time to boot to a visible screen
2. Check the boot device setting: if you created the VM without an ISO, make sure boot is set to `Disk`, not `CD/ISO`
3. Try stopping and restarting the VM

### noVNC shows "Disconnected" or "Connection refused"

The QEMU process may have crashed. Check:
```bash
ps aux | grep qemu
journalctl --user -u webvm -n 20
```

### VM starts but no screen appears in noVNC

1. Check the browser console (F12 → Console) for errors
2. Verify the VNC WebSocket port is reachable:
   ```bash
   curl -s --include \
       -H "Upgrade: websocket" \
       -H "Connection: Upgrade" \
       -H "Sec-WebSocket-Key: test" \
       http://localhost:5730
   ```
   A `101 Switching Protocols` response means WebSocket VNC is working.

### Network/internet not working inside the VM

1. Verify the VM is actually running (check dashboard)
2. From inside the VM, verify the network cable is connected and DHCP is enabled
3. Check the server's firewall: `sudo ufw status`
4. Try a live ISO (e.g., Ubuntu Try Mode) to confirm networking works at all

### VM is extremely slow

1. **Enable KVM** — the VM must have KVM acceleration enabled. Check:
   ```bash
   ps aux | grep qemu | grep kvm
   # If you don't see "-enable-kvm" in the output, KVM is not working
   ```
2. Increase RAM and vCPU in the VM settings
3. Move the disk image to a local SSD (not NFS/network storage)
4. Close other resource-intensive applications on the host

### Disk space running low

VM disk images grow dynamically (qcow2 format). The actual disk space used equals the data written inside the VM, not the declared size. To reclaim unused space:
```bash
# Compact the qcow2 image (from inside the VM first run a secure erase)
qemu-img convert -O qcow2 /path/to/vm.qcow2 /path/to/vm-compact.qcow2
```
