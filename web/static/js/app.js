/**
 * WebVM — Dashboard JavaScript
 *
 * Handles:
 * - Fetching and rendering the VM list on the dashboard
 * - Per-VM action buttons (start, stop, reboot, delete)
 * - Escape HTML to prevent XSS in VM names
 * - i18n via window.__I18N injected by Flask
 */

const API = "";  // Same-origin; Flask serves at the same host

/** Shortcut to i18n strings injected from Flask template. */
const _ = (key, kwargs = {}) => {
    const parts = key.split(".");
    let value = window.__I18N;
    for (const part of parts) {
        if (value && typeof value === "object" && part in value) {
            value = value[part];
        } else {
            return key;
        }
    }
    if (typeof value !== "string") return key;
    // Format with kwargs
    if (Object.keys(kwargs).length > 0) {
        try { value = value.replace(/\{(\w+)\}/g, (_, k) => kwargs[k] ?? `{${k}}`); } catch (_) {}
    }
    return value;
};

async function fetchJSON(url, options = {}) {
    const res = await fetch(API + url, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(err.error || res.statusText);
    }
    return res.json();
}

function esc(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function vmCard(vm) {
    const meta = _(vm.os_category + "." + vm.os_version, { os_cat: vm.os_category, os_ver: vm.os_version })
        || `${vm.os_category} / ${vm.os_version}`;

    const startBtn = `<button class="btn btn-success btn-sm" onclick="doAction('${esc(vm.name)}','start')">${_("vm_actions.start")}</button>`;
    const stopBtn  = `<button class="btn btn-danger btn-sm" onclick="doAction('${esc(vm.name)}','stop')">${_("vm_actions.stop")}</button>`;
    const rebootBtn= `<button class="btn btn-secondary btn-sm" onclick="doAction('${esc(vm.name)}','reboot')">${_("vm_actions.reboot")}</button>`;

    const actions = vm.status === "stopped"
        ? startBtn
        : `${stopBtn}${rebootBtn}`;

    return `
    <div class="vm-card">
        <div class="vm-card-header">
            <h3>${esc(vm.name)}</h3>
            <span class="status-badge status-${vm.status}">${_(`vm_status.${vm.status}`)}</span>
        </div>
        <div class="vm-card-meta">${meta} · ${vm.ram}MB RAM · ${vm.vcpu} vCPU · ${vm.disk_size}</div>
        <div class="vm-card-actions">
            ${actions}
            <a href="/vm/${esc(vm.name)}" class="btn btn-secondary btn-sm">${_("vm_actions.view")}</a>
            <button class="btn btn-danger-outline btn-sm" onclick="doDelete('${esc(vm.name)}')">${_("vm_actions.delete")}</button>
        </div>
    </div>`;
}

async function loadVMs() {
    const el = document.getElementById("vm-list");
    if (!el) return;

    try {
        const vms = await fetchJSON("/api/vms");
        if (vms.length === 0) {
            el.innerHTML = `<p style="color:var(--text-muted)">${_("dashboard.no_vms")} <a href="/create">${_("dashboard.no_vms_link")}</a>.</p>`;
        } else {
            el.innerHTML = vms.map(vmCard).join("");
        }
    } catch (err) {
        el.innerHTML = `<p class="error-msg">${esc(err.message)}</p>`;
    }
}

async function doAction(name, action) {
    try {
        await fetchJSON(`/api/vm/${name}/${action}`, { method: "POST" });
        await loadVMs();
    } catch (err) {
        alert(`${action} failed: ${err.message}`);
    }
}

async function doDelete(name) {
    if (!confirm(_("vm_actions.confirm_delete", { name }))) return;
    try {
        await fetchJSON(`/api/vm/${name}`, { method: "DELETE" });
        await loadVMs();
    } catch (err) {
        alert(`Delete failed: ${err.message}`);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadVMs();
    setInterval(loadVMs, 5000);
});
