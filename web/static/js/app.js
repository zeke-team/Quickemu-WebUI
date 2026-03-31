/**
 * WebVM — Dashboard JavaScript
 * Handles VM list rendering and API calls.
 */

const API = "";  // same origin

async function fetchJSON(url, options = {}) {
    const res = await fetch(API + url, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(err.error || res.statusText);
    }
    return res.json();
}

function vmCard(vm) {
    const meta = `${vm.os_category} / ${vm.os_version} · ${vm.ram}MB RAM · ${vm.vcpu} vCPU · ${vm.disk_size}`;
    return `
    <div class="vm-card">
        <div class="vm-card-header">
            <h3>${esc(vm.name)}</h3>
            <span class="status-badge status-${vm.status}">${vm.status}</span>
        </div>
        <div class="vm-card-meta">${meta}</div>
        <div class="vm-card-actions">
            ${vm.status === "stopped"
                ? `<button class="btn btn-success btn-sm" onclick="doAction('${vm.name}','start')">Start</button>`
                : `<button class="btn btn-danger btn-sm" onclick="doAction('${vm.name}','stop')">Stop</button>
                   <button class="btn btn-secondary btn-sm" onclick="doAction('${vm.name}','reboot')">Reboot</button>`
            }
            <a href="/vm/${vm.name}" class="btn btn-secondary btn-sm">View</a>
            <button class="btn btn-danger-outline btn-sm" onclick="doDelete('${vm.name}')">Delete</button>
        </div>
    </div>`;
}

function esc(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

async function loadVMs() {
    const el = document.getElementById("vm-list");
    if (!el) return;

    try {
        const vms = await fetchJSON("/api/vms");
        if (vms.length === 0) {
            el.innerHTML = `<p style="color:var(--text-muted)">No VMs yet. <a href="/create">Create one</a>.</p>`;
        } else {
            el.innerHTML = vms.map(vmCard).join("");
        }
    } catch (err) {
        el.innerHTML = `<p class="error-msg">Failed to load VMs: ${err.message}</p>`;
    }
}

async function doAction(name, action) {
    try {
        await fetchJSON(`/api/vm/${name}/${action}`, { method: "POST" });
        await loadVMs();
    } catch (err) {
        alert(`Action failed: ${err.message}`);
    }
}

async function doDelete(name) {
    if (!confirm(`Delete VM "${name}"? This will remove the disk image and cannot be undone.`)) return;
    try {
        await fetchJSON(`/api/vm/${name}`, { method: "DELETE" });
        await loadVMs();
    } catch (err) {
        alert(`Delete failed: ${err.message}`);
    }
}

document.addEventListener("DOMContentLoaded", loadVMs);
