"""Local web dashboard for world-state snapshots: characters, quests, locations, and history per tick."""

from __future__ import annotations

import argparse
import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from src.interface.viewer import _pick_port
from src.interface.world_state import DEFAULT_STATE_DIR, list_state_scenarios, load_series, load_view

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Infinite DnD World Dashboard</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
      --bg: #0a0a0c;
      --panel: #131316;
      --border: rgba(255, 255, 255, 0.07);
      --text: #e8e8ec;
      --muted: #8b8b96;
      --faint: #57575f;
      --accent: #e6b450;
      --ember: #e0704d;
      --green: #8ec973;
      --amber: #e6b450;
      --mono: "JetBrains Mono", "Cascadia Code", "Consolas", monospace;
      --sans: "Inter", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    html, body { height: 100%; }

    body {
      color: var(--text);
      font-family: var(--sans);
      font-size: 13px;
      background: var(--bg);
      -webkit-font-smoothing: antialiased;
    }

    button, input, select { font: inherit; color: inherit; }
    button { cursor: pointer; background: none; border: none; text-align: left; }
    :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 6px; }

    .app { display: grid; grid-template-rows: auto 1fr; height: 100vh; }

    /* ── Topbar ─────────────────────────────────────────── */

    .topbar {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 12px 18px 14px;
      background: var(--panel);
      border-bottom: 1px solid var(--border);
    }

    .brand { display: flex; align-items: center; gap: 9px; font-weight: 600; font-size: 14px; white-space: nowrap; }
    .brand-mark { width: 18px; height: 18px; border-radius: 5px; background: linear-gradient(135deg, var(--accent), var(--ember)); flex-shrink: 0; }

    .topbar-main { display: flex; align-items: center; gap: 14px; }

    .tabs { display: flex; gap: 2px; padding: 3px; background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border); border-radius: 8px; }
    .tabs a { padding: 5px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; color: var(--muted); text-decoration: none; white-space: nowrap; }
    .tabs a:hover { color: var(--text); }
    .tabs a.active { background: var(--accent); color: #1a1408; }

    select#scenario {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 6px 10px;
      color: var(--text);
      max-width: 260px;
    }
    select#scenario option { background: var(--panel); }

    .tick-controls { display: flex; align-items: center; gap: 8px; flex: 1; max-width: 460px; }
    .tick-controls button {
      padding: 4px 9px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      color: var(--muted);
      font-size: 12px;
    }
    .tick-controls button:hover { color: var(--text); }
    .tick-controls input[type="range"] { flex: 1; accent-color: var(--accent); }
    .tick-label { font-family: var(--mono); font-size: 11px; color: var(--muted); white-space: nowrap; }

    .live-btn {
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 5px 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.04);
      font-size: 12px;
      font-weight: 600;
      color: var(--muted);
      white-space: nowrap;
    }
    .live-btn .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--faint); }
    .live-btn.on { color: #1a1408; background: var(--accent); border-color: var(--accent); }
    .live-btn.on .dot { background: #1a1408; animation: pulse 1.4s ease-in-out infinite; }
    @keyframes pulse { 50% { opacity: 0.3; } }

    .session-meta { margin-left: auto; text-align: right; font-size: 12px; color: var(--muted); min-width: 0; }
    .session-meta .title { font-weight: 600; font-size: 13px; color: var(--text); }
    .session-meta .clock { font-family: var(--mono); }

    /* ── Body ───────────────────────────────────────────── */

    .bodygrid { display: grid; grid-template-columns: 310px minmax(0, 1fr) 390px; min-height: 0; }

    .rail {
      border-right: 1px solid var(--border);
      padding: 16px 12px 12px;
      background: rgba(255, 255, 255, 0.015);
      display: grid;
      grid-template-rows: auto minmax(230px, 46%) minmax(0, 1fr);
      gap: 10px;
      min-height: 0;
    }

    h3.section {
      font-size: 10.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--faint);
      margin: 0 6px 8px;
    }

    /* ── Map ────────────────────────────────────────────── */

    .map-wrap {
      position: relative;
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      min-height: 0;
      background: #0d0d10;
    }
    .map-wrap svg { width: 100%; height: 100%; display: block; }

    .map-edge { stroke: rgba(255, 255, 255, 0.12); stroke-width: 1.3; }

    .map-node { cursor: pointer; }
    .map-node .body { fill: #17171c; stroke: rgba(255, 255, 255, 0.25); stroke-width: 1.3; transition: fill 0.3s ease, stroke 0.3s ease; }
    .map-node:hover .body { stroke: var(--text); }
    .map-node.occupied .body { fill: #20202a; stroke: rgba(255, 255, 255, 0.45); }
    .map-node.pc .body { fill: rgba(230, 180, 80, 0.30); stroke: var(--accent); }
    .map-node.fresh .body { stroke: var(--green); }
    .map-node .halo { fill: none; stroke: rgba(255, 255, 255, 0.35); stroke-dasharray: 3 3; }
    .map-node .label { fill: var(--muted); font-family: var(--mono); font-size: 10.5px; text-anchor: middle; pointer-events: none; }
    .map-node.pc .label { fill: #eac878; }
    .map-node .count { fill: var(--text); font-family: var(--mono); font-size: 10px; font-weight: 600; text-anchor: middle; pointer-events: none; }
    .map-node .items-dot { fill: var(--amber); }

    .loc-detail { overflow-y: auto; padding: 2px 6px; min-height: 0; }
    .loc-head { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
    .loc-head .name { font-weight: 600; font-size: 13px; }
    .loc-desc { font-size: 11.5px; color: var(--muted); line-height: 1.55; margin-bottom: 8px; }
    .loc-field { margin-bottom: 9px; }
    .loc-field .k { display: block; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--faint); margin-bottom: 3px; }
    .loc-detail .who { font-size: 12px; color: var(--muted); line-height: 1.6; }
    .loc-detail .pc { color: #eac878; font-weight: 600; }
    .loc-detail .dead { color: var(--faint); text-decoration: line-through; }

    /* ── Characters ─────────────────────────────────────── */

    .char-panel { overflow-y: auto; padding: 16px 18px; min-width: 0; }

    .char-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }

    .char-card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
      min-width: 0;
    }
    .char-card:hover { border-color: rgba(255, 255, 255, 0.14); }
    .char-card.pc { border-color: rgba(230, 180, 80, 0.45); }
    .char-card.dead { opacity: 0.55; }
    .char-card.changed { border-color: rgba(230, 180, 80, 0.4); }

    .char-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 9px; }
    .char-head .name { font-weight: 600; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    .chip {
      display: inline-flex;
      align-items: center;
      font-size: 10.5px;
      font-weight: 600;
      letter-spacing: 0.04em;
      padding: 2px 7px;
      border-radius: 5px;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.05);
      white-space: nowrap;
    }
    .chip.violet { color: #eac878; background: rgba(230, 180, 80, 0.14); }
    .chip.ember { color: var(--ember); background: rgba(224, 112, 77, 0.13); }
    .chip.green { color: var(--green); background: rgba(142, 201, 115, 0.12); }
    .chip.amber { color: var(--amber); background: rgba(230, 180, 80, 0.12); }

    .hp-bar { height: 6px; border-radius: 4px; background: rgba(255, 255, 255, 0.06); overflow: hidden; margin: 8px 0 4px; }
    .hp-bar span { display: block; height: 100%; border-radius: 4px; background: var(--green); transition: width 0.4s ease; }
    .hp-bar.mid span { background: var(--amber); }
    .hp-bar.low span { background: var(--ember); }

    .stat-line { display: flex; justify-content: space-between; font-family: var(--mono); font-size: 11.5px; color: var(--muted); }

    .char-loc { font-size: 11.5px; color: var(--muted); margin-top: 8px; }
    .char-loc .at { color: var(--faint); }

    .inv-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 7px; }
    .pill { font-family: var(--mono); font-size: 10.5px; padding: 1px 7px; border-radius: 5px; background: rgba(255, 255, 255, 0.05); color: var(--muted); }

    .char-goal { font-size: 11.5px; color: var(--faint); margin-top: 8px; line-height: 1.5; }

    .delta-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }

    /* ── Right column ───────────────────────────────────── */

    .side { border-left: 1px solid var(--border); background: var(--panel); display: grid; grid-template-rows: auto 1fr; min-height: 0; }

    .quests { padding: 16px; overflow-y: auto; max-height: 45%; border-bottom: 1px solid var(--border); }

    .quest-card { border: 1px solid var(--border); border-radius: 9px; padding: 11px 12px; margin-bottom: 8px; }
    .quest-card:hover { border-color: rgba(255, 255, 255, 0.14); }
    .quest-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
    .quest-head .title { font-weight: 600; font-size: 12.5px; }
    .quest-steps { margin: 7px 0 0; padding-left: 16px; color: var(--muted); font-size: 11.5px; line-height: 1.6; }
    .quest-owner { font-size: 10.5px; color: var(--faint); margin-top: 5px; font-family: var(--mono); }

    .history { display: grid; grid-template-rows: auto 1fr; min-height: 0; padding: 16px 0 0; }
    .history h3.section { padding: 0 16px; }
    .feed { overflow-y: auto; padding: 0 16px 16px; }

    .event-row { display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 10px; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.03); }
    .event-row .clock { font-family: var(--mono); font-size: 10.5px; color: var(--faint); padding-top: 2px; }
    .event-row .text { font-size: 12px; color: var(--muted); line-height: 1.55; word-break: break-word; }
    .event-row.fresh .text { color: var(--text); }
    .event-row .where { color: var(--faint); font-size: 10.5px; }

    .empty { padding: 26px; text-align: center; color: var(--faint); }

    .drawer { position: fixed; z-index: 20; inset: 0; background: rgba(0,0,0,.72); display: none; align-items: center; justify-content: center; }
    .drawer.open { display: flex; }
    .dialog { width: min(620px, calc(100vw - 32px)); max-height: calc(100vh - 40px); overflow: auto; background: var(--panel); border: 1px solid rgba(230,180,80,.3); border-radius: 12px; padding: 22px; box-shadow: 0 24px 70px #000; }
    .dialog-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; }
    .dialog h2 { margin:0; font-size:17px; }
    .char-card { cursor:pointer; }
    .spark { width:82px; height:22px; margin-left:auto; overflow:visible; }
    .spark polyline { fill:none; stroke:var(--accent); stroke-width:1.5; vector-effect:non-scaling-stroke; }
    .detail-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    .detail-field { border-top:1px solid var(--border); padding-top:10px; }
    .detail-field .k { display:block; color:var(--accent); font:10px var(--mono); text-transform:uppercase; margin-bottom:6px; }

    ::-webkit-scrollbar { width: 9px; height: 9px; }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.18); }

    @media (max-width: 1100px) {
      .bodygrid { grid-template-columns: 260px minmax(0, 1fr); }
      .side { display: none; }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="topbar">
      <div class="brand"><span class="brand-mark"></span>infinite-dnd</div>
      <div class="topbar-main">
        <select id="scenario"></select>
        <div class="tick-controls">
          <button id="tick-prev" title="Previous tick">‹</button>
          <input type="range" id="tick-slider" min="0" max="0" value="0">
          <button id="tick-next" title="Next tick">›</button>
          <span class="tick-label" id="tick-label">tick –</span>
        </div>
        <button class="live-btn" id="live-btn"><span class="dot"></span>LIVE</button>
        <div class="session-meta">
          <div class="title" id="meta-title">Waiting for snapshots</div>
          <div id="meta-sub"><span class="clock" id="meta-clock"></span> <span id="meta-quests"></span></div>
        </div>
      </div>
    </div>

    <div class="bodygrid">
      <div class="rail">
        <h3 class="section">Map</h3>
        <div class="map-wrap"><svg id="map-svg" viewBox="0 0 100 100"></svg></div>
        <div class="loc-detail" id="loc-detail"></div>
      </div>

      <div class="char-panel">
        <h3 class="section">Characters</h3>
        <div class="char-grid" id="char-grid"></div>
      </div>

      <div class="side">
        <div class="quests">
          <h3 class="section">Quests</h3>
          <div id="quest-list"></div>
        </div>
        <div class="history">
          <h3 class="section">History</h3>
          <div class="feed" id="feed"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="drawer" id="char-drawer"><div class="dialog" id="char-detail"></div></div>

  <script>
    const POLL_MS = 1000;
    const QUEST_COLOR = { active: "amber", completed: "green", failed: "ember" };

    const state = {
      scenarios: [],
      scenario: null,
      view: null,
      live: true,
      timer: null,
      pollCount: 0,
      mapLayout: null,
      selectedLoc: null,
      series: {},
    };

    const dom = {
      scenario: document.getElementById("scenario"),
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
      questList: document.getElementById("quest-list"),
      feed: document.getElementById("feed"),
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

    async function loadScenarios() {
      state.scenarios = await fetchJson("/api/scenarios");
      renderScenarios();
      if (!state.scenarios.length) {
        dom.charGrid.innerHTML = "";
        dom.metaTitle.textContent = "No snapshots yet";
        dom.locDetail.innerHTML = '<div class="empty">Run a game to produce world-state snapshots.</div>';
        return;
      }
      if (!state.scenario || !state.scenarios.some((s) => s.scenario === state.scenario)) {
        state.scenario = state.scenarios[0].scenario;
        dom.scenario.value = state.scenario;
      }
      await loadView(null);
    }

    async function loadView(tick) {
      if (!state.scenario) return;
      const query = tick === null || tick === undefined ? "" : `?tick=${tick}`;
      state.view = await fetchJson(`/api/state/${encodeURIComponent(state.scenario)}${query}`);
      state.series = await fetchJson(`/api/series/${encodeURIComponent(state.scenario)}`);
      renderAll();
    }

    function renderScenarios() {
      dom.scenario.innerHTML = state.scenarios.map((s) => `
        <option value="${escapeHtml(s.scenario)}" ${s.scenario === state.scenario ? "selected" : ""}>
          ${escapeHtml(s.title)} (${escapeHtml(s.tick_count)} ticks)
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
        <div class="detail-field"><span class="k">Knowledge</span>${(c.knowledge || []).map(escapeHtml).join("<br>") || "—"}</div></div>`;
      document.getElementById("char-drawer").classList.add("open");
    }

    function renderQuests() {
      const view = state.view;
      if (!view) return;
      const changes = view.changes?.quests || {};
      const quests = Object.values(view.state.quests || {});
      const rank = { active: 0, completed: 1, failed: 2 };
      quests.sort((a, b) => (rank[(a.status || "").toLowerCase()] ?? 0) - (rank[(b.status || "").toLowerCase()] ?? 0));

      dom.questList.innerHTML = quests.map((q) => {
        const status = (q.status || "active").toLowerCase();
        const delta = changes[q.id];
        const chips = [];
        if (delta?.new) chips.push('<span class="chip violet">new</span>');
        if (delta?.status_from) chips.push(`<span class="chip amber">${escapeHtml(delta.status_from)} →</span>`);
        if (delta?.steps_updated) chips.push('<span class="chip amber">progress</span>');
        return `
          <div class="quest-card">
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
      dom.feed.innerHTML = history.map((event, i) => `
        <div class="event-row ${i >= freshFrom ? "fresh" : ""}">
          <span class="clock">${escapeHtml(clocks[i] || "")}</span>
          <span class="text">${escapeHtml(event.text)} <span class="where">· ${escapeHtml(event.location || "")}</span></span>
        </div>
      `).join("") || '<div class="empty">Nothing has happened yet.</div>';
      dom.feed.scrollTop = dom.feed.scrollHeight;
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
        if (!state.scenarios.length || state.pollCount % 5 === 0) {
          const scenarios = await fetchJson("/api/scenarios");
          const changed = JSON.stringify(scenarios) !== JSON.stringify(state.scenarios);
          state.scenarios = scenarios;
          if (changed) renderScenarios();
          if (!state.scenario && scenarios.length) {
            state.scenario = scenarios[0].scenario;
            dom.scenario.value = state.scenario;
          }
        }
        if (!state.scenario) return;
        const fresh = await fetchJson(`/api/state/${encodeURIComponent(state.scenario)}`);
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

    dom.scenario.addEventListener("change", () => {
      state.scenario = dom.scenario.value;
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
    document.body.addEventListener("click", (event) => { const close=event.target.closest("[data-close]"); if(close) document.getElementById(close.dataset.close).classList.remove("open"); });

    loadScenarios().catch((error) => {
      dom.locDetail.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
    });
    setLive(true);
  </script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch the Infinite DnD world-state dashboard.")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_STATE_DIR), help="World-state directory to watch.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8766, help="Preferred port for the local server.")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open a browser tab.")
    args = parser.parse_args(argv)

    target = Path(args.path)
    server = ThreadingHTTPServer((args.host, _pick_port(args.host, args.port)), _build_handler(target))
    url = f"http://{args.host}:{server.server_port}"
    print(f"Serving world dashboard at {url}")
    print(f"Watching snapshots in {target.resolve()}")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping world dashboard.")
    finally:
        server.server_close()

    return 0


def _build_handler(state_dir: Path) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(_HTML)
                return
            if parsed.path == "/api/scenarios":
                self._send_json(list_state_scenarios(state_dir))
                return
            if parsed.path.startswith("/api/state/"):
                scenario = unquote(parsed.path.removeprefix("/api/state/"))
                if not _is_known_scenario(scenario):
                    self._send_json({"error": f"Scenario not found: {scenario}"}, status=HTTPStatus.NOT_FOUND)
                    return
                tick_values = parse_qs(parsed.query).get("tick")
                try:
                    tick = int(tick_values[0]) if tick_values else None
                except ValueError:
                    self._send_json({"error": f"Invalid tick: {tick_values[0]}"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    self._send_json(load_view(state_dir, scenario, tick))
                except FileNotFoundError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
                return
            if parsed.path.startswith("/api/series/"):
                scenario = unquote(parsed.path.removeprefix("/api/series/"))
                if not _is_known_scenario(scenario):
                    self._send_json({"error": f"Scenario not found: {scenario}"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json(load_series(state_dir, scenario))
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    def _is_known_scenario(scenario: str) -> bool:
        # Path traversal guard: only serve scenario names discovered under the state dir.
        return any(meta["scenario"] == scenario for meta in list_state_scenarios(state_dir))

    return DashboardHandler


if __name__ == "__main__":
    raise SystemExit(main())
