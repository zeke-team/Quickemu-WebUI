/**
 * WebVM — Dashboard JavaScript
 *
 * Handles:
 * - Fetching and rendering the VM list on the dashboard
 * - Per-VM action buttons (start, stop, reboot, delete)
 * - Escape HTML to prevent XSS in VM names
 *
 * The dashboard polls on load only. For real-time status updates,
 * a polling interval or WebSocket notification could be added.
 */

const API = "";  // Same-origin; Flask serves at the same host

/**
 * Make an authenticated JSON fetch request.
 * @param {string} url - API endpoint path (e.g. "/api/vms")
 * @param {object} options - fetch options (method, headers, body, etc.)
 * @returns {Promise<object>} parsed JSON response
 */
async function fetchJSON(url, options = {}) {
    const res = await fetch(API + url, options);
    if (!res.ok) {
        // Try to extract error message from JSON body
        const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(err.error || res.statusText);
    }
    return res.json();
}

/**
 * Escape HTML special characters to prevent XSS when rendering
 * VM names (which come from user input) into innerHTML.
 * @param {string} s - Raw string
 * @returns {string} HTML-escaped string
 */
function esc(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

/**
 * Build an HTML card element for a single VM.
 * @param {object} vm - VM config object (from API)
 * @returns {string} HTML string
 */
function vmCard(vm) {
    const meta = `${vm.os_category} / ${vm.os_version} · ${vm.ram}MB RAM · ${vm.vcpu} vCPU · ${vm.disk_size}`;

    const actions = vm.status === "stopped"
        ? `<button class="btn btn-success btn-sm" onclick="doAction('${esc(vm.name)}','start')">Start</button>`
        : `<button class="btn btn-danger btn-sm" onclick="doAction('${esc(vm.name)}','stop')">Stop</button>
           <button class="btn btn-secondary btn-sm" onclick="doAction('${esc(vm.name)}','reboot')">Reboot</button>`;

    return `
    <div class="vm-card">
        <div class="vm-card-header">
            <h3>${esc(vm.name)}</h3>
            <span class="status-badge status-${vm.status}">${vm.status}</span>
        </div>
        <div class="vm-card-meta">${meta}</div>
        <div class="vm-card-actions">
            ${actions}
            <a href="/vm/${esc(vm.name)}" class="btn btn-secondary btn-sm">View</a>
            <button class="btn btn-danger-outline btn-sm" onclick="doDelete('${esc(vm.name)}')">Delete</button>
        </div>
    </div>`;
}

/**
 * Fetch and render the VM list into the #vm-list element.
 * Called on page load and after any action completes.
 */
async function loadVMs() {
    const el = document.getElementById("vm-list");
    if (!el) return;  // Not on the dashboard page

    try {
        const vms = await fetchJSON("/api/vms");
        if (vms.length === 0) {
            el.innerHTML = `<p style="color:var(--text-muted)">No VMs yet. <a href="/create">Create one</a>.</p>`;
        } else {
            el.innerHTML = vms.map(vmCard).join("");
        }
    } catch (err) {
        el.innerHTML = `<p class="error-msg">Failed to load VMs: ${esc(err.message)}</p>`;
    }
}

/**
 * Trigger a VM action (start/stop/reboot) then refresh the list.
 * @param {string} name - VM name
 * @param {string} action - Action name (start, stop, reboot)
 */
async function doAction(name, action) {
    try {
        await fetchJSON(`/api/vm/${name}/${action}`, { method: "POST" });
        await loadVMs();  // Refresh to show updated status
    } catch (err) {
        alert(`Action failed: ${err.message}`);
    }
}

/**
 * Delete a VM after user confirmation.
 * @param {string} name - VM name
 */
async function doDelete(name) {
    if (!confirm(`Delete VM "${name}"? This will remove the disk image and cannot be undone.`)) {
        return;
    }
    try {
        await fetchJSON(`/api/vm/${name}`, { method: "DELETE" });
        await loadVMs();
    } catch (err) {
        alert(`Delete failed: ${err.message}`);
    }
}

// Load VM list when the dashboard DOM is ready
document.addEventListener("DOMContentLoaded", loadVMs);
