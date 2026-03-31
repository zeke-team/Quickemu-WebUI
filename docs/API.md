# WebVM API Reference

Base URL: `http://localhost:5000/api`

All endpoints return `application/json`.

## VM Management

### List all VMs
```
GET /vms
```
**Response**
```json
[
  {
    "name": "my-ubuntu",
    "os_type": "linux",
    "ram": "4096",
    "vcpu": 2,
    "disk": "/home/user/.webvm/vms/my-ubuntu.qcow2",
    "disk_size": "64G",
    "vnc_port": 5930,
    "status": "running"
  }
]
```

### Get a VM
```
GET /vm/:name
```
**Response** — Same structure as VM object above, or `404`.

### Create a VM
```
POST /vm
Content-Type: application/json

{
  "name": "my-ubuntu",
  "os_type": "linux",
  "iso": "/path/to/ubuntu.iso",
  "ram": "4096",
  "vcpu": 2,
  "disk_size": "64G",
  "boot": "cd"
}
```
**Response** `201` — Created VM object.

### Delete a VM
```
DELETE /vm/:name
```
**Response** `200` — `{ "result": "deleted" }`

### Start a VM
```
POST /vm/:name/start
```
**Response** `200` — `{ "result": "started" }`

### Stop a VM
```
POST /vm/:name/stop
```
**Response** `200` — `{ "result": "stopped" }`

### Reboot a VM
```
POST /vm/:name/reboot
```
**Response** `200` — `{ "result": "rebooted" }`

### Get VM status
```
GET /vm/:name/status
```
**Response**
```json
{ "name": "my-ubuntu", "status": "running" }
```

## ISO Management

### List ISOs
```
GET /isos
```
**Response**
```json
[
  { "name": "ubuntu-24.04.iso", "path": "/home/user/.webvm/isos/ubuntu-24.04.iso" }
]
```

### Upload ISO
```
POST /iso/upload
Content-Type: multipart/form-data

file: <binary>
```
**Response** `200` — `{ "name": "ubuntu-24.04.iso", "path": "/home/user/.webvm/isos/ubuntu-24.04.iso" }`
