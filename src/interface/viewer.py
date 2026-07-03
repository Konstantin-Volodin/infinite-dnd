"""Local web viewer for JSONL game session logs."""

from __future__ import annotations

import argparse
import json
import socket
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from src.interface.session_log import DEFAULT_LOG_DIR, list_logs, load_session

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Infinite DnD Log Viewer</title>
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

    .search {
      flex: 1;
      max-width: 380px;
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 7px 12px;
      color: var(--faint);
    }

    .search input { background: none; border: none; outline: none; color: var(--text); width: 100%; }
    .search input::placeholder { color: var(--faint); }

    .seg {
      display: flex;
      gap: 2px;
      padding: 3px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      border-radius: 8px;
    }

    .seg button {
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      color: var(--muted);
      white-space: nowrap;
    }

    .seg button:hover { color: var(--text); }
    .seg button.active { background: var(--accent); color: #1a1408; }

    .session-meta { margin-left: auto; text-align: right; font-size: 12px; color: var(--muted); min-width: 0; }
    .session-meta .title { font-weight: 600; font-size: 13px; color: var(--text); }

    /* ── Body ───────────────────────────────────────────── */

    .bodygrid { display: grid; grid-template-columns: 240px minmax(0, 1fr) 390px; min-height: 0; }

    .rail {
      border-right: 1px solid var(--border);
      padding: 16px 12px;
      overflow-y: auto;
      background: rgba(255, 255, 255, 0.015);
    }

    .rail h3 {
      font-size: 10.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--faint);
      margin: 0 6px 8px;
    }

    .rail-divider { height: 1px; background: var(--border); margin: 14px 0; }

    .session-row { display: block; width: 100%; padding: 8px 10px; border-radius: 8px; color: var(--muted); margin-bottom: 2px; }
    .session-row:hover { background: rgba(255, 255, 255, 0.05); color: var(--text); }
    .session-row.active { background: rgba(230, 180, 80, 0.13); color: var(--text); }
    .session-row .name { display: block; font-size: 12.5px; font-weight: 600; margin-bottom: 2px; }
    .session-row .sub { display: block; font-size: 11px; color: var(--faint); }
    .session-row.active .sub { color: var(--muted); }

    .filter-row {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 6px 10px;
      border-radius: 8px;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 1px;
    }

    .filter-row:hover { background: rgba(255, 255, 255, 0.05); color: var(--text); }
    .filter-row.active { background: rgba(230, 180, 80, 0.13); color: var(--text); }

    .dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; background: var(--faint); }
    .dot.violet { background: var(--accent); }
    .dot.ember { background: var(--ember); }
    .dot.green { background: var(--green); }
    .dot.amber { background: var(--amber); }

    .count { margin-left: auto; font-family: var(--mono); font-size: 10.5px; color: var(--faint); }

    /* ── Timeline ───────────────────────────────────────── */

    .log-panel { overflow-y: auto; min-width: 0; }

    .turn-header {
      position: sticky;
      top: 0;
      z-index: 5;
      display: flex;
      align-items: baseline;
      gap: 10px;
      padding: 8px 18px;
      background: rgba(10, 10, 12, 0.92);
      backdrop-filter: blur(6px);
      border-bottom: 1px solid var(--border);
      font-size: 11.5px;
      font-weight: 600;
      color: var(--text);
    }

    .turn-header .clock { font-family: var(--mono); font-weight: 400; color: var(--faint); }

    .log-row {
      display: grid;
      grid-template-columns: 58px 92px minmax(0, 1fr);
      gap: 12px;
      align-items: baseline;
      padding: 6px 18px;
      cursor: pointer;
      position: relative;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }

    .log-row:hover { background: rgba(255, 255, 255, 0.03); }
    .log-row.selected { background: rgba(230, 180, 80, 0.08); }
    .log-row.selected::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 2px; background: var(--accent); }

    .log-time { font-family: var(--mono); font-size: 11px; color: var(--faint); }

    .chip {
      display: inline-flex;
      align-items: center;
      font-size: 10.5px;
      font-weight: 600;
      letter-spacing: 0.04em;
      padding: 2px 7px;
      border-radius: 5px;
      width: fit-content;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.05);
      white-space: nowrap;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .chip.violet { color: #eac878; background: rgba(230, 180, 80, 0.14); }
    .chip.ember { color: var(--ember); background: rgba(224, 112, 77, 0.13); }
    .chip.green { color: var(--green); background: rgba(142, 201, 115, 0.12); }
    .chip.amber { color: var(--amber); background: rgba(230, 180, 80, 0.12); }

    .log-msg { color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
    .log-msg .who { color: var(--text); font-weight: 500; }
    .log-row.story .log-msg { color: var(--text); }
    .log-row.dim .log-msg { color: var(--faint); }
    .log-row.selected .log-msg { color: var(--text); }

    .stat-chips { display: inline-flex; gap: 6px; flex-wrap: wrap; }
    .stat-chips span { font-family: var(--mono); font-size: 10.5px; color: var(--faint); background: rgba(255, 255, 255, 0.04); padding: 1px 7px; border-radius: 5px; }

    .empty { padding: 26px; text-align: center; color: var(--faint); }

    /* ── Inspector ──────────────────────────────────────── */

    .inspector { border-left: 1px solid var(--border); background: var(--panel); padding: 20px; overflow-y: auto; }

    .inspector h4 {
      font-size: 10.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--faint);
      margin-bottom: 14px;
    }

    .insp-field { margin-bottom: 13px; }
    .insp-label { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--faint); margin-bottom: 3px; }
    .insp-value { font-size: 12.5px; color: var(--text); line-height: 1.55; word-break: break-word; }
    .insp-value.mono { font-family: var(--mono); font-size: 12px; }

    .pill-row { display: flex; flex-wrap: wrap; gap: 5px; }
    .pill { font-family: var(--mono); font-size: 11px; padding: 2px 8px; border-radius: 5px; background: rgba(230, 180, 80, 0.14); color: #eac878; }

    .payload {
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 13px;
      font-family: var(--mono);
      font-size: 11.5px;
      line-height: 1.65;
      color: var(--muted);
      white-space: pre-wrap;
      word-break: break-word;
      overflow-x: auto;
    }

    .payload .k { color: #eac878; }
    .payload .h { color: var(--text); font-weight: 600; }

    ::-webkit-scrollbar { width: 9px; height: 9px; }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.18); }

    @media (max-width: 1100px) {
      .bodygrid { grid-template-columns: 210px minmax(0, 1fr); }
      .inspector { display: none; }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="topbar">
      <div class="brand"><span class="brand-mark"></span>infinite-dnd</div>
      <div class="topbar-main">
        <div class="search">🔍 <input id="search" placeholder="Search logs..."></div>
        <div class="seg" id="detail-seg">
          <button data-detail="story" class="active">Story</button>
          <button data-detail="runs">Runs</button>
          <button data-detail="all">All</button>
        </div>
        <div class="session-meta">
          <div class="title" id="session-title">Waiting for logs</div>
          <div id="session-sub"></div>
        </div>
      </div>
    </div>

    <div class="bodygrid">
      <div class="rail">
        <h3>Sessions</h3>
        <div id="file-list"></div>
        <div class="rail-divider"></div>
        <h3>Events</h3>
        <div id="event-list"></div>
        <div class="rail-divider"></div>
        <h3>Agents</h3>
        <div id="label-list"></div>
      </div>

      <div class="log-panel" id="log-panel"></div>
      <div class="inspector" id="inspector"></div>
    </div>
  </div>

  <script>
    const EVENT_COLOR = {
      game_session_started: "violet",
      game_session_finished: "violet",
      pc_death: "ember",
      resolved: "green",
      world_snapshot: "amber",
      player_action: "amber",
      agent_run_started: "",
      agent_run_finished: "",
      llm_message: "",
      parse_error: "ember",
    };

    const STORY_EVENTS = new Set([
      "game_session_started", "game_session_finished", "pc_death",
      "resolved", "world_snapshot", "player_action", "parse_error",
    ]);

    const state = {
      files: [],
      session: null,
      search: "",
      detail: "story",
      eventFilter: null,
      labelFilter: null,
      selectedLine: null,
    };

    const dom = {
      fileList: document.getElementById("file-list"),
      eventList: document.getElementById("event-list"),
      labelList: document.getElementById("label-list"),
      logPanel: document.getElementById("log-panel"),
      inspector: document.getElementById("inspector"),
      search: document.getElementById("search"),
      detailSeg: document.getElementById("detail-seg"),
      sessionTitle: document.getElementById("session-title"),
      sessionSub: document.getElementById("session-sub"),
    };

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatDateTime(value) {
      if (!value) return "unknown";
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
    }

    function formatDuration(value) {
      if (value === null || value === undefined) return "--";
      return `${Number(value).toFixed(1)}s`;
    }

    async function fetchJson(path) {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      return response.json();
    }

    async function loadFiles() {
      state.files = await fetchJson("/api/files");
      renderFiles();
      if (!state.files.length) {
        dom.logPanel.innerHTML = '<div class="empty">No log files were found in the selected directory.</div>';
        return;
      }
      await loadSession(state.files[0].name);
    }

    async function loadSession(name) {
      state.session = await fetchJson(`/api/logs/${encodeURIComponent(name)}`);
      state.eventFilter = null;
      state.labelFilter = null;
      state.selectedLine = null;
      renderAll();
    }

    function renderAll() {
      renderFiles();
      renderTopbar();
      renderRailFilters();
      renderRows();
      renderInspector();
    }

    function renderFiles() {
      if (!state.files.length) {
        dom.fileList.innerHTML = '<div class="empty">No logs found.</div>';
        return;
      }
      dom.fileList.innerHTML = state.files.map((file) => {
        const active = state.session && state.session.file === file.name;
        const title = file.scenario_title || "Unknown campaign";
        const sub = `${file.character_id || "?"} · ${file.turns_completed ?? "?"}/${file.max_turns ?? "?"} turns`;
        return `
          <button class="session-row ${active ? "active" : ""}" data-file="${escapeHtml(file.name)}" title="${escapeHtml(file.name)}">
            <span class="name">${escapeHtml(title)}</span>
            <span class="sub">${escapeHtml(sub)} · ${escapeHtml(formatDateTime(file.modified_time))}</span>
          </button>
        `;
      }).join("");
    }

    function renderTopbar() {
      const session = state.session;
      if (!session) return;
      const summary = session.summary;
      const title = summary.scenario_title || session.file;
      dom.sessionTitle.textContent = summary.character_id ? `${title} · ${summary.character_id}` : title;
      dom.sessionSub.textContent =
        `${summary.turns_completed ?? 0}/${summary.max_turns ?? "?"} turns · ` +
        `${session.stats.run_count} runs · ${formatDuration(summary.duration_s)}`;
    }

    function renderRailFilters() {
      const session = state.session;
      if (!session) return;

      const events = session.event_types.filter((event) => event !== "turn_started");
      dom.eventList.innerHTML = events.map((event) => `
        <button class="filter-row ${state.eventFilter === event ? "active" : ""}" data-event="${escapeHtml(event)}">
          <span class="dot ${EVENT_COLOR[event] || ""}"></span>${escapeHtml(event.replaceAll("_", " "))}
          <span class="count">${escapeHtml(session.event_counts[event])}</span>
        </button>
      `).join("");

      const labels = [...new Set(session.runs.map((run) => run.label))];
      const labelCounts = {};
      session.entries.forEach((entry) => {
        if (entry.label) labelCounts[entry.label] = (labelCounts[entry.label] || 0) + 1;
      });
      dom.labelList.innerHTML = labels.length
        ? labels.map((label) => `
            <button class="filter-row ${state.labelFilter === label ? "active" : ""}" data-label="${escapeHtml(label)}">
              <span class="dot violet"></span>${escapeHtml(label)}
              <span class="count">${escapeHtml(labelCounts[label] || 0)}</span>
            </button>
          `).join("")
        : '<div class="empty">No agent runs recorded.</div>';
    }

    function detailAllows(entry) {
      if (state.detail === "all") return true;
      if (state.detail === "runs") return entry.event !== "llm_message";
      return STORY_EVENTS.has(entry.event);
    }

    function filteredEntries() {
      if (!state.session) return [];
      const search = state.search.trim().toLowerCase();
      return state.session.entries.filter((entry) => {
        if (entry.event === "turn_started") return false;
        if (state.eventFilter ? entry.event !== state.eventFilter : !detailAllows(entry)) return false;
        if (state.labelFilter && entry.label !== state.labelFilter) return false;
        if (!search) return true;
        const haystack = [entry.summary, entry.excerpt, entry.label, entry.event, entry.raw_pretty]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(search);
      });
    }

    function rowContent(entry) {
      const raw = entry.raw || {};
      if (entry.event === "resolved" && raw.result) {
        const who = raw.subject ? `<span class="who">${escapeHtml(raw.subject)}</span> ` : "";
        return `${who}${escapeHtml(raw.result)}`;
      }
      if (entry.event === "world_snapshot") {
        const stats = [
          ["locations", raw.locations], ["characters", raw.characters],
          ["quests done", raw.quests_completed], ["xp", raw.total_xp], ["game min", raw.minutes_elapsed],
        ].filter(([, value]) => value !== undefined);
        return `<span class="stat-chips">${stats.map(([key, value]) => `<span>${escapeHtml(value)} ${escapeHtml(key)}</span>`).join("")}</span>`;
      }
      if (entry.event === "llm_message") {
        const tools = [...(entry.tool_calls || []), ...(entry.tool_returns || [])];
        if (tools.length) return `→ ${escapeHtml(tools.join(", "))}${entry.excerpt ? ` · ${escapeHtml(entry.excerpt)}` : ""}`;
        return escapeHtml(entry.excerpt || entry.summary);
      }
      return escapeHtml(entry.summary);
    }

    function rowChip(entry) {
      if (entry.event === "llm_message") {
        const kind = { model_request: "request", model_response: "response", tool_return: "tool ret" }[entry.message_kind] || "llm";
        return `<span class="chip">${escapeHtml(kind)}</span>`;
      }
      if (entry.event === "agent_run_started" || entry.event === "agent_run_finished") {
        const suffix = entry.event === "agent_run_finished" ? " ✓" : " …";
        return `<span class="chip violet">${escapeHtml((entry.label || "run") + suffix)}</span>`;
      }
      const label = { game_session_started: "session", game_session_finished: "session", world_snapshot: "world", player_action: "player", pc_death: "death", resolved: (entry.raw || {}).tool || "resolved", parse_error: "error" }[entry.event] || entry.event.replaceAll("_", " ");
      return `<span class="chip ${EVENT_COLOR[entry.event] || ""}">${escapeHtml(label.toLowerCase())}</span>`;
    }

    function rowClass(entry) {
      if (entry.event === "resolved" || entry.event === "pc_death") return "story";
      if (entry.event === "llm_message" || entry.event === "agent_run_started" || entry.event === "agent_run_finished") return "dim";
      return "";
    }

    function renderRows() {
      const entries = filteredEntries();
      if (!entries.length) {
        dom.logPanel.innerHTML = '<div class="empty">No events match the current filters.</div>';
        return;
      }

      const chunks = [];
      let currentTurn;
      for (const entry of entries) {
        if (entry.turn !== currentTurn) {
          currentTurn = entry.turn;
          const title = currentTurn === null || currentTurn === undefined ? "Session" : `Turn ${currentTurn}`;
          chunks.push(`<div class="turn-header">${escapeHtml(title)}<span class="clock">${escapeHtml(entry.display_time)}</span></div>`);
        }
        chunks.push(`
          <div class="log-row ${rowClass(entry)} ${state.selectedLine === entry.line ? "selected" : ""}" data-line="${entry.line}">
            <span class="log-time">${escapeHtml(entry.display_time)}</span>
            ${rowChip(entry)}
            <span class="log-msg">${rowContent(entry)}</span>
          </div>
        `);
      }
      dom.logPanel.innerHTML = chunks.join("");
    }

    function highlightPayload(text) {
      return escapeHtml(text)
        .replace(/^(ModelRequest|ModelResponse)(.*)$/m, '<span class="h">$1</span>$2')
        .replace(/^(\\s*)([\\w.-]+):/gm, '$1<span class="k">$2</span>:');
    }

    function renderInspector() {
      const session = state.session;
      if (!session) {
        dom.inspector.innerHTML = "";
        return;
      }
      const entry = session.entries.find((candidate) => candidate.line === state.selectedLine);
      if (!entry) {
        renderSessionInspector(session);
        return;
      }

      const tools = [...(entry.tool_calls || []), ...(entry.tool_returns || [])];
      const usage = entry.usage
        ? Object.entries(entry.usage).map(([key, value]) => `${key.replace("_tokens", "")} ${value.toLocaleString()}`).join(" · ")
        : null;

      dom.inspector.innerHTML = `
        <h4>Event Detail</h4>
        <div class="insp-field"><div class="insp-label">Summary</div><div class="insp-value">${escapeHtml(entry.summary)}</div></div>
        <div class="insp-field"><div class="insp-label">Event</div><div class="insp-value mono">${escapeHtml(entry.message_kind || entry.event)}</div></div>
        ${entry.label ? `<div class="insp-field"><div class="insp-label">Agent</div><div class="insp-value mono">${escapeHtml(entry.label)}</div></div>` : ""}
        <div class="insp-field"><div class="insp-label">Time</div><div class="insp-value mono">${escapeHtml(entry.display_time)} · turn ${escapeHtml(entry.turn ?? "-")} · line ${escapeHtml(entry.line)}</div></div>
        ${tools.length ? `<div class="insp-field"><div class="insp-label">Tools</div><div class="pill-row">${tools.map((tool) => `<span class="pill">${escapeHtml(tool)}</span>`).join("")}</div></div>` : ""}
        ${usage ? `<div class="insp-field"><div class="insp-label">Tokens</div><div class="insp-value mono">${escapeHtml(usage)}</div></div>` : ""}
        <div class="insp-field"><div class="insp-label">Payload</div><div class="payload">${highlightPayload(entry.raw_pretty || JSON.stringify(entry.raw, null, 2))}</div></div>
      `;
    }

    function renderSessionInspector(session) {
      const summary = session.summary;
      const tokens = { input_tokens: 0, output_tokens: 0 };
      session.runs.forEach((run) => {
        Object.keys(tokens).forEach((key) => { tokens[key] += run.tokens?.[key] || 0; });
      });

      dom.inspector.innerHTML = `
        <h4>Session Overview</h4>
        <div class="insp-field"><div class="insp-label">Campaign</div><div class="insp-value">${escapeHtml(summary.scenario_title || "unknown")}</div></div>
        <div class="insp-field"><div class="insp-label">Character</div><div class="insp-value mono">${escapeHtml(summary.character_id || "unknown")}</div></div>
        <div class="insp-field"><div class="insp-label">Started</div><div class="insp-value">${escapeHtml(formatDateTime(summary.started_at))}</div></div>
        <div class="insp-field"><div class="insp-label">Duration</div><div class="insp-value">${escapeHtml(formatDuration(summary.duration_s))} · ${escapeHtml(summary.turns_completed ?? 0)}/${escapeHtml(summary.max_turns ?? "?")} turns</div></div>
        <div class="insp-field"><div class="insp-label">Traffic</div><div class="insp-value">${escapeHtml(session.stats.run_count)} agent runs · ${escapeHtml(session.stats.llm_message_count)} LLM messages</div></div>
        <div class="insp-field"><div class="insp-label">Tokens</div><div class="insp-value mono">${escapeHtml(tokens.input_tokens.toLocaleString())} in · ${escapeHtml(tokens.output_tokens.toLocaleString())} out</div></div>
        ${session.stats.error_count ? `<div class="insp-field"><div class="insp-label">Parse errors</div><div class="insp-value">${escapeHtml(session.stats.error_count)}</div></div>` : ""}
        <div class="insp-field"><div class="insp-label">File</div><div class="insp-value mono">${escapeHtml(session.path)}</div></div>
        <div class="empty">Select a log row to inspect its payload.</div>
      `;
    }

    dom.fileList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-file]");
      if (button) loadSession(button.dataset.file);
    });

    dom.eventList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-event]");
      if (!button) return;
      state.eventFilter = state.eventFilter === button.dataset.event ? null : button.dataset.event;
      renderRailFilters();
      renderRows();
    });

    dom.labelList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-label]");
      if (!button) return;
      state.labelFilter = state.labelFilter === button.dataset.label ? null : button.dataset.label;
      renderRailFilters();
      renderRows();
    });

    dom.detailSeg.addEventListener("click", (event) => {
      const button = event.target.closest("[data-detail]");
      if (!button) return;
      state.detail = button.dataset.detail;
      dom.detailSeg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === button));
      renderRows();
    });

    dom.logPanel.addEventListener("click", (event) => {
      const row = event.target.closest("[data-line]");
      if (!row) return;
      state.selectedLine = state.selectedLine === Number(row.dataset.line) ? null : Number(row.dataset.line);
      renderRows();
      renderInspector();
    });

    dom.search.addEventListener("input", (event) => {
      state.search = event.target.value;
      renderRows();
    });

    loadFiles().catch((error) => {
      dom.logPanel.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
    });
  </script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch the Infinite DnD log viewer.")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_LOG_DIR), help="Log file or directory to inspect.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Preferred port for the local server.")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open a browser tab.")
    args = parser.parse_args(argv)

    target = Path(args.path)
    if not target.exists():
        parser.error(f"Path not found: {target}")

    server = ThreadingHTTPServer((args.host, _pick_port(args.host, args.port)), _build_handler(target))
    url = f"http://{args.host}:{server.server_port}"
    print(f"Serving log viewer at {url}")
    print(f"Reading logs from {target.resolve()}")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping log viewer.")
    finally:
        server.server_close()

    return 0


def _build_handler(target: Path) -> type[BaseHTTPRequestHandler]:
    class LogViewerHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(_HTML)
                return
            if parsed.path == "/api/files":
                self._send_json(list_logs(target))
                return
            if parsed.path.startswith("/api/logs/"):
                log_name = unquote(parsed.path.removeprefix("/api/logs/"))
                log_path = self._resolve_log_path(log_name)
                if log_path is None:
                    self._send_json({"error": f"Log not found: {log_name}"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json(load_session(log_path))
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _resolve_log_path(self, log_name: str) -> Path | None:
            for metadata in list_logs(target):
                if metadata["name"] == log_name:
                    return Path(metadata["path"])
            return None

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

    return LogViewerHandler


def _pick_port(host: str, preferred: int) -> int:
    for candidate in [preferred, *range(preferred + 1, preferred + 10), 0]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, candidate))
            except OSError:
                continue
            return sock.getsockname()[1]
    raise RuntimeError("Could not find an available port for the log viewer.")
