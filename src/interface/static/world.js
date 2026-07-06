    const POLL_MS = 1000;
    const QUEST_COLOR = { active: "amber", completed: "green", failed: "ember" };

    const state = {
      runs: [],
      scenario: null,
      runId: null,
      view: null,
      live: true,
      timer: null,
      pollCount: 0,
      mapLayout: null,
      selectedLoc: null,
      series: {},
    };

    const dom = {
      run: document.getElementById("run"),
      slider: document.getElementById("tick-slider"),
      tickLabel: document.getElementById("tick-label"),
      tickPrev: document.getElementById("tick-prev"),
      tickNext: document.getElementById("tick-next"),
      liveBtn: document.getElementById("live-btn"),
      metaTitle: document.getElementById("meta-title"),
      metaClock: document.getElementById("meta-clock"),
      metaQuests: document.getElementById("meta-quests"),
      mapSvg: document.getElementById("map-svg"),
      locDetail: document.getElementById("loc-detail"),
      charGrid: document.getElementById("char-grid"),
      charCount: document.getElementById("char-count"),
      questList: document.getElementById("quest-list"),
      questCount: document.getElementById("quest-count"),
      feed: document.getElementById("feed"),
      storyBody: document.getElementById("story-body"),
      storyCount: document.getElementById("story-count"),
    };

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatClock(totalMinutes) {
      const day = Math.floor(totalMinutes / 1440) + 1;
      const rest = totalMinutes % 1440;
      const hh = String(Math.floor(rest / 60)).padStart(2, "0");
      const mm = String(rest % 60).padStart(2, "0");
      return `day ${day} · ${hh}:${mm}`;
    }

    async function fetchJson(path) {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      return response.json();
    }

    function runKey(scenario, runId) {
      return `${scenario}/${runId}`;
    }

    async function loadRuns() {
      state.runs = await fetchJson("/api/runs");
      renderRuns();
      if (!state.runs.length) {
        dom.charGrid.innerHTML = "";
        dom.metaTitle.textContent = "No snapshots yet";
        dom.locDetail.innerHTML = '<div class="empty">Run a game to produce world-state snapshots.</div>';
        return;
      }
      if (!state.scenario || !state.runId || !state.runs.some((r) => r.scenario === state.scenario && r.run_id === state.runId)) {
        state.scenario = state.runs[0].scenario;
        state.runId = state.runs[0].run_id;
        dom.run.value = runKey(state.scenario, state.runId);
      }
      await loadView(null);
    }

    async function loadView(tick) {
      if (!state.scenario || !state.runId) return;
      const query = tick === null || tick === undefined ? "" : `?tick=${tick}`;
      const scenarioPart = encodeURIComponent(state.scenario);
      const runPart = encodeURIComponent(state.runId);
      state.view = await fetchJson(`/api/state/${scenarioPart}/${runPart}${query}`);
      state.series = await fetchJson(`/api/series/${scenarioPart}/${runPart}`);
      renderAll();
    }

    function renderRuns() {
      dom.run.innerHTML = state.runs.map((r) => `
        <option value="${escapeHtml(runKey(r.scenario, r.run_id))}" ${r.scenario === state.scenario && r.run_id === state.runId ? "selected" : ""}>
          ${escapeHtml(r.title)} · ${escapeHtml(r.run_id)} (${escapeHtml(r.tick_count)} ticks)
        </option>
      `).join("");
    }

    function renderAll() {
      renderTopbar();
      renderMap();
      renderLocDetail();
      renderCharacters();
      renderQuests();
      renderFeed();
    }

    function renderTopbar() {
      const view = state.view;
      if (!view) return;
      const idx = view.ticks.indexOf(view.tick);
      dom.slider.max = view.ticks.length - 1;
      dom.slider.value = idx;
      dom.tickLabel.textContent = `tick ${view.tick} / ${view.latest_tick}`;
      dom.metaTitle.textContent = view.title;
      dom.metaClock.textContent = formatClock(view.state.minutes_elapsed || 0);
      const quests = Object.values(view.state.quests || {});
      const active = quests.filter((q) => !["completed", "failed"].includes((q.status || "").toLowerCase())).length;
      const done = quests.filter((q) => (q.status || "").toLowerCase() === "completed").length;
      dom.metaQuests.textContent = ` · ${active} active · ${done} done`;
      dom.liveBtn.classList.toggle("on", state.live);
    }

    // ── Map ────────────────────────────────────────────────

    function computeLayout(locations) {
      const ids = Object.keys(locations).sort();
      const key = ids.join("|");
      if (state.mapLayout && state.mapLayout.key === key) return state.mapLayout;

      const nodes = ids.map((id, i) => {
        const angle = (2 * Math.PI * i) / Math.max(1, ids.length);
        return { id, x: 130 * Math.cos(angle), y: 130 * Math.sin(angle) };
      });
      const byId = new Map(nodes.map((n) => [n.id, n]));

      const edges = [];
      const seen = new Set();
      for (const id of ids) {
        for (const target of locations[id].connections || []) {
          if (!byId.has(target) || target === id) continue;
          const pair = id < target ? `${id}|${target}` : `${target}|${id}`;
          if (seen.has(pair)) continue;
          seen.add(pair);
          edges.push([byId.get(id), byId.get(target)]);
        }
      }

      // Small deterministic force layout: pairwise repulsion, springs along
      // connections, mild centering pull, with a cooling displacement cap.
      const iterations = 250;
      for (let iter = 0; iter < iterations; iter++) {
        const cool = 1 - iter / iterations;
        const disp = new Map(nodes.map((n) => [n.id, { x: 0, y: 0 }]));
        for (let a = 0; a < nodes.length; a++) {
          for (let b = a + 1; b < nodes.length; b++) {
            const n1 = nodes[a], n2 = nodes[b];
            const dx = n1.x - n2.x, dy = n1.y - n2.y;
            const d = Math.hypot(dx, dy) || 0.01;
            const f = 2600 / (d * d);
            const d1 = disp.get(n1.id), d2 = disp.get(n2.id);
            d1.x += (dx / d) * f; d1.y += (dy / d) * f;
            d2.x -= (dx / d) * f; d2.y -= (dy / d) * f;
          }
        }
        for (const [n1, n2] of edges) {
          const dx = n1.x - n2.x, dy = n1.y - n2.y;
          const d = Math.hypot(dx, dy) || 0.01;
          const f = (d - 95) * 0.04;
          const d1 = disp.get(n1.id), d2 = disp.get(n2.id);
          d1.x -= (dx / d) * f; d1.y -= (dy / d) * f;
          d2.x += (dx / d) * f; d2.y += (dy / d) * f;
        }
        for (const n of nodes) {
          const d = disp.get(n.id);
          const len = Math.hypot(d.x, d.y) || 0.01;
          const cap = Math.min(len, 14 * cool);
          n.x += (d.x / len) * cap - n.x * 0.005;
          n.y += (d.y / len) * cap - n.y * 0.005;
        }
      }

      state.mapLayout = { key, nodes, edges };
      return state.mapLayout;
    }

    function shortName(id) {
      return id.length > 18 ? id.slice(0, 17) + "…" : id;
    }

    function renderMap() {
      const view = state.view;
      if (!view) return;
      const locations = view.state.locations || {};
      const layout = computeLayout(locations);
      if (!layout.nodes.length) {
        dom.mapSvg.innerHTML = "";
        return;
      }

      const newLocs = new Set(view.changes?.new_locations || []);
      const pcLoc = view.state.characters?.[view.pc]?.location;
      const selected = state.selectedLoc || pcLoc;

      const occupants = {};
      Object.values(view.state.characters || {}).forEach((c) => {
        (occupants[c.location] = occupants[c.location] || []).push(c);
      });

      const xs = layout.nodes.map((n) => n.x);
      const ys = layout.nodes.map((n) => n.y);
      const pad = 48;
      const minX = Math.min(...xs) - pad, minY = Math.min(...ys) - pad;
      const width = Math.max(...xs) + pad - minX, height = Math.max(...ys) + pad - minY;
      dom.mapSvg.setAttribute("viewBox", `${minX} ${minY} ${width} ${height}`);

      const edgeHtml = layout.edges.map(([a, b]) =>
        `<line class="map-edge" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/>`
      ).join("");

      const nodeHtml = layout.nodes.map((n) => {
        const here = occupants[n.id] || [];
        const alive = here.filter((c) => (c.stats?.hp ?? 1) > 0);
        const r = 8 + Math.min(6, alive.length * 2);
        const cls = [
          "map-node",
          here.length ? "occupied" : "",
          n.id === pcLoc ? "pc" : "",
          newLocs.has(n.id) ? "fresh" : "",
        ].join(" ");
        const itemCount = (locations[n.id].items || []).length;
        return `
          <g class="${cls}" data-loc="${escapeHtml(n.id)}" transform="translate(${n.x},${n.y})">
            ${n.id === selected ? `<circle class="halo" r="${r + 5}"/>` : ""}
            <circle class="body" r="${r}"/>
            ${alive.length ? `<text class="count" dy="3">${alive.length}</text>` : ""}
            ${itemCount ? `<circle class="items-dot" cx="${r - 1}" cy="${1 - r}" r="3"/>` : ""}
            <text class="label" y="${r + 13}">${escapeHtml(shortName(n.id))}</text>
          </g>
        `;
      }).join("");

      dom.mapSvg.innerHTML = edgeHtml + nodeHtml;
    }

    function renderLocDetail() {
      const view = state.view;
      if (!view) return;
      const pcLoc = view.state.characters?.[view.pc]?.location;
      const locId = state.selectedLoc || pcLoc;
      const loc = (view.state.locations || {})[locId];
      if (!loc) {
        dom.locDetail.innerHTML = '<div class="empty">Click a location on the map.</div>';
        return;
      }
      const here = Object.values(view.state.characters || {}).filter((c) => c.location === locId);
      const who = here.map((c) => {
        const cls = c.id === view.pc ? "pc" : (c.stats?.hp ?? 1) <= 0 ? "dead" : "";
        return `<span class="${cls}">${escapeHtml(c.id)}</span>`;
      }).join(", ");

      dom.locDetail.innerHTML = `
        <div class="loc-head">
          <span class="name">${escapeHtml(loc.id)}</span>
          ${state.selectedLoc ? '<span class="chip">pinned</span>' : '<span class="chip violet">following pc</span>'}
        </div>
        ${loc.description ? `<div class="loc-desc">${escapeHtml(loc.description)}</div>` : ""}
        ${who ? `<div class="loc-field"><span class="k">here</span><div class="who">${who}</div></div>` : ""}
        ${loc.items?.length ? `<div class="loc-field"><span class="k">items</span><div class="inv-row">${loc.items.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}</div></div>` : ""}
        ${loc.features?.length ? `<div class="loc-field"><span class="k">features</span><div class="loc-desc">${escapeHtml(loc.features.join(", "))}</div></div>` : ""}
        ${loc.connections?.length ? `<div class="loc-field"><span class="k">connects to</span><div class="loc-desc">${escapeHtml(loc.connections.join(", "))}</div></div>` : ""}
      `;
    }

    function deltaChips(delta) {
      if (!delta) return "";
      const chips = [];
      if (delta.new) chips.push('<span class="chip violet">new</span>');
      if (delta.hp) chips.push(`<span class="chip ${delta.hp > 0 ? "green" : "ember"}">${delta.hp > 0 ? "+" : ""}${delta.hp} hp</span>`);
      if (delta.xp) chips.push(`<span class="chip violet">+${delta.xp} xp</span>`);
      if (delta.level) chips.push(`<span class="chip violet">level up</span>`);
      if (delta.gold) chips.push(`<span class="chip amber">${delta.gold > 0 ? "+" : ""}${delta.gold} gold</span>`);
      if (delta.moved_from) chips.push(`<span class="chip">moved: ${escapeHtml(delta.moved_from)} →</span>`);
      (delta.gained || []).forEach((item) => chips.push(`<span class="chip green">+ ${escapeHtml(item)}</span>`));
      (delta.lost || []).forEach((item) => chips.push(`<span class="chip ember">− ${escapeHtml(item)}</span>`));
      return chips.length ? `<div class="delta-row">${chips.join("")}</div>` : "";
    }

    function renderCharacters() {
      const view = state.view;
      if (!view) return;
      const changes = view.changes?.characters || {};
      const chars = Object.values(view.state.characters || {});
      chars.sort((a, b) => (a.id === view.pc ? -1 : b.id === view.pc ? 1 : a.id.localeCompare(b.id)));

      dom.charCount.textContent = chars.length || "";
      dom.charGrid.innerHTML = chars.map((c) => {
        const stats = c.stats || {};
        const dead = (stats.hp ?? 1) <= 0;
        const frac = stats.max_hp ? Math.max(0, stats.hp) / stats.max_hp : 0;
        const barClass = frac > 0.6 ? "" : frac > 0.3 ? "mid" : "low";
        const delta = changes[c.id];
        const points = sparkline(state.series[c.id] || []);
        return `
          <div class="char-card ${c.id === view.pc ? "pc" : ""} ${dead ? "dead" : ""} ${delta ? "changed" : ""}" data-char="${escapeHtml(c.id)}">
            <div class="char-head">
              <span class="name">${dead ? "☠ " : ""}${escapeHtml(c.id)}</span>
              ${c.id === view.pc ? '<span class="chip violet">PC</span>' : ""}
              ${c.role ? `<span class="chip">${escapeHtml(c.role)}</span>` : ""}
              ${points ? `<svg class="spark" viewBox="0 0 82 22" aria-label="HP history"><polyline points="${points}"></polyline></svg>` : ""}
            </div>
            <div class="hp-bar ${barClass}"><span style="width:${Math.round(frac * 100)}%"></span></div>
            <div class="stat-line">
              <span>${escapeHtml(Math.max(0, stats.hp ?? 0))}/${escapeHtml(stats.max_hp ?? "?")} hp</span>
              <span>lvl ${escapeHtml(stats.level ?? 1)}</span>
              <span>${escapeHtml(stats.xp ?? 0)} xp</span>
              <span>${escapeHtml(stats.gold ?? 0)} gold</span>
            </div>
            <div class="char-loc"><span class="at">at</span> ${escapeHtml(c.location || "unknown")}</div>
            ${c.inventory?.length ? `<div class="inv-row">${c.inventory.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}</div>` : ""}
            ${c.goal ? `<div class="char-goal">${escapeHtml(c.goal)}</div>` : ""}
            ${deltaChips(delta)}
          </div>
        `;
      }).join("") || '<div class="empty">No characters.</div>';
    }

    function sparkline(series) {
      if (!series.length) return "";
      const values = series.map((p) => Number(p.hp) || 0);
      const lo = Math.min(...values), hi = Math.max(...values), span = Math.max(1, hi - lo);
      return values.map((value, i) => `${values.length === 1 ? 41 : i * 82 / (values.length - 1)},${20 - (value - lo) * 18 / span}`).join(" ");
    }

    function showCharacter(id) {
      const c = state.view?.state.characters?.[id]; if (!c) return;
      const stats = c.stats || {};
      document.getElementById("char-detail").innerHTML = `<div class="dialog-head"><h2>${escapeHtml(c.id)}</h2><button data-close="char-drawer">×</button></div><div class="detail-grid">
        <div class="detail-field"><span class="k">Role & location</span>${escapeHtml(c.role || "—")} · ${escapeHtml(c.location || "—")}</div>
        <div class="detail-field"><span class="k">Stats</span>${escapeHtml(stats.hp ?? 0)}/${escapeHtml(stats.max_hp ?? "?")} HP · level ${escapeHtml(stats.level ?? 1)} · ${escapeHtml(stats.xp ?? 0)} XP · ${escapeHtml(stats.gold ?? 0)} gold</div>
        <div class="detail-field"><span class="k">Backstory</span>${escapeHtml(c.backstory || "—")}</div><div class="detail-field"><span class="k">Personality</span>${escapeHtml(c.personality || "—")}</div>
        <div class="detail-field"><span class="k">Relationships</span>${Object.entries(c.relationships || {}).map(([k,v]) => `${escapeHtml(k)}: ${escapeHtml(v)}`).join("<br>") || "—"}</div>
        <div class="detail-field"><span class="k">Knowledge</span>${(c.knowledge || []).map(escapeHtml).join("<br>") || "—"}</div></div>
        <div class="dialog-hint">esc or click outside to close</div>`;
      document.getElementById("char-drawer").classList.add("open");
    }

    function renderQuests() {
      const view = state.view;
      if (!view) return;
      const changes = view.changes?.quests || {};
      const quests = Object.values(view.state.quests || {});
      const rank = { active: 0, completed: 1, failed: 2 };
      quests.sort((a, b) => (rank[(a.status || "").toLowerCase()] ?? 0) - (rank[(b.status || "").toLowerCase()] ?? 0));

      dom.questCount.textContent = quests.length;
      dom.questList.innerHTML = quests.map((q) => {
        const status = (q.status || "active").toLowerCase();
        const cardClass = status === "active" ? "active" : ["completed", "failed"].includes(status) ? "done" : "";
        const delta = changes[q.id];
        const chips = [];
        if (delta?.new) chips.push('<span class="chip violet">new</span>');
        if (delta?.status_from) chips.push(`<span class="chip amber">${escapeHtml(delta.status_from)} →</span>`);
        if (delta?.steps_updated) chips.push('<span class="chip amber">progress</span>');
        return `
          <div class="quest-card ${cardClass}">
            <div class="quest-head">
              <span class="title">${escapeHtml(q.title || q.id)}</span>
              <span class="chip ${QUEST_COLOR[status] || ""}">${escapeHtml(status)}</span>
            </div>
            ${chips.length ? `<div class="delta-row">${chips.join("")}</div>` : ""}
            ${q.steps?.length ? `<ul class="quest-steps">${q.steps.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>` : ""}
            ${q.owner ? `<div class="quest-owner">owner: ${escapeHtml(q.owner)}</div>` : ""}
          </div>
        `;
      }).join("") || '<div class="empty">No quests.</div>';
    }

    function renderFeed() {
      const view = state.view;
      if (!view) return;
      const history = view.state.history || [];
      const clocks = view.history_clocks || [];
      const freshFrom = history.length - (view.changes?.new_history || 0);
      dom.storyCount.textContent = history.length;
      dom.feed.innerHTML = history.map((event, i) => `
        <div class="event-row ${i >= freshFrom ? "fresh" : ""}">
          <span class="clock">${escapeHtml(clocks[i] || "")}</span>
          <span class="text">${escapeHtml(event.text)}${event.location ? ` <span class="where">${escapeHtml(event.location)}</span>` : ""}</span>
        </div>
      `).join("") || '<div class="empty">Nothing has happened yet.</div>';
      dom.storyBody.scrollTop = dom.storyBody.scrollHeight;
    }

    // ── Live polling ────────────────────────────────────────

    function setLive(on) {
      state.live = on;
      dom.liveBtn.classList.toggle("on", on);
      if (state.timer) clearInterval(state.timer);
      state.timer = null;
      if (on) state.timer = setInterval(pollLive, POLL_MS);
    }

    async function pollLive() {
      try {
        state.pollCount += 1;
        if (!state.runs.length || state.pollCount % 5 === 0) {
          const runs = await fetchJson("/api/runs");
          const changed = JSON.stringify(runs) !== JSON.stringify(state.runs);
          state.runs = runs;
          if (changed) renderRuns();
          if ((!state.scenario || !state.runId) && runs.length) {
            state.scenario = runs[0].scenario;
            state.runId = runs[0].run_id;
            dom.run.value = runKey(state.scenario, state.runId);
          }
        }
        if (!state.scenario || !state.runId) return;
        // Always poll the currently selected run, not the newest — a new run
        // starting elsewhere must not yank the view away mid-session.
        const fresh = await fetchJson(`/api/state/${encodeURIComponent(state.scenario)}/${encodeURIComponent(state.runId)}`);
        const current = state.view;
        const currentLen = current ? (current.state.history || []).length : -1;
        if (!current || fresh.tick !== current.tick || (fresh.state.history || []).length !== currentLen) {
          state.view = fresh;
          renderAll();
        }
      } catch (error) {
        /* transient — snapshot mid-write or server briefly busy; retry next poll */
      }
    }

    // ── Events ──────────────────────────────────────────────

    dom.run.addEventListener("change", () => {
      const sep = dom.run.value.indexOf("/");
      state.scenario = dom.run.value.slice(0, sep);
      state.runId = dom.run.value.slice(sep + 1);
      state.mapLayout = null;
      state.selectedLoc = null;
      loadView(null).catch(() => {});
    });

    dom.mapSvg.addEventListener("click", (event) => {
      const node = event.target.closest("[data-loc]");
      if (!node) return;
      state.selectedLoc = state.selectedLoc === node.dataset.loc ? null : node.dataset.loc;
      renderMap();
      renderLocDetail();
    });

    dom.slider.addEventListener("input", () => {
      const view = state.view;
      if (!view) return;
      setLive(false);
      loadView(view.ticks[Number(dom.slider.value)]).catch(() => {});
    });

    function step(direction) {
      const view = state.view;
      if (!view) return;
      const idx = view.ticks.indexOf(view.tick) + direction;
      if (idx < 0 || idx >= view.ticks.length) return;
      setLive(false);
      loadView(view.ticks[idx]).catch(() => {});
    }

    dom.tickPrev.addEventListener("click", () => step(-1));
    dom.tickNext.addEventListener("click", () => step(1));

    dom.liveBtn.addEventListener("click", () => {
      setLive(!state.live);
      if (state.live) loadView(null).catch(() => {});
    });

    dom.charGrid.addEventListener("click", (event) => { const card=event.target.closest("[data-char]"); if(card) showCharacter(card.dataset.char); });
    document.body.addEventListener("click", (event) => {
      const close = event.target.closest("[data-close]");
      if (close) document.getElementById(close.dataset.close).classList.remove("open");
      else if (event.target.classList.contains("drawer")) event.target.classList.remove("open");
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") document.querySelectorAll(".drawer.open").forEach((d) => d.classList.remove("open"));
    });

    loadRuns().catch((error) => {
      dom.locDetail.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
    });
    setLive(true);
