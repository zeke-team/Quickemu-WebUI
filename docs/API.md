# WebVM REST API Reference

> Base URL: `http://<server>:5000/api`

All endpoints return `Content-Type: application/json` unless noted.
All request bodies for POST/PATCH must be `Content-Type: application/json`.

---

## VM Management

### List all VMs
```
GET /vms
```

**Response** `200`
```json
[
  {
    "boot": "cd",
    "disk": "/home/user/.webvm/vms/my-ubuntu.qcow2",
    "disk_size": "64G",
    "iso": "",
    "name": "my-ubuntu",
    "os_category": "linux",
    "os_version": "ubuntu-24.04",
    "ram": "4096",
    "status": "running",
    "vcpu": 2,
    "vnc_port": 5930
  }
]
```

---

### Get a VM
```
GET /vm/:name
```

**Response** `200` — VM object (same structure as above)  
**Response** `404` — `{ "error": "VM not found" }`

---

### Create a VM
```
POST /vm
```

**Request body**
```json
{
  "name": "my-ubuntu",
  "os_category": "linux",
  "os_version": "ubuntu-24.04",
  "iso": "/path/to/ubuntu-24.04.iso",
  "ram": "4096",
  "vcpu": 2,
  "disk_size": "64G",
  "boot": "cd"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Unique VM identifier (no spaces) |
| `os_category` | string | Yes | — | `linux`, `windows`, `macos`, or `other` |
| `os_version` | string | Yes | — | e.g. `ubuntu-24.04`, `windows-11`, `sequoia` |
| `iso` | string | No | `""` | Absolute path to ISO file |
| `ram` | string | No | `"4096"` | Memory in MB (e.g. `"8192"`) |
| `vcpu` | integer | No | `2` | Number of virtual CPUs |
| `disk_size` | string | No | `"64G"` | Disk size (e.g. `"128G"`) |
| `boot` | string | No | `"cd"` | Boot device: `"cd"` (from ISO) or `"disk"` |

**Response** `201` — Created VM object  
**Response** `409` — `{ "error": "VM 'name' already exists" }`  
**Response** `400` — `{ "error": "Missing field: name" }`

---

### Delete a VM
```
DELETE /vm/:name
```

> VM must be stopped before deletion. The disk image is permanently removed.

**Response** `200` — `{ "result": "deleted" }`  
**Response** `404` — `{ "error": "VM not found" }`

---

### Start a VM
```
POST /vm/:name/start
```

**Response** `200` — `{ "result": "started" }`  
**Response** `404` — `{ "error": "VM not found" }`  
**Response** `500` — `{ "error": "Failed to start VM" }`

---

### Stop a VM
```
POST /vm/:name/stop
```

Graceful shutdown via QMP, then SIGTERM → SIGKILL if needed.

**Response** `200` — `{ "result": "stopped" }`  
**Response** `404` — `{ "error": "VM not found" }`

---

### Reboot a VM
```
POST /vm/:name/reboot
```

Sends QMP `system_reset` — immediate reboot without disk I/O.

**Response** `200` — `{ "result": "rebooted" }`  
**Response** `404` — `{ "error": "VM not found" }`

---

### Get VM Status
```
GET /vm/:name/status
```

**Response** `200`
```json
{ "name": "my-ubuntu", "status": "running" }
```

`status` is one of: `running` | `stopped` | `not_found`

---

## OS Catalog

### List OS Categories
```
GET /os/categories
```

**Response** `200`
```json
[
  { "id": "linux",   "name": "Linux" },
  { "id": "windows", "name": "Windows" },
  { "id": "macos",   "name": "macOS" },
  { "id": "other",   "name": "Other / Custom" }
]
```

---

### List OS Versions for a Category
```
GET /os/versions/:category_id
```

**Example:** `GET /os/versions/macos`

**Response** `200`
```json
[
  { "id": "tahoe",   "name": "macOS Tahoe (16)" },
  { "id": "sequoia", "name": "macOS Sequoia (15)" },
  { "id": "sonoma",  "name": "macOS Sonoma (14)" },
  ...
]
```

---

## ISO Management

### List Available ISOs
```
GET /isos
```

Lists files in `~/.webvm/isos/`.

**Response** `200`
```json
[
  { "name": "ubuntu-24.04.iso", "path": "/home/user/.webvm/isos/ubuntu-24.04.iso" }
]
```

---

### Upload an ISO
```
POST /iso/upload
Content-Type: multipart/form-data
```

| Field | Type | Description |
|-------|------|-------------|
| `file` | binary | ISO or IMG file |

**Response** `200` — `{ "name": "ubuntu-24.04.iso", "path": "/home/user/.webvm/isos/ubuntu-24.04.iso" }`  
**Response** `400` — `{ "error": "No file selected" }`
