# User Guide

> How to use WebVM to create and manage virtual machines from your browser.

## Accessing WebVM

WebVM is accessed through a web browser on any device in your local network.

```
http://<server-ip>:5000
```

The server IP is printed when WebVM starts, e.g. `http://192.168.1.24:5000`.

## Dashboard

The dashboard (`/`) shows all your virtual machines as cards:

- **Name** — VM identifier
- **Status badge** — green `RUNNING` or gray `STOPPED`
- **OS** — category and version (e.g., "Linux / Ubuntu 24.04 LTS")
- **Resources** — RAM and vCPU allocation
- **Actions** — Start / Stop / Reboot / View / Delete

## Creating a VM

1. Click **+ New VM** in the top navigation
2. Fill in the form:
   - **VM Name** — a unique identifier (no spaces)
   - **OS Category** — Linux, Windows, macOS, or Other
   - **OS Version** — the specific release (auto-loaded after category selection)
   - **ISO File** — path to an installation ISO (optional, leave blank for disk-only boot)
   - **RAM** — memory in MB (default 4096 MB)
   - **vCPUs** — number of virtual CPUs (default 2)
   - **Disk Size** — disk image size (default 64G, e.g. `128G`, `256G`)
   - **Boot Device** — CD/ISO (install from ISO) or Disk (boot from disk image)
3. Click **Create VM**

The VM will appear in the dashboard in `STOPPED` state.

## Starting and Accessing a VM

1. Click **View** on the VM card
2. Click **Start** — the VM boots up
3. The noVNC screen appears and shows the VM's display
4. Interact with the VM using your mouse and keyboard directly in the browser

> **Note:** noVNC is a pure browser VNC client — no plugins or software installation needed on the client device.

## Stopping a VM

From the VM detail page, click **Stop**. The VM shuts down gracefully.
If it doesn't respond within a few seconds, use **Reboot** or click **Stop** again
to force-terminate.

## Deleting a VM

1. Click **Delete** on the VM card or detail page
2. Confirm the deletion in the dialog
3. The VM, its disk image, and all associated files are permanently removed

> **Warning:** This cannot be undone. Make sure to back up any data inside the VM before deleting.

## Uploading ISO Files

1. Navigate to the VM creation page (`/create`)
2. Enter the full path to your ISO file in the **ISO File** field
3. Alternatively, place ISO files in `~/.webvm/isos/` on the server

## Keyboard Shortcuts (noVNC)

| Shortcut | Action |
|----------|--------|
| Ctrl+Alt+Del | Send Ctrl+Alt+Del to VM |
| Ctrl+Alt+Backspace | Send Ctrl+Alt+Backspace |
| Ctrl+Alt+F | Toggle fullscreen |
| Alt+Tab | Switch windows (host ↔ VM) — use noVNC menu first |

## Accessing noVNC Settings

Click the noVNC toolbar at the top of the VM screen to access:
- **Connection info** — shows connected host/port
- **Clipboard** — copy text between host and VM
- **Fullscreen** toggle
- **Disconnect** button

## Troubleshooting

### VM screen is blank
- Wait 10–20 seconds after clicking Start — VMs take time to boot
- Make sure the ISO or boot device is correct

### noVNC shows "Disconnected"
- The VM may have crashed — check `ps aux | grep qemu` on the server
- Try stopping and restarting the VM
- Check the VNC port is not blocked by a firewall

### Network access doesn't work from other devices
- Make sure the Flask server is started with `--host 0.0.0.0` (default)
- Check the server's firewall: `sudo ufw allow 5000/tcp`
- Ensure client device is on the same network

### VM is very slow
- Enable KVM acceleration: `-enable-kvm` flag (already enabled by default)
- Increase RAM and vCPU in VM settings
- Use a local disk (not NFS/network storage) for the disk image
