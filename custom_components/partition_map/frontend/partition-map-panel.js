// Partition Map — panneau latéral façon GParted.
// Composant web sans dépendance ni étape de build.

const ROLE_COLORS = {
  boot: "#7f77dd",
  kernel: "#afa9ec",
  system: "#534ab7",
  bootstate: "#cecbf6",
  overlay: "#1d9e75",
  data: "#378add",
  data_orphan: "#e24b4a",
  other: "#888780",
};

const I18N = {
  fr: {
    title: "Partition Map",
    refresh: "Actualiser",
    loading: "Lecture des disques…",
    error: "Lecture impossible",
    boot: "démarrage",
    data: "données",
    partition: "Partition",
    name: "Nom",
    fs: "Système de fichiers",
    size: "Taille",
    used: "Utilisé",
    role: "Rôle",
    mount: "Montage",
    unallocated: "non alloué",
    not_mounted: "non monté",
    active: "actif",
    inactive: "inactif",
    orphan_warning: "Espace mort",
    unalloc_warning: "Espace non alloué",
    updated: "Mis à jour",
    network: "Stockages réseau",
    free: "libre",
    roles: {
      boot: "Boot",
      kernel: "Noyau",
      system: "Système",
      bootstate: "État de boot",
      overlay: "Overlay",
      data: "Données",
      data_orphan: "Ancienne data",
      other: "Autre",
      unallocated: "Non alloué",
    },
  },
  en: {
    title: "Partition Map",
    refresh: "Refresh",
    loading: "Reading disks…",
    error: "Couldn't read disks",
    boot: "boot",
    data: "data",
    partition: "Partition",
    name: "Name",
    fs: "File system",
    size: "Size",
    used: "Used",
    role: "Role",
    mount: "Mount",
    unallocated: "unallocated",
    not_mounted: "not mounted",
    active: "active",
    inactive: "inactive",
    orphan_warning: "Dead space",
    unalloc_warning: "Unallocated space",
    updated: "Updated",
    network: "Network storage",
    free: "free",
    roles: {
      boot: "Boot",
      kernel: "Kernel",
      system: "System",
      bootstate: "Boot state",
      overlay: "Overlay",
      data: "Data",
      data_orphan: "Old data",
      other: "Other",
      unallocated: "Unallocated",
    },
  },
};

const fmt = (bytes) => {
  if (bytes == null) return "—";
  const units = ["o", "Ko", "Mo", "Go", "To"];
  let i = 0;
  let n = bytes;
  while (n >= 1000 && i < units.length - 1) {
    n /= 1000;
    i++;
  }
  return `${n.toFixed(n < 10 && i > 0 ? 2 : n < 100 && i > 0 ? 1 : 0)} ${units[i]}`;
};

const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

class PartitionMapPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._data = null;
    this._error = null;
    this._loading = false;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (this._menu) this._menu.hass = hass;
    if (first) {
      this._renderShell();
      this._load(false);
    }
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  get _t() {
    const lang = (this._hass?.language || "en").split("-")[0];
    return I18N[lang] || I18N.en;
  }

  async _load(refresh) {
    this._loading = true;
    this._error = null;
    this._renderContent();
    try {
      this._data = await this._hass.connection.sendMessagePromise({
        type: "partition_map/layout",
        refresh,
      });
    } catch (err) {
      this._error = err?.message || String(err);
    }
    this._loading = false;
    this._renderContent();
  }

  _renderShell() {
    const t = this._t;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; background:var(--primary-background-color); min-height:100vh; color:var(--primary-text-color); }
        .toolbar { display:flex; align-items:center; gap:8px; height:56px; padding:0 12px;
          background:var(--app-header-background-color); color:var(--app-header-text-color, white);
          font-size:20px; }
        .toolbar .title { flex:1; }
        .toolbar button { background:transparent; border:1px solid currentColor; color:inherit;
          border-radius:4px; padding:6px 12px; cursor:pointer; font-size:14px; }
        .content { max-width:1100px; margin:0 auto; padding:16px; display:flex; flex-direction:column; gap:16px; }
        .card { background:var(--card-background-color); border-radius:var(--ha-card-border-radius, 12px);
          border:1px solid var(--divider-color); padding:16px; }
        .head { display:flex; justify-content:space-between; align-items:baseline; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
        .head .dev { font-size:18px; font-weight:500; }
        .muted { color:var(--secondary-text-color); font-size:13px; }
        .badge { font-size:12px; padding:2px 8px; border-radius:10px; margin-left:6px;
          background:var(--secondary-background-color); color:var(--secondary-text-color); }
        .bar { display:flex; height:44px; border-radius:6px; overflow:hidden; gap:2px;
          background:var(--divider-color); padding:2px; }
        .seg { position:relative; min-width:8px; border-radius:3px; overflow:hidden; cursor:default;
          display:flex; align-items:center; padding:0 6px; font-size:12px; color:#fff; white-space:nowrap; }
        .seg .fill { position:absolute; inset:0 auto 0 0; background:rgba(0,0,0,.28); }
        .seg span { position:relative; overflow:hidden; text-overflow:ellipsis; }
        .seg.orphan { background-image:repeating-linear-gradient(45deg, rgba(255,255,255,.25) 0 6px, transparent 6px 12px); }
        .seg.gap { background:var(--card-background-color); color:var(--secondary-text-color);
          border:1px dashed var(--secondary-text-color); }
        .warn { margin-top:10px; font-size:13px; color:var(--error-color); }
        .warn.soft { color:var(--warning-color); }
        table { width:100%; border-collapse:collapse; margin-top:12px; font-size:13px; }
        th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--divider-color); vertical-align:top; }
        th { color:var(--secondary-text-color); font-weight:500; }
        td.num { text-align:right; white-space:nowrap; }
        .dot { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; }
        .legend { display:flex; flex-wrap:wrap; gap:12px; font-size:12px; color:var(--secondary-text-color); }
        @media (max-width: 700px) { .hide-narrow { display:none; } }
      </style>
      <div class="toolbar">
        <span class="menu"></span>
        <span class="title">${esc(t.title)}</span>
        <button id="refresh">${esc(t.refresh)}</button>
      </div>
      <div class="content" id="content"></div>
    `;
    this._menu = document.createElement("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;
    this.shadowRoot.querySelector(".menu").appendChild(this._menu);
    this.shadowRoot.getElementById("refresh").addEventListener("click", () => this._load(true));
  }

  _renderContent() {
    const root = this.shadowRoot.getElementById("content");
    if (!root) return;
    const t = this._t;
    if (this._loading && !this._data) {
      root.innerHTML = `<div class="card muted">${esc(t.loading)}</div>`;
      return;
    }
    if (this._error) {
      root.innerHTML = `<div class="card warn">${esc(t.error)} : ${esc(this._error)}</div>`;
      return;
    }
    if (!this._data) return;

    const legend = Object.entries(t.roles)
      .map(([role, label]) => {
        const color = role === "unallocated" ? "transparent; border:1px dashed var(--secondary-text-color)" : ROLE_COLORS[role];
        return `<span><span class="dot" style="background:${color}"></span>${esc(label)}</span>`;
      })
      .join("");

    const updated = this._data.updated ? new Date(this._data.updated).toLocaleString(this._hass.language) : "";
    root.innerHTML =
      this._data.disks.map((d) => this._disk(d)).join("") +
      this._mounts() +
      `<div class="legend">${legend}</div>` +
      `<div class="muted">${esc(t.updated)} : ${esc(updated)}</div>`;
  }

  _mounts() {
    const t = this._t;
    const mounts = Object.values(this._data.storages || {}).filter((s) => s.kind === "mount");
    if (!mounts.length) return "";
    const rows = mounts
      .map((m) => {
        const pct = m.percent ?? 0;
        const color = pct >= 95 ? "var(--error-color)" : pct >= 85 ? "var(--warning-color)" : ROLE_COLORS.data;
        return `<div style="margin-top:12px">
          <div class="head" style="margin-bottom:6px">
            <span><span class="dev">${esc(m.id)}</span> <span class="muted">${esc(m.mount_type || "")}</span></span>
            <span>${fmt(m.used_bytes)} / ${fmt(m.total_bytes)} · ${fmt(m.free_bytes)} ${esc(t.free)}</span>
          </div>
          <div class="bar" title="${pct} %"><div class="seg" style="flex:${Math.max(pct, 0.5)}; background-color:${color}">${pct >= 10 ? `<span>${pct} %</span>` : ""}</div><div class="seg gap" style="flex:${Math.max(100 - pct, 0.5)}"></div></div>
        </div>`;
      })
      .join("");
    return `<div class="card"><div class="head"><span class="dev">${esc(t.network)}</span></div>${rows}</div>`;
  }

  _disk(d) {
    const t = this._t;
    const usage = this._data.storages?.data;
    const items = [
      ...d.partitions.map((p) => ({ kind: "part", start: p.start, size: p.size, p })),
      ...d.gaps.map((g) => ({ kind: "gap", start: g.start, size: g.size })),
    ].sort((a, b) => a.start - b.start);

    const segs = items
      .map((it) => {
        const grow = Math.max(it.size / d.size, 0.002);
        if (it.kind === "gap") {
          return `<div class="seg gap" style="flex:${grow}" title="${esc(t.unallocated)} · ${fmt(it.size)}">${grow >= 0.05 ? `<span>${esc(t.unallocated)}</span>` : ""}</div>`;
        }
        const p = it.p;
        let fill = "";
        if (p.role === "data" && usage?.total_bytes) {
          const pct = Math.min(100, (usage.used_bytes / usage.total_bytes) * 100);
          fill = `<div class="fill" style="width:${pct.toFixed(1)}%"></div>`;
        }
        const label = p.fs_label || p.part_name || p.device;
        const cls = p.role === "data_orphan" ? "seg orphan" : "seg";
        return `<div class="${cls}" style="flex:${grow}; background-color:${ROLE_COLORS[p.role] || ROLE_COLORS.other}"
          title="${esc(p.device)} · ${esc(label)} · ${fmt(p.size)}">${fill}${grow >= 0.05 ? `<span>${esc(label)} ${fmt(p.size)}</span>` : ""}</div>`;
      })
      .join("");

    const rows = d.partitions
      .map((p) => {
        const role = t.roles[p.role] || p.role;
        const slot = p.slot ? ` ${p.slot} · ${p.active ? t.active : t.inactive}` : "";
        let used = "—";
        if (p.role === "data" && usage?.total_bytes) used = `${fmt(usage.used_bytes)}`;
        const mount = p.mount_points.length
          ? esc(p.mount_points[0]) + (p.mount_points.length > 1 ? ` <span class="muted">+${p.mount_points.length - 1}</span>` : "")
          : `<span class="muted">${esc(t.not_mounted)}</span>`;
        return `<tr>
          <td><span class="dot" style="background:${ROLE_COLORS[p.role] || ROLE_COLORS.other}"></span>${esc(p.device)}</td>
          <td>${esc(p.part_name)}${p.fs_label && p.fs_label !== p.part_name ? ` <span class="muted">(${esc(p.fs_label)})</span>` : ""}</td>
          <td class="hide-narrow">${esc(p.fs_type || "—")}</td>
          <td class="num">${fmt(p.size)}</td>
          <td class="num hide-narrow">${used}</td>
          <td>${esc(role)}${esc(slot)}</td>
          <td class="hide-narrow">${mount}</td>
        </tr>`;
      })
      .join("");

    const orphanBytes = d.partitions.filter((p) => p.role === "data_orphan").reduce((s, p) => s + p.size, 0);
    const warnings =
      (orphanBytes ? `<div class="warn">⚠ ${esc(t.orphan_warning)} : ${fmt(orphanBytes)}</div>` : "") +
      (d.unallocated ? `<div class="warn soft">${esc(t.unalloc_warning)} : ${fmt(d.unallocated)}</div>` : "");

    const badges =
      (d.is_boot ? `<span class="badge">${esc(t.boot)}</span>` : "") +
      (d.is_data ? `<span class="badge">${esc(t.data)}</span>` : "");

    return `<div class="card">
      <div class="head">
        <span><span class="dev">${esc(d.device)}</span> <span class="muted">${esc(d.vendor)} ${esc(d.model)} · ${esc(d.serial)}</span>${badges}</span>
        <span>${fmt(d.size)}</span>
      </div>
      <div class="bar">${segs}</div>
      ${warnings}
      <table>
        <thead><tr>
          <th>${esc(t.partition)}</th><th>${esc(t.name)}</th><th class="hide-narrow">${esc(t.fs)}</th>
          <th class="num">${esc(t.size)}</th><th class="num hide-narrow">${esc(t.used)}</th>
          <th>${esc(t.role)}</th><th class="hide-narrow">${esc(t.mount)}</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  }
}

customElements.define("partition-map-panel", PartitionMapPanel);
