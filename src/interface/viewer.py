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

from src.interface.log_reader import list_logs, load_session
from src.interface.logger import DEFAULT_LOG_DIR

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Infinite DnD Log Viewer</title>
  <style>
    :root {
      --bg: #120f0b;
      --panel: rgba(32, 24, 17, 0.82);
      --panel-strong: rgba(48, 36, 24, 0.94);
      --paper: #f4ead8;
      --ink: #201710;
      --muted: #cfbea7;
      --gold: #d6a95f;
      --gold-soft: rgba(214, 169, 95, 0.18);
      --jade: #6f9a8d;
      --crimson: #a34b3f;
      --line: rgba(255, 232, 199, 0.12);
      --shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
      --radius: 20px;
      --mono: "Cascadia Code", "Consolas", monospace;
      --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      --sans: "Segoe UI Variable", "Trebuchet MS", sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--paper);
      font-family: var(--sans);
      background:
        radial-gradient(circle at top left, rgba(111, 154, 141, 0.18), transparent 32%),
        radial-gradient(circle at top right, rgba(163, 75, 63, 0.2), transparent 28%),
        linear-gradient(160deg, #1b1510 0%, #0f0c09 55%, #140f0d 100%);
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
      background-size: 22px 22px;
      mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.35), transparent 78%);
    }

    .shell {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      min-height: 100vh;
    }

    .sidebar {
      padding: 28px;
      border-right: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(30, 23, 17, 0.94), rgba(19, 15, 11, 0.92));
      backdrop-filter: blur(18px);
    }

    .brand {
      margin-bottom: 28px;
    }

    .eyebrow {
      margin: 0 0 8px;
      font-size: 0.72rem;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--gold);
    }

    h1, h2, h3 {
      margin: 0;
      font-family: var(--serif);
      font-weight: 600;
      letter-spacing: 0.01em;
    }

    .brand p,
    .sidebar-copy,
    .meta-row,
    .small {
      color: var(--muted);
    }

    .file-list {
      display: grid;
      gap: 10px;
    }

    .file-button {
      width: 100%;
      padding: 14px 16px;
      border: 1px solid transparent;
      border-radius: 16px;
      color: inherit;
      background: rgba(255, 245, 230, 0.04);
      text-align: left;
      cursor: pointer;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }

    .file-button:hover,
    .file-button:focus-visible {
      transform: translateY(-1px);
      border-color: rgba(214, 169, 95, 0.38);
      background: rgba(214, 169, 95, 0.08);
      outline: none;
    }

    .file-button.active {
      border-color: rgba(214, 169, 95, 0.52);
      background: linear-gradient(180deg, rgba(214, 169, 95, 0.14), rgba(214, 169, 95, 0.08));
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03);
    }

    .file-name {
      display: block;
      margin-bottom: 4px;
      font-weight: 600;
    }

    .file-meta {
      font-size: 0.84rem;
      color: var(--muted);
    }

    .main {
      padding: 28px;
    }

    .hero,
    .panel,
    .stat,
    .event-card,
    .run-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }

    .hero {
      display: grid;
      gap: 20px;
      padding: 24px;
      margin-bottom: 20px;
      background:
        linear-gradient(135deg, rgba(214, 169, 95, 0.12), transparent 46%),
        linear-gradient(180deg, rgba(48, 36, 24, 0.98), rgba(27, 21, 15, 0.94));
    }

    .hero-title {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: end;
      flex-wrap: wrap;
    }

    .hero-copy p {
      margin: 10px 0 0;
      color: var(--muted);
      max-width: 65ch;
    }

    .controls {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }

    .field {
      display: grid;
      gap: 6px;
      font-size: 0.84rem;
      color: var(--muted);
    }

    .field input,
    .field select {
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.08);
      color: var(--paper);
      background: rgba(12, 10, 8, 0.78);
      font: inherit;
    }

    .field input:focus,
    .field select:focus {
      outline: 2px solid rgba(214, 169, 95, 0.35);
      border-color: rgba(214, 169, 95, 0.45);
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }

    .stat {
      padding: 18px;
      background: linear-gradient(180deg, rgba(40, 31, 22, 0.92), rgba(26, 20, 15, 0.9));
    }

    .stat-label {
      display: block;
      font-size: 0.76rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }

    .stat-value {
      font-family: var(--serif);
      font-size: 1.8rem;
    }

    .run-strip {
      margin-bottom: 20px;
      padding: 18px;
    }

    .run-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }

    .run-card {
      padding: 16px;
      background: rgba(255, 245, 230, 0.04);
      cursor: pointer;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }

    .run-card:hover,
    .run-card:focus-visible {
      transform: translateY(-1px);
      border-color: rgba(111, 154, 141, 0.45);
      background: rgba(111, 154, 141, 0.08);
      outline: none;
    }

    .run-card.active {
      border-color: rgba(111, 154, 141, 0.55);
      background: linear-gradient(180deg, rgba(111, 154, 141, 0.16), rgba(111, 154, 141, 0.08));
    }

    .run-title {
      font-weight: 700;
      margin-bottom: 10px;
      word-break: break-word;
    }

    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }

    .pill,
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 0.76rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: rgba(255, 245, 230, 0.08);
      color: var(--paper);
    }

    .badge.event-game_session_started,
    .badge.event-game_session_finished {
      background: rgba(214, 169, 95, 0.16);
      color: #f7d9a2;
    }

    .badge.event-turn_started {
      background: rgba(111, 154, 141, 0.18);
      color: #bddad2;
    }

    .badge.event-agent_run_started,
    .badge.event-agent_run_finished {
      background: rgba(93, 111, 178, 0.18);
      color: #cad4ff;
    }

    .badge.event-llm_message {
      background: rgba(163, 75, 63, 0.18);
      color: #f2c0b8;
    }

    .timeline {
      display: grid;
      gap: 14px;
    }

    .event-card {
      padding: 18px 18px 14px;
      background: linear-gradient(180deg, rgba(33, 25, 18, 0.96), rgba(20, 16, 12, 0.92));
    }

    .event-top {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: start;
      margin-bottom: 12px;
    }

    .event-main {
      display: grid;
      gap: 10px;
    }

    .event-summary {
      font-size: 1rem;
      line-height: 1.5;
    }

    .meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 0.88rem;
    }

    details {
      margin-top: 12px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }

    summary {
      cursor: pointer;
      color: var(--gold);
    }

    pre {
      margin: 12px 0 0;
      padding: 14px;
      border-radius: 16px;
      background: rgba(8, 8, 8, 0.6);
      border: 1px solid rgba(255,255,255,0.06);
      color: #f1e6d7;
      overflow-x: auto;
      font-family: var(--mono);
      font-size: 0.85rem;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
      border: 1px dashed rgba(255,255,255,0.14);
      border-radius: var(--radius);
      background: rgba(255,255,255,0.03);
    }

    @media (max-width: 1100px) {
      .shell {
        grid-template-columns: 1fr;
      }

      .sidebar {
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }

      .controls,
      .stats {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 720px) {
      .main,
      .sidebar {
        padding: 18px;
      }

      .controls,
      .stats {
        grid-template-columns: 1fr;
      }

      .hero-title,
      .event-top {
        flex-direction: column;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <p class="eyebrow">Infinite DnD</p>
        <h1>Log Viewer</h1>
        <p class="sidebar-copy">Inspect turns, agent runs, and raw LLM traffic from any recorded session.</p>
      </div>
      <div id="file-list" class="file-list"></div>
    </aside>
    <main class="main">
      <section class="hero">
        <div class="hero-title">
          <div class="hero-copy">
            <p class="eyebrow">Session Ledger</p>
            <h2 id="session-title">Waiting for logs</h2>
            <p id="session-meta">Select a log file to inspect the timeline.</p>
          </div>
          <div class="small" id="session-path"></div>
        </div>
        <div class="controls">
          <label class="field">
            Search
            <input id="search" type="search" placeholder="Filter by text, tool, or label">
          </label>
          <label class="field">
            Event
            <select id="event-filter"></select>
          </label>
          <label class="field">
            Turn
            <select id="turn-filter"></select>
          </label>
          <label class="field">
            Run
            <select id="run-filter"></select>
          </label>
        </div>
      </section>

      <section id="stats" class="stats"></section>

      <section class="panel run-strip">
        <div class="hero-title">
          <div>
            <p class="eyebrow">Agent Runs</p>
            <h3>Conversation Slices</h3>
          </div>
          <div class="small">Click a run to isolate its traffic.</div>
        </div>
        <div id="runs" class="run-grid"></div>
      </section>

      <section id="timeline" class="timeline"></section>
    </main>
  </div>

  <script>
    const state = {
      files: [],
      session: null,
      search: "",
      eventFilter: "all",
      turnFilter: "all",
      runFilter: "all"
    };

    const dom = {
      fileList: document.getElementById("file-list"),
      sessionTitle: document.getElementById("session-title"),
      sessionMeta: document.getElementById("session-meta"),
      sessionPath: document.getElementById("session-path"),
      search: document.getElementById("search"),
      eventFilter: document.getElementById("event-filter"),
      turnFilter: document.getElementById("turn-filter"),
      runFilter: document.getElementById("run-filter"),
      stats: document.getElementById("stats"),
      runs: document.getElementById("runs"),
      timeline: document.getElementById("timeline")
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
      if (!value) {
        return "unknown";
      }
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
    }

    function formatDuration(value) {
      if (value === null || value === undefined) {
        return "--";
      }
      return `${Number(value).toFixed(3)}s`;
    }

    async function fetchJson(path) {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      return response.json();
    }

    async function loadFiles() {
      state.files = await fetchJson("/api/files");
      renderFiles();
      if (!state.files.length) {
        dom.timeline.innerHTML = '<div class="empty">No log files were found in the selected directory.</div>';
        return;
      }
      await loadSession(state.files[0].name);
    }

    async function loadSession(name) {
      state.session = await fetchJson(`/api/logs/${encodeURIComponent(name)}`);
      state.eventFilter = "all";
      state.turnFilter = "all";
      state.runFilter = "all";
      renderFiles();
      renderFilters();
      renderSummary();
      renderRuns();
      renderTimeline();
    }

    function renderFiles() {
      if (!state.files.length) {
        dom.fileList.innerHTML = '<div class="empty">No logs found.</div>';
        return;
      }

      dom.fileList.innerHTML = state.files.map((file) => {
        const active = state.session && state.session.file === file.name;
        return `
          <button class="file-button ${active ? "active" : ""}" data-file="${escapeHtml(file.name)}">
            <span class="file-name">${escapeHtml(file.name)}</span>
            <span class="file-meta">${formatDateTime(file.modified_time)} · ${(file.size_bytes / 1024).toFixed(1)} KB</span>
          </button>
        `;
      }).join("");

      dom.fileList.querySelectorAll(".file-button").forEach((button) => {
        button.addEventListener("click", () => loadSession(button.dataset.file));
      });
    }

    function renderFilters() {
      if (!state.session) {
        return;
      }

      dom.eventFilter.innerHTML = ["all", ...state.session.event_types]
        .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value === "all" ? "All events" : value)}</option>`)
        .join("");

      dom.turnFilter.innerHTML = ["all", ...state.session.turns]
        .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value === "all" ? "All turns" : `Turn ${value}`)}</option>`)
        .join("");

      const runLabels = state.session.runs.map((run) => run.label);
      dom.runFilter.innerHTML = ["all", ...runLabels]
        .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value === "all" ? "All runs" : value)}</option>`)
        .join("");

      dom.eventFilter.value = state.eventFilter;
      dom.turnFilter.value = state.turnFilter;
      dom.runFilter.value = state.runFilter;
    }

    function renderSummary() {
      const session = state.session;
      const summary = session.summary;
      const stats = session.stats;
      dom.sessionTitle.textContent = summary.character_id ? `${summary.character_id} · ${session.file}` : session.file;
      dom.sessionMeta.textContent = `${formatDateTime(summary.started_at)} to ${formatDateTime(summary.finished_at)} · ${summary.turns_completed} turns completed`;
      dom.sessionPath.textContent = session.path;

      const cards = [
        { label: "Turns", value: summary.turns_completed ?? 0, note: `Budget ${summary.max_turns ?? "--"}` },
        { label: "Agent Runs", value: stats.run_count, note: `${stats.llm_message_count} LLM messages` },
        { label: "Timeline", value: stats.event_count, note: `${session.event_types.length} event types` },
        { label: "Duration", value: formatDuration(summary.duration_s), note: `${stats.error_count} parse errors` }
      ];

      dom.stats.innerHTML = cards.map((card) => `
        <article class="stat">
          <span class="stat-label">${escapeHtml(card.label)}</span>
          <div class="stat-value">${escapeHtml(card.value)}</div>
          <div class="small">${escapeHtml(card.note)}</div>
        </article>
      `).join("");
    }

    function renderRuns() {
      if (!state.session.runs.length) {
        dom.runs.innerHTML = '<div class="empty">No agent run spans were found in this log.</div>';
        return;
      }

      dom.runs.innerHTML = state.session.runs.map((run) => {
        const active = state.runFilter === run.label;
        const tools = run.tool_calls.length ? run.tool_calls.map((tool) => `<span class="pill">${escapeHtml(tool)}</span>`).join("") : '<span class="pill">No tools</span>';
        return `
          <button class="run-card ${active ? "active" : ""}" data-run="${escapeHtml(run.label)}">
            <div class="run-title">${escapeHtml(run.label)}</div>
            <div class="meta-row">
              <span>Turn ${escapeHtml(run.turn ?? "-")}</span>
              <span>${escapeHtml(formatDuration(run.elapsed_s))}</span>
              <span>${escapeHtml(run.message_count)} messages</span>
            </div>
            <div class="pill-row">${tools}</div>
          </button>
        `;
      }).join("");

      dom.runs.querySelectorAll(".run-card").forEach((button) => {
        button.addEventListener("click", () => {
          state.runFilter = state.runFilter === button.dataset.run ? "all" : button.dataset.run;
          dom.runFilter.value = state.runFilter;
          renderRuns();
          renderTimeline();
        });
      });
    }

    function filteredEntries() {
      if (!state.session) {
        return [];
      }

      const search = state.search.trim().toLowerCase();
      return state.session.entries.filter((entry) => {
        if (state.eventFilter !== "all" && entry.event !== state.eventFilter) {
          return false;
        }
        if (state.turnFilter !== "all" && String(entry.turn ?? "") !== state.turnFilter) {
          return false;
        }
        if (state.runFilter !== "all" && entry.label !== state.runFilter) {
          return false;
        }
        if (!search) {
          return true;
        }
        const haystack = [entry.summary, entry.excerpt, entry.label, entry.event, entry.raw_pretty, JSON.stringify(entry.raw)]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(search);
      });
    }

    function renderTimeline() {
      const entries = filteredEntries();
      if (!entries.length) {
        dom.timeline.innerHTML = '<div class="empty">No events match the current filters.</div>';
        return;
      }

      dom.timeline.innerHTML = entries.map((entry) => {
        const turnPill = entry.turn !== null && entry.turn !== undefined ? `<span class="pill">Turn ${escapeHtml(entry.turn)}</span>` : "";
        const runPill = entry.label ? `<span class="pill">${escapeHtml(entry.label)}</span>` : "";
        const toolPills = [...(entry.tool_calls || []), ...(entry.tool_returns || [])]
          .map((tool) => `<span class="pill">${escapeHtml(tool)}</span>`)
          .join("");
        const raw = escapeHtml(entry.raw_pretty || JSON.stringify(entry.raw, null, 2));

        return `
          <article class="event-card">
            <div class="event-top">
              <div class="pill-row">
                <span class="badge event-${escapeHtml(entry.event)}">${escapeHtml(entry.event)}</span>
                ${turnPill}
                ${runPill}
                ${toolPills}
              </div>
              <div class="small">${escapeHtml(entry.display_time)} · line ${escapeHtml(entry.line)}</div>
            </div>
            <div class="event-main">
              <div class="event-summary">${escapeHtml(entry.summary)}</div>
              ${entry.excerpt ? `<div class="small">${escapeHtml(entry.excerpt)}</div>` : ""}
            </div>
            <details>
              <summary>Raw event payload</summary>
              <pre>${raw}</pre>
            </details>
          </article>
        `;
      }).join("");
    }

    dom.search.addEventListener("input", (event) => {
      state.search = event.target.value;
      renderTimeline();
    });

    dom.eventFilter.addEventListener("change", (event) => {
      state.eventFilter = event.target.value;
      renderTimeline();
    });

    dom.turnFilter.addEventListener("change", (event) => {
      state.turnFilter = event.target.value;
      renderTimeline();
    });

    dom.runFilter.addEventListener("change", (event) => {
      state.runFilter = event.target.value;
      renderRuns();
      renderTimeline();
    });

    loadFiles().catch((error) => {
      dom.timeline.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
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