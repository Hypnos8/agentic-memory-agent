"""Local, read-only viewer for trajectory JSONL files."""

import argparse
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from telemetry.logger import DEFAULT_LOG_PATH


STATIC_DIR = Path(__file__).with_name("static")
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def read_runs(path: Path) -> dict:
    runs, invalid_lines = [], []
    try:
        with path.open("rb") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line.decode("utf-8"))
                    if not isinstance(record, dict):
                        raise ValueError("Expected an object")
                    # Reject non-standard NaN/Infinity, including nested values.
                    json.dumps(record, allow_nan=False)
                except (UnicodeError, ValueError):
                    invalid_lines.append(number)
                    continue
                runs.append({"line": number, "record": record})
    except FileNotFoundError:
        pass
    return {"runs": list(reversed(runs)), "invalid_lines": invalid_lines}


class ViewerHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, log_path: Path, **kwargs):
        self.log_path = log_path
        super().__init__(*args, **kwargs)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/api/runs":
            try:
                body = json.dumps(read_runs(self.log_path), ensure_ascii=False, allow_nan=False).encode("utf-8")
            except (OSError, UnicodeError):
                self.respond(500, b'{"error":"Logdatei konnte nicht gelesen werden."}',
                             "application/json; charset=utf-8")
                return
            self.respond(200, body, "application/json; charset=utf-8")
        elif route in ASSETS:
            filename, content_type = ASSETS[route]
            self.respond(200, (STATIC_DIR / filename).read_bytes(), content_type)
        else:
            self.respond(404, b"Not found", "text/plain; charset=utf-8")

    def respond(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Do not echo log content or query strings to the terminal.
        pass


def create_server(log_path: Path = DEFAULT_LOG_PATH, port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), partial(ViewerHandler, log_path=Path(log_path)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    args = parser.parse_args()
    try:
        server = create_server(args.log_path, args.port)
    except (OSError, OverflowError) as exc:
        parser.exit(1, f"Server konnte nicht gestartet werden: {exc}\n")
    with server:
        print(f"Log-Viewer: http://127.0.0.1:{server.server_port} (Strg+C zum Beenden)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
