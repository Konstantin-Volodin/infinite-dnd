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

from src.interface.assets import read_asset, static_asset
from src.interface.session_log import DEFAULT_LOG_DIR, list_logs, load_session

_HTML = read_asset("templates/logs.html")


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
            if parsed.path.startswith("/static/"):
                self._send_static(parsed.path.removeprefix("/static/"))
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

        def _send_static(self, name: str) -> None:
            asset = static_asset(name)
            if asset is None:
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return
            body, content_type = asset
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
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
