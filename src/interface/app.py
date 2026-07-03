"""Unified infinite-dnd browser app: World and Logs as tabs under one shell."""

from __future__ import annotations

import argparse
import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from src.interface.dashboard import _HTML as WORLD_HTML
from src.interface.session_log import DEFAULT_LOG_DIR, list_logs, load_session
from src.interface.viewer import _HTML as LOGS_HTML, _pick_port
from src.interface.world_state import DEFAULT_STATE_DIR, list_state_scenarios, load_series, load_view


def _with_nav(html: str, active: str) -> str:
    tabs = (
        '<div class="tabs">'
        f'<a href="/" class="{"active" if active == "world" else ""}">World</a>'
        f'<a href="/logs" class="{"active" if active == "logs" else ""}">Logs</a>'
        "</div>"
    )
    return html.replace('<div class="topbar-main">', f'<div class="topbar-main">{tabs}', 1)


def _build_handler(
    state_dir: Path = DEFAULT_STATE_DIR,
    log_dir: Path = DEFAULT_LOG_DIR,
) -> type[BaseHTTPRequestHandler]:
    class StudioHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(_with_nav(WORLD_HTML, "world"))
            elif parsed.path == "/logs":
                self._send_html(_with_nav(LOGS_HTML, "logs"))
            elif parsed.path == "/api/scenarios":
                self._send_json(list_state_scenarios(state_dir))
            elif parsed.path == "/api/files":
                self._send_json(list_logs(log_dir))
            elif parsed.path.startswith("/api/state/"):
                scenario = unquote(parsed.path.removeprefix("/api/state/"))
                tick_values = parse_qs(parsed.query).get("tick")
                try:
                    tick = int(tick_values[0]) if tick_values else None
                    self._require_scenario(scenario)
                    self._send_json(load_view(state_dir, scenario, tick))
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                except FileNotFoundError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            elif parsed.path.startswith("/api/series/"):
                scenario = unquote(parsed.path.removeprefix("/api/series/"))
                try:
                    self._require_scenario(scenario)
                    self._send_json(load_series(state_dir, scenario))
                except FileNotFoundError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            elif parsed.path.startswith("/api/logs/"):
                name = unquote(parsed.path.removeprefix("/api/logs/"))
                path = next((Path(item["path"]) for item in list_logs(log_dir) if item["name"] == name), None)
                if path:
                    self._send_json(load_session(path))
                else:
                    self._send_json({"error": f"Log not found: {name}"}, HTTPStatus.NOT_FOUND)
            else:
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

        def _require_scenario(self, scenario: object) -> None:
            if not isinstance(scenario, str) or not any(
                meta["scenario"] == scenario for meta in list_state_scenarios(state_dir)
            ):
                raise FileNotFoundError(f"Scenario not found: {scenario}")

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
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

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return StudioHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch the infinite-dnd app (World + Logs tabs).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer(
        (args.host, _pick_port(args.host, args.port)),
        _build_handler(args.state_dir, args.log_dir),
    )
    url = f"http://{args.host}:{server.server_port}"
    print(f"Serving infinite-dnd at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping infinite-dnd.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
