"""Small localhost-only API for the TCP scanner."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from scanner import DEFAULT_TIMEOUT, parse_ports, scan, validate_target
from storage import get_scan, json_bytes, list_scans, save_report

DEFAULT_DATABASE = "scanner.db"
BASE_DIR = Path(__file__).parent
STATIC_FILES = {
    "/": ("dashboard.html", "text/html; charset=utf-8"),
    "/dashboard.css": ("dashboard.css", "text/css; charset=utf-8"),
    "/dashboard.js": ("dashboard.js", "text/javascript; charset=utf-8"),
}


class ApiHandler(BaseHTTPRequestHandler):
    database = DEFAULT_DATABASE

    def _send(self, status: int, payload: object) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, filename: str, content_type: str) -> None:
        body = (BASE_DIR / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in STATIC_FILES:
            filename, content_type = STATIC_FILES[path]
            self._send_static(filename, content_type)
            return
        if path == "/health":
            self._send(200, {"status": "ok"})
            return
        if path == "/scans":
            self._send(200, {"scans": list_scans(self.database)})
            return
        if path.startswith("/scans/"):
            try:
                scan_id = int(path.rsplit("/", 1)[1])
            except ValueError:
                self._send(400, {"error": "invalid scan id"})
                return
            report = get_scan(self.database, scan_id)
            self._send(200, report) if report else self._send(404, {"error": "scan not found"})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/scans":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                raise ValueError("request body too large")
            payload = json.loads(self.rfile.read(length) or b"{}")
            target = validate_target(str(payload["target"]))
            ports = parse_ports(str(payload.get("ports", "22,80,443")))
            timeout = float(payload.get("timeout", DEFAULT_TIMEOUT))
            if timeout <= 0 or timeout > 10:
                raise ValueError("timeout must be between 0 and 10 seconds")
            report = scan(target, ports, timeout)
            scan_id = save_report(self.database, report)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
            return
        self._send(201, {"id": scan_id, "report": report})

    def log_message(self, format: str, *args: object) -> None:
        return


def run(host: str, port: int, database: str) -> None:
    ApiHandler.database = database
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"API disponible sur http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local scanner API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("API must remain bound to localhost")
    run(args.host, args.port, args.database)


if __name__ == "__main__":
    main()
