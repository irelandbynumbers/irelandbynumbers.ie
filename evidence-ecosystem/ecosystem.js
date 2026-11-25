// Interactive map of Ireland's evidence-policy ecosystem.
// Reads nodes.csv, links.csv, layout.csv and stats.csv from this folder and draws an SVG network.
// To attach figures to an organisation, add rows to stats.csv; they appear in the details panel.
(function () {
  const W = 1300, H = 1110;
  const NS = "http://www.w3.org/2000/svg";

  const GROUPS = {
    government: { name: "Government and public administration", color: "#1baf7a" },
    learned: { name: "Learned and professional societies", color: "#a3a832" },
    research: { name: "Research performing organisations", color: "#eb6834" },
    funder: { name: "Research funders", color: "#6250d6" },
    advisory: { name: "Expert advisory bodies", color: "#e34948" },
    societal: { name: "Societal actors and advocacy bodies", color: "#2a78d6" },
    institute: { name: "National research institutes", color: "#008300" },
    consultants: { name: "Consultants and professional services", color: "#8a8986" },
    knowledge: { name: "Knowledge repositories and science communication", color: "#11a3b5" },
  };

  // Each link type has its own colour, width and dash pattern, so the types can be told apart without colour.
  const LINKS = {
    funding: { name: "Research funding", verb: "funds", inverse: "is funded by", color: "#d55181", width: 2.6, dash: "2 4" },
    demand: { name: "Demand for evidence", verb: "asks for evidence from", inverse: "is asked for evidence by", color: "#2a78d6", width: 1.6, dash: "" },
    supply: { name: "Supply of research-based evidence", verb: "supplies research-based evidence to", inverse: "receives research-based evidence from", color: "#d99400", width: 3, dash: "" },
    synthesis: { name: "Evidence synthesis and advice", verb: "gives evidence synthesis and advice to", inverse: "receives evidence synthesis and advice from", color: "#008300", width: 1.8, dash: "7 4" },
  };

  function parseCSV(text) {
    const rows = [];
    let row = [], field = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) {
        if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
        else if (c === '"') q = false;
        else field += c;
      } else if (c === '"') q = true;
      else if (c === ",") { row.push(field); field = ""; }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(field); field = "";
        if (row.length > 1 || row[0] !== "") rows.push(row);
        row = [];
      } else field += c;
    }
    if (field !== "" || row.length) { row.push(field); rows.push(row); }
    const head = rows.shift();
    return rows.map((r) => Object.fromEntries(head.map((h, i) => [h, (r[i] || "").trim()])));
  }

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  function wrap(text, max) {
    const words = text.split(" "), lines = [];
    let line = "";
    for (const w of words) {
      if (line && (line + " " + w).length > max) { lines.push(line); line = w; }
      else line = line ? line + " " + w : w;
    }
    if (line) lines.push(line);
    return lines;
  }

  function addLabel(parent, text, x, y, cls, max, above) {
    const lines = wrap(text, max);
    const t = el("text", { x, y, class: cls, "text-anchor": "middle" }, parent);
    if (above) t.setAttribute("transform", `translate(0, ${-(lines.length - 1) * 1.15 * (cls === "eco-hub-label" ? 22 : 18)})`);
    lines.forEach((ln, i) => {
      const s = el("tspan", { x, dy: i === 0 ? 0 : "1.15em" }, t);
      s.textContent = ln;
    });
    return t;
  }

  async function load(root) {
    const base = root.dataset.base || "";
    const get = (f) => fetch(base + f).then((r) => (r.ok ? r.text() : "")).then((t) => (t ? parseCSV(t) : []));
    const [nodes, links, layout, stats] = await Promise.all([get("nodes.csv"), get("links.csv"), get("layout.csv"), get("stats.csv")]);
    draw(root, nodes, links, layout, stats);
  }

  function draw(root, nodes, links, layout, stats) {
    const byId = new Map(nodes.map((n) => [n.id, n]));
    const pos = new Map(layout.map((l) => [l.id, l]));

    // Place hubs and stand-alone nodes from layout.csv, and spread members evenly around their hub.
    const members = {};
    nodes.forEach((n) => {
      const p = pos.get(n.id);
      if (p) { n.x = +p.x; n.y = +p.y; n.ring = +p.ring_radius || 0; n.labelPos = p.label_position || "below"; }
      if (n.role === "member") (members[n.cluster] = members[n.cluster] || []).push(n);
    });
    Object.entries(members).forEach(([hubId, list]) => {
      const hub = byId.get(hubId);
      list.forEach((m, i) => {
        const a = -Math.PI / 2 + (2 * Math.PI * i) / list.length;
        m.angle = a;
        m.x = hub.x + hub.ring * Math.cos(a);
        m.y = hub.y + hub.ring * Math.sin(a);
      });
    });
    nodes.forEach((n) => { n.r = n.role === "hub" ? 28 : n.role === "member" ? 6 : 10; n.links = []; n.stats = []; });
    stats.forEach((s) => { const n = byId.get(s.node_id); if (n) n.stats.push(s); });
    links = links.filter((l) => byId.has(l.source) && byId.has(l.target) && LINKS[l.type]);
    links.forEach((l) => { byId.get(l.source).links.push(l); byId.get(l.target).links.push(l); });

    const svg = root.querySelector("svg.eco-map");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const defs = el("defs", {}, svg);
    Object.entries(LINKS).forEach(([k, t]) => {
      const m = el("marker", { id: "arrow-" + k, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, markerUnits: "userSpaceOnUse", orient: "auto-start-reverse" }, defs);
      m.setAttribute("markerWidth", 9 + t.width * 1.5);
      m.setAttribute("markerHeight", 9 + t.width * 1.5);
      el("path", { d: "M0,1 L10,5 L0,9 z", fill: t.color }, m);
    });

    const gRings = el("g", { class: "eco-rings" }, svg);
    const gLinks = el("g", { class: "eco-links" }, svg);
    const gNodes = el("g", { class: "eco-nodes" }, svg);
    const gMemberLabels = el("g", { class: "eco-member-labels" }, svg);

    nodes.filter((n) => n.role === "hub").forEach((h) => {
      if (h.ring) el("circle", { cx: h.x, cy: h.y, r: h.ring, class: "eco-ring" }, gRings);
    });

    // Curved links, trimmed so arrowheads sit on the edge of each node.
    links.forEach((l) => {
      const s = byId.get(l.source), t = byId.get(l.target), type = LINKS[l.type];
      const dx = t.x - s.x, dy = t.y - s.y, len = Math.hypot(dx, dy);
      const bend = 0.14 * len;
      const cx = (s.x + t.x) / 2 - (dy / len) * bend, cy = (s.y + t.y) / 2 + (dx / len) * bend;
      const trim = (n, px, py, pad) => { const vx = px - n.x, vy = py - n.y, d = Math.hypot(vx, vy); return [n.x + (vx / d) * (n.r + pad), n.y + (vy / d) * (n.r + pad)]; };
      const [x1, y1] = trim(s, cx, cy, l.both_ways === "yes" ? 3 : 1);
      const [x2, y2] = trim(t, cx, cy, 3);
      const p = el("path", {
        d: `M${x1},${y1} Q${cx},${cy} ${x2},${y2}`,
        class: "eco-link", stroke: type.color, "stroke-width": type.width, "stroke-dasharray": type.dash,
        "marker-end": `url(#arrow-${l.type})`,
      }, gLinks);
      if (l.both_ways === "yes") p.setAttribute("marker-start", `url(#arrow-${l.type})`);
      l.el = p;
    });

    const tip = root.querySelector(".eco-tooltip");
    nodes.forEach((n) => {
      const g = el("g", { class: "eco-node eco-" + n.role, tabindex: 0, role: "button", "aria-label": n.label }, gNodes);
      el("circle", { cx: n.x, cy: n.y, r: n.role === "member" ? 9 : n.r + 4, class: "eco-hit" }, g);
      el("circle", { cx: n.x, cy: n.y, r: n.r, fill: GROUPS[n.group].color, class: "eco-dot" }, g);
      if (n.role === "hub") {
        const off = Math.max(n.ring, n.r) + (n.ring ? 14 : 4);
        const above = n.labelPos === "above";
        addLabel(g, n.label, n.x, above ? n.y - off - 6 : n.y + off + 18, "eco-hub-label", 22, above);
      }
      if (n.role === "node") {
        if (n.labelPos === "right" || n.labelPos === "left") {
          const t = el("text", { x: n.x + (n.labelPos === "right" ? 1 : -1) * (n.r + 6), y: n.y + 6, class: "eco-node-label", "text-anchor": n.labelPos === "right" ? "start" : "end" }, g);
          t.textContent = n.label;
        } else addLabel(g, n.label, n.x, n.labelPos === "above" ? n.y - n.r - 10 : n.y + n.r + 19, "eco-node-label", 22, n.labelPos === "above");
      }
      n.el = g;
      g.addEventListener("mouseenter", (e) => showTip(n, e));
      g.addEventListener("mousemove", (e) => showTip(n, e));
      g.addEventListener("mouseleave", () => (tip.hidden = true));
      g.addEventListener("click", (e) => { e.stopPropagation(); select(n); });
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(n); } });
    });
    svg.addEventListener("click", () => select(null));

    function showTip(n, e) {
      const box = root.querySelector(".eco-canvas").getBoundingClientRect();
      tip.innerHTML = `<strong>${n.label}</strong><span>${GROUPS[n.group].name}</span>`;
      tip.hidden = false;
      const x = e.clientX - box.left + 14, y = e.clientY - box.top + 14;
      tip.style.left = Math.min(x, box.width - tip.offsetWidth - 4) + "px";
      tip.style.top = y + "px";
    }

    // Link-type filters.
    const active = new Set(Object.keys(LINKS));
    const filters = root.querySelector(".eco-filters");
    Object.entries(LINKS).forEach(([k, t]) => {
      const count = links.filter((l) => l.type === k).length;
      const b = document.createElement("button");
      b.type = "button"; b.className = "eco-chip"; b.setAttribute("aria-pressed", "true");
      b.innerHTML = `<svg width="34" height="10" aria-hidden="true"><line x1="1" y1="5" x2="33" y2="5" stroke="${t.color}" stroke-width="${t.width + 0.5}" stroke-dasharray="${t.dash}"/></svg>${t.name} <span class="eco-count">${count}</span>`;
      b.addEventListener("click", () => {
        active.has(k) ? active.delete(k) : active.add(k);
        b.setAttribute("aria-pressed", active.has(k));
        refresh();
      });
      filters.appendChild(b);
    });

    let selected = null;
    function select(n) { selected = n && selected === n ? null : n; refresh(); renderPanel(); }

    function refresh() {
      const sel = selected;
      const cluster = sel ? (sel.role === "hub" ? sel.id : sel.role === "member" ? sel.cluster : null) : null;
      links.forEach((l) => {
        const on = active.has(l.type);
        const touches = sel && (l.source === sel.id || l.target === sel.id || (sel.role === "member" && (l.source === sel.cluster || l.target === sel.cluster)));
        l.el.style.display = on ? "" : "none";
        l.el.classList.toggle("is-faded", !!sel && !touches);
        l.el.classList.toggle("is-hot", !!sel && !!touches);
      });
      const linked = new Set();
      if (sel) links.forEach((l) => {
        if (!active.has(l.type)) return;
        const focus = sel.role === "member" ? sel.cluster : sel.id;
        if (l.source === focus) linked.add(l.target);
        if (l.target === focus) linked.add(l.source);
      });
      nodes.forEach((n) => {
        const keep = !sel || n === sel || linked.has(n.id) || n.id === cluster || (cluster && n.cluster === cluster) || (n.role === "member" && linked.has(n.cluster));
        n.el.classList.toggle("is-faded", !keep);
        n.el.classList.toggle("is-selected", n === sel);
      });
      // Only the selected member is named on the map; the full member list is in the side panel.
      gMemberLabels.innerHTML = "";
      if (sel && sel.role === "member") {
        const hub = byId.get(sel.cluster);
        const c = Math.cos(sel.angle), sn = Math.sin(sel.angle);
        const t = el("text", { x: hub.x + (hub.ring + 12) * c, y: hub.y + (hub.ring + 12) * sn + 5, class: "eco-member-label is-selected", "text-anchor": Math.abs(c) < 0.3 ? "middle" : c > 0 ? "start" : "end" }, gMemberLabels);
        t.textContent = sel.label;
      }
    }

    const panel = root.querySelector(".eco-panel");
    const intro = panel.innerHTML;
    function linkSentences(n) {
      const focus = n.role === "member" ? byId.get(n.cluster) : n;
      const order = Object.keys(LINKS);
      const out = focus.links.filter((l) => active.has(l.type)).sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type)).map((l) => {
        const t = LINKS[l.type];
        const self = l.source === focus.id;
        const other = byId.get(self ? l.target : l.source);
        const verb = l.both_ways === "yes" ? t.name.toLowerCase() + " in both directions with" : self ? t.verb : t.inverse;
        return `<li><span class="eco-swatch" style="--c:${t.color}"></span>${verb[0].toUpperCase() + verb.slice(1)} <button type="button" class="eco-jump" data-id="${other.id}">${other.label}</button></li>`;
      });
      return { focus, out };
    }
    function renderPanel() {
      const n = selected;
      if (!n) { panel.innerHTML = intro; return; }
      const g = GROUPS[n.group];
      let h = `<p class="eco-kicker" style="--c:${g.color}">${g.name}</p><h3>${n.label}</h3>`;
      if (n.role === "member") h += `<p>Part of <button type="button" class="eco-jump" data-id="${n.cluster}">${byId.get(n.cluster).label}</button>. Links in the map are drawn to the group as a whole.</p>`;
      if (n.description) h += `<p>${n.description}</p>`;
      if (n.role === "hub" && members[n.id]) h += `<details><summary>${members[n.id].length} organisations in this group</summary><ul class="eco-members">${members[n.id].map((m) => `<li><button type="button" class="eco-jump" data-id="${m.id}">${m.label}</button></li>`).join("")}</ul></details>`;
      const { focus, out } = linkSentences(n);
      h += `<h4>${n.role === "member" ? "Links for " + focus.label : "Links"}</h4>`;
      h += out.length ? `<ul class="eco-links-list">${out.join("")}</ul>` : `<p class="eco-muted">No links of the selected types.</p>`;
      h += `<h4>Figures</h4>`;
      h += n.stats.length
        ? `<dl class="eco-stats">${n.stats.map((s) => `<dt>${s.label}${s.year ? " (" + s.year + ")" : ""}</dt><dd>${s.value}${s.unit ? " " + s.unit : ""}${s.source_url ? ` <a href="${s.source_url}">${s.source_name || "Source"}</a>` : s.source_name ? " " + s.source_name : ""}</dd>`).join("")}</dl>`
        : `<p class="eco-muted">No figures attached yet.</p>`;
      panel.innerHTML = h;
      panel.querySelectorAll(".eco-jump").forEach((b) => b.addEventListener("click", () => { selected = null; select(byId.get(b.dataset.id)); }));
    }

    // Plain list of every group and organisation, for readers who prefer text to the diagram.
    const list = root.querySelector(".eco-list-body");
    if (list) {
      const tops = nodes.filter((n) => n.role !== "member");
      list.innerHTML = Object.entries(GROUPS).map(([k, g]) => {
        const items = tops.filter((n) => n.group === k);
        if (!items.length) return "";
        return `<h4>${g.name}</h4><ul>${items.map((n) => members[n.id]
          ? `<li>${n.label}<ul>${members[n.id].map((m) => `<li>${m.label}</li>`).join("")}</ul></li>`
          : `<li>${n.label}</li>`).join("")}</ul>`;
      }).join("");
    }

    refresh();
  }

  document.querySelectorAll(".eco-root").forEach((r) => load(r).catch((e) => {
    r.querySelector(".eco-panel").textContent = "The map could not be loaded.";
    console.error(e);
  }));
})();
