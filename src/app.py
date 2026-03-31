"""Flask web application and REST API for WebVM."""
import os
from pathlib import Path
from flask import Flask, jsonify, request, render_template, send_from_directory

from .config import HOST, PORT, DEBUG, VM_DIR, ISO_DIR
from .vm_manager import VMManager
from .os_catalog import all_categories, all_versions

app = Flask(__name__, template_folder="../web/templates", static_folder="../web/static")
app.secret_key = os.urandom(32)

vm_mgr = VMManager()


# ── Web UI ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/vm/<name>")
def vm_detail(name: str):
    vm = vm_mgr.get_vm(name)
    if not vm:
        return "VM not found", 404
    return render_template("vm.html", vm=vm)


@app.route("/create")
def create_page():
    return render_template("create.html")


# ── REST API ─────────────────────────────────────────────────────────────────

@app.route("/api/vms")
def api_list():
    return jsonify(vm_mgr.list_vms())


@app.route("/api/vm/<name>", methods=["GET"])
def api_get(name: str):
    vm = vm_mgr.get_vm(name)
    if not vm:
        return jsonify({"error": "VM not found"}), 404
    return jsonify(vm)


@app.route("/api/vm", methods=["POST"])
def api_create():
    data = request.get_json() or {}

    required = ["name", "os_category", "os_version"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        vm = vm_mgr.create_vm(
            name=data["name"],
            os_category=data["os_category"],
            os_version=data["os_version"],
            iso_path=data.get("iso", ""),
            disk_size=data.get("disk_size", "64G"),
            ram=data.get("ram", "4096"),
            vcpu=int(data.get("vcpu", 2)),
            boot=data.get("boot", "cd"),
        )
        return jsonify(vm), 201
    except FileExistsError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/vm/<name>", methods=["DELETE"])
def api_delete(name: str):
    if vm_mgr.get_vm(name) is None:
        return jsonify({"error": "VM not found"}), 404
    if vm_mgr.delete_vm(name):
        return jsonify({"result": "deleted"})
    return jsonify({"error": "Failed to delete VM"}), 500


@app.route("/api/vm/<name>/start", methods=["POST"])
def api_start(name: str):
    if vm_mgr.get_vm(name) is None:
        return jsonify({"error": "VM not found"}), 404
    if vm_mgr.start_vm(name):
        return jsonify({"result": "started"})
    return jsonify({"error": "Failed to start VM"}), 500


@app.route("/api/vm/<name>/stop", methods=["POST"])
def api_stop(name: str):
    if vm_mgr.get_vm(name) is None:
        return jsonify({"error": "VM not found"}), 404
    if vm_mgr.stop_vm(name):
        return jsonify({"result": "stopped"})
    return jsonify({"error": "Failed to stop VM"}), 500


@app.route("/api/vm/<name>/reboot", methods=["POST"])
def api_reboot(name: str):
    if vm_mgr.get_vm(name) is None:
        return jsonify({"error": "VM not found"}), 404
    if vm_mgr.reboot_vm(name):
        return jsonify({"result": "rebooted"})
    return jsonify({"error": "Failed to reboot VM"}), 500


@app.route("/api/vm/<name>/status")
def api_status(name: str):
    status = vm_mgr.get_status(name)
    return jsonify({"name": name, "status": status})


# ── OS Catalog API ─────────────────────────────────────────────────────────

@app.route("/api/os/categories")
def api_categories():
    cats = []
    for c in all_categories():
        cats.append({"id": c.id, "name": c.name})
    return jsonify(cats)


@app.route("/api/os/versions/<category_id>")
def api_versions(category_id):
    versions = all_versions(category_id)
    return jsonify([{"id": v.id, "name": v.name} for v in versions])


# ── ISO file handling ────────────────────────────────────────────────────────

@app.route("/api/isos", methods=["GET"])
def api_list_isos():
    isos = []
    for f in ISO_DIR.iterdir():
        if f.suffix.lower() in (".iso", ".img"):
            isos.append({"name": f.name, "path": str(f)})
    return jsonify(isos)


@app.route("/api/iso/upload", methods=["POST"])
def api_upload_iso():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = Path(file.filename).name
    dest = ISO_DIR / filename
    file.save(dest)
    return jsonify({"name": filename, "path": str(dest)})


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
