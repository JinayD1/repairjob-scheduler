"""
The HTTP layer, shared by the local dev server and the Vercel functions.

Vercel's Python runtime expects each file in api/ to export a class named
`handler` that subclasses BaseHTTPRequestHandler. The local dev server
(dev_server.py) uses the same class. Both therefore run exactly the same code
for the three routes:

    GET  /api/config       map, technicians, presets, limits
    POST /api/dispatch     {"pins": [{"x","y","appliance"}], "w_distance": 0.6}
    POST /api/explore      {"tech_index": 0, "x": 33, "y": 22}

All algorithm work happens in the rest of the dispatch package; this file
only parses requests and serialises responses.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler

from .api import config_payload, dispatch_payload, explore_payload

MAX_BODY_BYTES = 64 * 1024


class DispatchHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _route(self) -> str:
        return self.path.split("?", 1)[0].rstrip("/")

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if self._route() == "/api/config":
            self._send_json(200, config_payload())
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        route = self._route()
        body = self._read_json()
        if not isinstance(body, dict):
            self._send_json(400, {"error": "expected a JSON object body"})
            return
        try:
            if route == "/api/dispatch":
                self._send_json(200, dispatch_payload(body.get("pins", []), body.get("w_distance", 0.6)))
            elif route == "/api/explore":
                self._send_json(200, explore_payload(body.get("tech_index", 0), body.get("x", 0), body.get("y", 0)))
            else:
                self._send_json(404, {"error": "not found"})
        except (TypeError, ValueError) as exc:
            self._send_json(400, {"error": str(exc)})

    def log_message(self, fmt, *args) -> None:
        sys.stderr.write("%s %s\n" % (self.command, self.path))
