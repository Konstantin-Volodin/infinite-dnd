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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Spectral:wght@500;600&display=swap');

    :root {
      --bg: #16141a;
      --panel: rgba(28, 25, 36, 0.85);
      --paper: #ece7e0;
      --muted: #a89fb0;
      --faint: #6f6779;
      --gold: #e8b94f;
      --jade: #7fa08c;
      --crimson: #b56159;
      --amber: #c17f3a;
      --line: rgba(232, 185, 79, 0.14);
      --radius: 3px;
      --mono: "JetBrains Mono", "Cascadia Code", "Consolas", monospace;
      --serif: "Spectral", "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      --sans: "Inter", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    html, body { height: 100%; }

    body {
      color: var(--paper);
      font-family: var(--sans);
      background: var(--bg);
      -webkit-font-smoothing: antialiased;
    }

    button, input, select { font: inherit; color: inherit; }
    button { cursor: pointer; }
    :focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; border-radius: 4px; }

    .app { display: grid; grid-template-rows: auto 1fr; height: 100vh; }

    /* ── Topbar ─────────────────────────────────────────── */

    .topbar {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 14px 20px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: var(--serif);
      font-weight: 600;
      font-size: 15px;
      white-space: nowrap;
    }

    .brand-mark {
      width: 20px;
      height: 20px;
      border-radius: 4px;
      background: linear-gradient(135deg, var(--gold), var(--amber));
      flex-shrink: 0;
    }

    .search {
      flex: 1;
      max-width: 420px;
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 0, 0, 0.18);
      border: 1px solid var(--line);
      border-radius: 4px;
      padding: 8px 12px;
      color: var(--muted);
      font-size: 13px;
    }

    .search input { background: none; border: none; outline: none; color: var(--paper); width: 100%; }
    .search input::placeholder { color: var(--faint); }

    .turn-select {
      padding: 8px 10px;
      border-radius: 4px;
      border: 1px solid var(--line);
      background: rgba(0, 0, 0, 0.18);
      color: var(--paper);
      font-size: 13px;
    }

    .session-meta { margin-left: auto; text-align: right; font-size: 12.5px; color: var(--muted); min-width: 0; }
    .session-meta .title { font-family: var(--serif); font-size: 14px; color: var(--paper); }

    /* ── Body grid ──────────────────────────────────────── */

    .bodygrid { display: grid; grid-template-columns: 250px minmax(0, 1fr) 400px; min-height: 0; }

    .rail {
      border-right: 1px solid var(--line);
      padding: 18px 14px;
      overflow-y: auto;
      background: rgba(0, 0, 0, 0.12);
    }

    .rail h3 {
      font-family: var(--serif);
      font-style: italic;
      font-weight: 500;
      font-size: 12px;
      letter-spacing: 0.02em;
      color: var(--faint);
      margin-bottom: 10px;
    }

    .rail-divider { height: 1px; background: var(--line); margin: 16px 0; }

    .session-row {
      display: block;
      width: 100%;
      text-align: left;
      padding: 9px 10px;
      border-radius: var(--radius);
      background: none;
      border: none;
      color: var(--muted);
      margin-bottom: 2px;
    }

    .session-row:hover { background: rgba(255, 255, 255, 0.05); color: var(--paper); }

    .session-row.active {
      background: rgba(255, 255, 255, 0.06);
      color: var(--paper);
      box-shadow: inset 2px 0 0 0 var(--gold);
    }

    .session-row .name { display: block; font-size: 13px; font-weight: 600; margin-bottom: 2px; }
    .session-row .sub { display: block; font-size: 11.5px; color: var(--faint); font-family: var(--mono); }

    .filter-row {
      display: flex;
      align-items: center;
      gap: 9px;
      width: 100%;
      padding: 7px 8px;
      border-radius: var(--radius);
      background: none;
      border: none;
      text-align: left;
      font-size: 12.5px;
      color: var(--muted);
      margin-bottom: 1px;
      font-family: var(--mono);
    }

    .filter-row:hover { background: rgba(255, 255, 255, 0.05); color: var(--paper); }

    .filter-row.active {
      background: rgba(255, 255, 255, 0.06);
      color: var(--paper);
      box-shadow: inset 2px 0 0 0 var(--gold);
    }

    .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; background: var(--faint); }
    .dot.gold { background: var(--gold); }
    .dot.jade { background: var(--jade); }
    .dot.amber { background: var(--amber); }
    .dot.crimson { background: var(--crimson); }

    .count { margin-left: auto; font-family: var(--mono); font-size: 11px; color: var(--faint); }

    /* ── Log rows ───────────────────────────────────────── */

    .log-panel {
      overflow-y: auto;
      min-width: 0;
      background-image: repeating-linear-gradient(
        to bottom,
        transparent,
        transparent 40px,
        rgba(232, 185, 79, 0.035) 41px
      );
    }

    .log-row {
      display: grid;
      grid-template-columns: 66px 118px 42px 148px minmax(0, 1fr);
      gap: 12px;
      align-items: center;
      padding: 8px 18px;
      font-family: var(--mono);
      font-size: 12.5px;
      border-bottom: 1px solid var(--line);
      cursor: pointer;
      position: relative;
    }

    .log-row:hover { background: rgba(255, 255, 255, 0.03); }
    .log-row.selected { background: rgba(255, 255, 255, 0.045); }

    .log-row.selected::before {
      content: "";
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 2px;
      background: var(--gold);
    }

    .log-time { color: var(--faint); }
    .log-turn { color: var(--faint); }
    .log-label { color: var(--gold); opacity: 0.85; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .log-msg { color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .log-row.selected .log-msg { color: var(--paper); }

    .badge {
      display: inline-flex;
      align-items: center;
      font-family: var(--sans);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      padding: 2px 7px;
      border-radius: 2px;
      width: fit-content;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.04);
      white-space: nowrap;
    }

    .badge.gold { color: var(--gold); background: rgba(232, 185, 79, 0.14); }
    .badge.jade { color: var(--jade); background: rgba(127, 160, 140, 0.14); }
    .badge.amber { color: var(--amber); background: rgba(193, 127, 58, 0.14); }
    .badge.crimson { color: var(--crimson); background: rgba(181, 97, 89, 0.14); }

    .empty { padding: 28px; text-align: center; color: var(--muted); font-size: 13px; }

    /* ── Inspector ──────────────────────────────────────── */

    .inspector {
      border-left: 1px solid var(--line);
      background: var(--panel);
      padding: 22px;
      overflow-y: auto;
    }

    .inspector h4 {
      font-family: var(--serif);
      font-style: italic;
      font-weight: 500;
      font-size: 13px;
      color: var(--faint);
      margin-bottom: 14px;
    }

    .insp-field { margin-bottom: 14px; }

    .insp-label {
      font-size: 11px;
      color: var(--faint);
      margin-bottom: 3px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .insp-value {
      font-family: var(--mono);
      font-size: 12.5px;
      color: var(--paper);
      line-height: 1.55;
      word-break: break-word;
    }

    .pill-row { display: flex; flex-wrap: wrap; gap: 6px; }

    .pill {
      font-family: var(--mono);
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 2px;
      background: rgba(255, 255, 255, 0.04);
      color: var(--muted);
    }

    .payload {
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 14px;
      font-family: var(--mono);
      font-size: 11.5px;
      line-height: 1.65;
      color: var(--muted);
      white-space: pre-wrap;
      word-break: break-word;
      overflow-x: auto;
    }

    ::-webkit-scrollbar { width: 9px; height: 9px; }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.18); }

    @media (max-width: 1100px) {
      .bodygrid { grid-template-columns: 220px minmax(0, 1fr); }
      .inspector { display: none; }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="topbar">
      <div class="brand"><span class="brand-mark"></span>Infinite DnD · Session Logs</div>
      <div class="search">🔍 <input id="search" placeholder="Search events, tools, dialogue..."></div>
      <select id="turn-filter" class="turn-select"></select>
      <div class="session-meta">
        <div class="title" id="session-title">Waiting for logs</div>
        <div id="session-sub"></div>
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
      game_session_started: "gold",
      game_session_finished: "gold",
      pc_death: "crimson",
      turn_started: "jade",
      resolved: "jade",
      agent_run_started: "amber",
      agent_run_finished: "amber",
      llm_message: "crimson",
      parse_error: "crimson",
    };

    const state = {
      files: [],
      session: null,
      search: "",
      eventFilter: null,
      labelFilter: null,
      turnFilter: "all",
      selectedLine: null,
    };

    const dom = {
      fileList: document.getElementById("file-list"),
      eventList: document.getElementById("event-list"),
      labelList: document.getElementById("label-list"),
      logPanel: document.getElementById("log-panel"),
      inspector: document.getElementById("inspector"),
      search: document.getElementById("search"),
      turnFilter: document.getElementById("turn-filter"),
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

    function eventColor(event) {
      return EVENT_COLOR[event] || "";
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
      state.turnFilter = "all";
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
            <span class="sub">${escapeHtml(sub)}</span>
            <span class="sub">${escapeHtml(formatDateTime(file.modified_time))}</span>
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
        `${session.stats.event_count} events · ${session.stats.run_count} runs · ${formatDuration(summary.duration_s)}`;

      dom.turnFilter.innerHTML = ["all", ...session.turns]
        .map((value) => `<option value="${escapeHtml(value)}">${value === "all" ? "All turns" : `Turn ${escapeHtml(value)}`}</option>`)
        .join("");
      dom.turnFilter.value = state.turnFilter;
    }

    function renderRailFilters() {
      const session = state.session;
      if (!session) return;

      dom.eventList.innerHTML = session.event_types.map((event) => `
        <button class="filter-row ${state.eventFilter === event ? "active" : ""}" data-event="${escapeHtml(event)}">
          <span class="dot ${eventColor(event)}"></span>${escapeHtml(event)}
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
              <span class="dot gold"></span>${escapeHtml(label)}
              <span class="count">${escapeHtml(labelCounts[label] || 0)}</span>
            </button>
          `).join("")
        : '<div class="empty">No agent runs recorded.</div>';
    }

    function filteredEntries() {
      if (!state.session) return [];
      const search = state.search.trim().toLowerCase();
      return state.session.entries.filter((entry) => {
        if (state.eventFilter && entry.event !== state.eventFilter) return false;
        if (state.labelFilter && entry.label !== state.labelFilter) return false;
        if (state.turnFilter !== "all" && String(entry.turn ?? "") !== state.turnFilter) return false;
        if (!search) return true;
        const haystack = [entry.summary, entry.excerpt, entry.label, entry.event, entry.raw_pretty]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(search);
      });
    }

    function renderRows() {
      const entries = filteredEntries();
      if (!entries.length) {
        dom.logPanel.innerHTML = '<div class="empty">No events match the current filters.</div>';
        return;
      }
      dom.logPanel.innerHTML = entries.map((entry) => `
        <div class="log-row ${state.selectedLine === entry.line ? "selected" : ""}" data-line="${entry.line}">
          <span class="log-time">${escapeHtml(entry.display_time)}</span>
          <span class="badge ${eventColor(entry.event)}">${escapeHtml(entry.message_kind || entry.event)}</span>
          <span class="log-turn">${entry.turn !== null && entry.turn !== undefined ? "T" + escapeHtml(entry.turn) : ""}</span>
          <span class="log-label">${escapeHtml(entry.label || "")}</span>
          <span class="log-msg">${escapeHtml(entry.summary)}</span>
        </div>
      `).join("");
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
        ? Object.entries(entry.usage).map(([key, value]) => `${key.replace("_tokens", "")} ${value}`).join(" · ")
        : null;

      dom.inspector.innerHTML = `
        <h4>Event Detail</h4>
        <div class="insp-field"><div class="insp-label">Summary</div><div class="insp-value">${escapeHtml(entry.summary)}</div></div>
        <div class="insp-field"><div class="insp-label">Event</div><div class="insp-value">${escapeHtml(entry.message_kind || entry.event)}</div></div>
        ${entry.label ? `<div class="insp-field"><div class="insp-label">Agent</div><div class="insp-value">${escapeHtml(entry.label)}</div></div>` : ""}
        <div class="insp-field"><div class="insp-label">Time</div><div class="insp-value">${escapeHtml(entry.display_time)} · turn ${escapeHtml(entry.turn ?? "-")} · line ${escapeHtml(entry.line)}</div></div>
        ${tools.length ? `<div class="insp-field"><div class="insp-label">Tools</div><div class="pill-row">${tools.map((tool) => `<span class="pill">${escapeHtml(tool)}</span>`).join("")}</div></div>` : ""}
        ${usage ? `<div class="insp-field"><div class="insp-label">Tokens</div><div class="insp-value">${escapeHtml(usage)}</div></div>` : ""}
        <div class="insp-field"><div class="insp-label">Payload</div><div class="payload">${escapeHtml(entry.raw_pretty || JSON.stringify(entry.raw, null, 2))}</div></div>
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
        <div class="insp-field"><div class="insp-label">Character</div><div class="insp-value">${escapeHtml(summary.character_id || "unknown")}</div></div>
        <div class="insp-field"><div class="insp-label">Started</div><div class="insp-value">${escapeHtml(formatDateTime(summary.started_at))}</div></div>
        <div class="insp-field"><div class="insp-label">Duration</div><div class="insp-value">${escapeHtml(formatDuration(summary.duration_s))} · ${escapeHtml(summary.turns_completed ?? 0)}/${escapeHtml(summary.max_turns ?? "?")} turns</div></div>
        <div class="insp-field"><div class="insp-label">Traffic</div><div class="insp-value">${escapeHtml(session.stats.run_count)} agent runs · ${escapeHtml(session.stats.llm_message_count)} LLM messages</div></div>
        <div class="insp-field"><div class="insp-label">Tokens</div><div class="insp-value">${escapeHtml(tokens.input_tokens.toLocaleString())} in · ${escapeHtml(tokens.output_tokens.toLocaleString())} out</div></div>
        ${session.stats.error_count ? `<div class="insp-field"><div class="insp-label">Parse errors</div><div class="insp-value">${escapeHtml(session.stats.error_count)}</div></div>` : ""}
        <div class="insp-field"><div class="insp-label">File</div><div class="insp-value">${escapeHtml(session.path)}</div></div>
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

    dom.turnFilter.addEventListener("change", (event) => {
      state.turnFilter = event.target.value;
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
