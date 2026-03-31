"""
WebVM — Browser-based QEMU Virtual Machine Manager

This module is the main Flask application entry point. It provides:
- Web UI routes (HTML templates)
- REST API for VM lifecycle management
- OS catalog API for dynamic OS version dropdowns
- ISO upload handling

All API endpoints return JSON. All UI routes return rendered HTML templates.
"""

from flask import Flask, jsonify, request, render_template

from .config import HOST, PORT, DEBUG, VM_DIR, ISO_DIR
from .vm_manager import VMManager
from .os_catalog import all_categories, all_versions


def create_app():
    """
    Application factory. Creates and configures the Flask app.

    Returns:
        Flask: Configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder="../web/templates",
        static_folder="../web/static",
    )
    app.secret_key = __import__("os").urandom(32)

    # Store VMManager instance on app context for access in routes
    app.vm_mgr = VMManager()

    _register_routes(app)
    return app


def _register_routes(app: Flask):
    """
    Register all web and API routes on the Flask app.

    Args:
        app: Flask application instance.
    """

    # ── Web UI routes ──────────────────────────────────────────────────────

    @app.route("/")
    def index():
        """VM dashboard — list all VMs with status."""
        return render_template("index.html")

    @app.route("/vm/<name>")
    def vm_detail(name: str):
        """
        VM detail page — shows VM info and embeds noVNC screen.

        Args:
            name: VM name from URL path.
        """
        vm = app.vm_mgr.get_vm(name)
        if not vm:
            return "VM not found", 404
        return render_template("vm.html", vm=vm)

    @app.route("/create")
    def create_page():
        """New VM creation form page."""
        return render_template("create.html")

    # ── REST API: VM management ───────────────────────────────────────────

    @app.route("/api/vms")
    def api_list():
        """
        List all VMs with current status.
        GET /api/vms
        """
        return jsonify(app.vm_mgr.list_vms())

    @app.route("/api/vm/<name>", methods=["GET"])
    def api_get(name: str):
        """
        Get a single VM's configuration and status.
        GET /api/vm/:name
        """
        vm = app.vm_mgr.get_vm(name)
        if not vm:
            return jsonify({"error": "VM not found"}), 404
        return jsonify(vm)

    @app.route("/api/vm", methods=["POST"])
    def api_create():
        """
        Create a new VM and allocate its disk image.
        POST /api/vm
        Body: JSON with name, os_category, os_version, ram, vcpu, disk_size, iso, boot
        """
        data = request.get_json() or {}

        # Validate required fields
        required = ["name", "os_category", "os_version"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        try:
            vm = app.vm_mgr.create_vm(
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
        """
        Delete a VM and its disk image (must be stopped first).
        DELETE /api/vm/:name
        """
        if app.vm_mgr.get_vm(name) is None:
            return jsonify({"error": "VM not found"}), 404
        if app.vm_mgr.delete_vm(name):
            return jsonify({"result": "deleted"})
        return jsonify({"error": "Failed to delete VM"}), 500

    @app.route("/api/vm/<name>/start", methods=["POST"])
    def api_start(name: str):
        """
        Start a stopped VM.
        POST /api/vm/:name/start
        """
        if app.vm_mgr.get_vm(name) is None:
            return jsonify({"error": "VM not found"}), 404
        if app.vm_mgr.start_vm(name):
            return jsonify({"result": "started"})
        return jsonify({"error": "Failed to start VM"}), 500

    @app.route("/api/vm/<name>/stop", methods=["POST"])
    def api_stop(name: str):
        """
        Stop a running VM gracefully via QMP, then force-kill if needed.
        POST /api/vm/:name/stop
        """
        if app.vm_mgr.get_vm(name) is None:
            return jsonify({"error": "VM not found"}), 404
        if app.vm_mgr.stop_vm(name):
            return jsonify({"result": "stopped"})
        return jsonify({"error": "Failed to stop VM"}), 500

    @app.route("/api/vm/<name>/reboot", methods=["POST"])
    def api_reboot(name: str):
        """
        Reboot a VM via QMP system_reset command.
        POST /api/vm/:name/reboot
        """
        if app.vm_mgr.get_vm(name) is None:
            return jsonify({"error": "VM not found"}), 404
        if app.vm_mgr.reboot_vm(name):
            return jsonify({"result": "rebooted"})
        return jsonify({"error": "Failed to reboot VM"}), 500

    @app.route("/api/vm/<name>/status")
    def api_status(name: str):
        """
        Get current VM status (running / stopped / not_found).
        GET /api/vm/:name/status
        """
        status = app.vm_mgr.get_status(name)
        return jsonify({"name": name, "status": status})

    # ── REST API: OS catalog ───────────────────────────────────────────────

    @app.route("/api/os/categories")
    def api_categories():
        """
        List all OS categories (Linux, Windows, macOS, Other).
        GET /api/os/categories
        """
        cats = []
        for c in all_categories():
            cats.append({"id": c.id, "name": c.name})
        return jsonify(cats)

    @app.route("/api/os/versions/<category_id>")
    def api_versions(category_id: str):
        """
        List all OS versions for a given category.
        Used to populate the cascading dropdown on the create form.
        GET /api/os/versions/:category_id
        """
        versions = all_versions(category_id)
        return jsonify([{"id": v.id, "name": v.name} for v in versions])

    # ── REST API: ISO management ───────────────────────────────────────────

    @app.route("/api/isos", methods=["GET"])
    def api_list_isos():
        """
        List all ISO files in the ISO storage directory.
        GET /api/isos
        """
        isos = []
        for f in ISO_DIR.iterdir():
            if f.suffix.lower() in (".iso", ".img"):
                isos.append({"name": f.name, "path": str(f)})
        return jsonify(isos)

    @app.route("/api/iso/upload", methods=["POST"])
    def api_upload_iso():
        """
        Upload an ISO file to the server.
        POST /api/iso/upload
        Multipart form with 'file' field.
        """
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        filename = __import__("pathlib").Path(file.filename).name
        dest = ISO_DIR / filename
        file.save(dest)
        return jsonify({"name": filename, "path": str(dest)})


# Module-level app instance for `flask --app src.app` usage
app = create_app()


if __name__ == "__main__":
    import os
    os.makedirs(VM_DIR, exist_ok=True)
    os.makedirs(ISO_DIR, exist_ok=True)
    app.run(host=HOST, port=PORT, debug=DEBUG)
