"""Local read-only web viewer for TCW content."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import unquote, urlparse

from tcw.store.base import WORK_ARTIFACTS
from tcw.store.fs import (
    FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore, find_node_root,
)

DEFAULT_PORT = 8765
HOST = "127.0.0.1"

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


def _jsonable(value):
    if is_dataclass(value):
        data = asdict(value)
        for attr in ("ref", "status", "qualified"):
            if attr not in data and hasattr(value, attr):
                data[attr] = getattr(value, attr)
        return data
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def _json_bytes(value) -> bytes:
    return json.dumps(_jsonable(value), default=str).encode("utf-8")


def _static_bytes(name: str) -> tuple[bytes, str]:
    static = files("tcw.serve").joinpath("static")
    target = static.joinpath(name)
    data = target.read_bytes()
    ctype = STATIC_TYPES.get(Path(name).suffix, "application/octet-stream")
    return data, ctype


def _open_locator(locator: str) -> dict | None:
    if locator.startswith(("http://", "https://")):
        return {"url": locator}
    if os.name == "nt":
        os.startfile(locator)  # type: ignore[attr-defined]
        return None
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, locator])
    return None


class TcwServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], node_root: Path):
        super().__init__(server_address, TcwHandler)
        self.node_root = node_root


class TcwHandler(BaseHTTPRequestHandler):
    server: TcwServer

    def log_message(self, fmt: str, *args) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", "default-src 'self'")
        super().end_headers()

    def _send(self, status: int, body: bytes = b"", ctype: str = "text/plain; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_json(self, status: int, value) -> None:
        self._send(status, _json_bytes(value), "application/json; charset=utf-8")

    def _stores(self) -> tuple[FsWorkStore, FsTaxonomyStore, FsCapabilitiesStore]:
        root = self.server.node_root
        return (
            FsWorkStore.open(root),
            FsTaxonomyStore.open(root),
            FsCapabilitiesStore.open(root),
        )

    def do_GET(self) -> None:
        try:
            self._get()
        except Exception as e:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, str(e).encode("utf-8"))

    def do_POST(self) -> None:
        try:
            self._post()
        except Exception as e:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, str(e).encode("utf-8"))

    def _get(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body, ctype = _static_bytes("index.html")
            self._send(HTTPStatus.OK, body, ctype)
            return
        if path in ("/app.js", "/style.css", "/marked.min.js"):
            body, ctype = _static_bytes(path.lstrip("/"))
            self._send(HTTPStatus.OK, body, ctype)
            return

        work, taxonomy, capabilities = self._stores()
        if path == "/api/work":
            self._send_json(HTTPStatus.OK, work.board())
            return
        if path.startswith("/api/work/"):
            slug = unquote(path.removeprefix("/api/work/")).strip("/")
            item = work.get(slug)
            if item is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            self._send_json(HTTPStatus.OK, {
                "item": item,
                "artifacts": work.artifacts(slug),
            })
            return
        if path == "/api/taxonomy":
            self._send_json(HTTPStatus.OK, taxonomy.list())
            return
        if path == "/api/capabilities":
            self._send_json(HTTPStatus.OK, capabilities.list())
            return
        self._send(HTTPStatus.NOT_FOUND, b"not found")

    def _post(self) -> None:
        path = urlparse(self.path).path
        prefix = "/api/work/"
        suffix = "/open"
        marker = "/artifacts/"
        if not (path.startswith(prefix) and path.endswith(suffix) and marker in path):
            self._send(HTTPStatus.NOT_FOUND, b"not found")
            return
        middle = path[len(prefix):-len(suffix)]
        slug, _, name = middle.partition(marker)
        slug, name = unquote(slug), unquote(name)
        if name not in WORK_ARTIFACTS:
            self._send(HTTPStatus.BAD_REQUEST, b"unknown artifact")
            return

        work = FsWorkStore.open(self.server.node_root)
        item = work.get(slug)
        if item is None:
            self._send(HTTPStatus.NOT_FOUND, b"no such work item")
            return
        present = {a.name for a in work.artifacts(slug) if a.present}
        if name not in present:
            self._send(HTTPStatus.NOT_FOUND, b"artifact is not present")
            return
        locator = work.artifact_locator(slug, name)
        if locator is None:
            self._send(HTTPStatus.NOT_FOUND, b"artifact is not available")
            return
        opened = _open_locator(locator)
        if opened:
            self._send_json(HTTPStatus.OK, opened)
            return
        self._send(HTTPStatus.NO_CONTENT)


def serve(port: int = DEFAULT_PORT, open_browser: bool = True,
          node_root: Path | None = None) -> int:
    root = node_root or find_node_root()
    if root is None:
        print("tcw serve: no tcw node here — run `tcw init` in the project folder.",
              file=sys.stderr)
        return 1
    try:
        httpd = TcwServer((HOST, port), root)
    except OSError as e:
        print(f"tcw serve: cannot bind {HOST}:{port}: {e}", file=sys.stderr)
        return 1
    url = f"http://{HOST}:{httpd.server_port}/"
    print(f"Serving TCW at {url}")
    if open_browser:
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\ntcw serve: stopped", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0
