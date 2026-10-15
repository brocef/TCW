"""The web viewer's one process: a JSON API and the prebuilt client, served
from Python on the loopback address.

Every request passes the same checks before it is routed: its `Host` must
name a loopback address and its `Origin`, when sent, too; a write must be
JSON and at most 1 MiB. Every answer carries the content security policy.
Nothing here starts another process.
"""

from __future__ import annotations

import json
import re
import signal
import sys
import threading
import webbrowser
from contextlib import ExitStack
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse

from tcw.errors import BackendError, NotFound, Refused, TcwError, Unreachable, UsageError
from tcw.serve.services import Services
from tcw.store.base import MultipleMatch, StaleRevision

DEFAULT_PORT = 8765
HOST = "127.0.0.1"
MAX_BODY_BYTES = 1 * 1024 * 1024
POLICY = "default-src 'self'"
LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
WRITES = frozenset({"POST", "PUT", "PATCH"})
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}
MISSING_ASSETS = "packaged web assets are missing; reinstall TCW"


class ApiError(Exception):
    """An answer the server decides itself, not an operation's error."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code = status, code


def not_found(message: str = "not found") -> ApiError:
    return ApiError(HTTPStatus.NOT_FOUND, "not-found", message)


def read_only(message: str) -> ApiError:
    return ApiError(HTTPStatus.FORBIDDEN, "read-only", message)


def usage(message: str) -> ApiError:
    return ApiError(HTTPStatus.BAD_REQUEST, "usage", message)


def error_answer(error: BaseException) -> tuple[int, dict[str, Any]]:
    """The status and body for a failure (Design 11), by exception class.
    The message is the operation's own; no traceback is ever sent."""
    message = str(error)
    if isinstance(error, ApiError):
        return error.status, {"error": message, "code": error.code}
    if isinstance(error, StaleRevision):
        return HTTPStatus.CONFLICT, {"error": message, "code": "stale-revision"}
    if isinstance(error, UsageError):
        return HTTPStatus.BAD_REQUEST, {"error": message, "code": "usage"}
    if isinstance(error, NotFound):
        return HTTPStatus.NOT_FOUND, {"error": message, "code": "not-found"}
    if isinstance(error, Refused):
        body: dict[str, Any] = {"error": message, "code": "refused"}
        if error.name:
            body["ticket"] = error.name
        return HTTPStatus.CONFLICT, body
    if isinstance(error, MultipleMatch):
        return HTTPStatus.CONFLICT, {"error": message, "code": "refused"}
    if isinstance(error, Unreachable):
        return HTTPStatus.SERVICE_UNAVAILABLE, {"error": message, "code": "unreachable"}
    if isinstance(error, TcwError):
        return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": message, "code": "error"}
    if isinstance(error, ValueError):
        return HTTPStatus.BAD_REQUEST, {"error": message, "code": "usage"}
    return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": message or type(error).__name__,
                                              "code": "error"}


# ---------------------------------------------------------------------------
# Host and Origin


def _host_name(value: str) -> str:
    """The host in a `Host` header (`name[:port]`, `[::1]:port`)."""
    value = value.strip()
    if value.startswith("["):
        return value[1:value.find("]")] if "]" in value else value[1:]
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def _origin_host(value: str) -> str | None:
    parsed = urlparse(value.strip())
    if parsed.scheme not in ("http", "https"):
        return None
    return parsed.hostname


def from_loopback(host: str | None, origin: str | None) -> bool:
    """A request this server answers: a `Host` naming a loopback address, and
    an `Origin`, when there is one, naming one too. A missing `Host` is
    refused whatever the `Origin` says (DNS rebinding sends a hostile name as
    the `Host`, and a missing one cannot be checked)."""
    if not host or _host_name(host).lower() not in LOOPBACK:
        return False
    if origin is not None and (_origin_host(origin) or "").lower() not in LOOPBACK:
        return False
    return True


# ---------------------------------------------------------------------------
# Routing


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, list[str]]
    body: dict[str, Any]
    server: "TcwServer"
    match: re.Match | None = None

    @property
    def root(self) -> Path:
        return self.server.project_root

    @property
    def services(self) -> Services:
        return self.server.services

    @property
    def lock(self) -> threading.Lock:
        return self.server.write_lock

    def param(self, index: int) -> str:
        """A path parameter, percent-decoded once."""
        assert self.match is not None
        return unquote(self.match.group(index))

    def field(self, name: str, kind: type | tuple = str, *, required: bool = True,
              default: Any = None) -> Any:
        """A body field of the given type, or a usage error naming it."""
        if name not in self.body or self.body[name] is None:
            if required:
                raise usage(f"{name} is required")
            return default
        value = self.body[name]
        if not isinstance(value, kind) or isinstance(value, bool) and kind is not bool:
            raise usage(f"{name} has the wrong type")
        return value


Handler = Callable[[Request], tuple[int, Any]]


@dataclass(frozen=True)
class Route:
    method: str
    pattern: re.Pattern
    handler: Handler


def route(method: str, pattern: str, handler: Handler) -> Route:
    return Route(method, re.compile(pattern), handler)


def _routes() -> list[Route]:
    from tcw.serve import files as file_routes, records, work
    return [*records.ROUTES, *work.ROUTES, *file_routes.ROUTES]


# ---------------------------------------------------------------------------
# The server


def packaged_client(stack: ExitStack) -> Path:
    """The prebuilt client folder shipped as package data."""
    path = stack.enter_context(as_file(files("tcw.serve").joinpath("dist", "client")))
    if not (Path(path) / "index.html").is_file():
        raise BackendError(MISSING_ASSETS)
    return Path(path)


class TcwServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], project_root: Path, *,
                 client_dir: Path | None = None, services: Services | None = None):
        if address[0] != HOST:
            raise ValueError(f"the web viewer listens on {HOST} only")
        self.project_root = Path(project_root)
        self._stack = ExitStack()
        self.client_dir = Path(client_dir) if client_dir else packaged_client(self._stack)
        self.services = services or Services()
        self.write_lock = threading.Lock()
        self.routes = _routes()
        super().__init__(address, TcwHandler)

    def server_close(self) -> None:
        super().server_close()
        self._stack.close()


class TcwHandler(BaseHTTPRequestHandler):
    server: TcwServer

    def log_message(self, fmt: str, *args) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", POLICY)
        super().end_headers()

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, value: Any) -> None:
        self._send(status, json.dumps(value, default=str).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_PATCH(self) -> None:
        self._handle("PATCH")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def _handle(self, method: str) -> None:
        try:
            if not from_loopback(self.headers.get("Host"), self.headers.get("Origin")):
                raise ApiError(HTTPStatus.FORBIDDEN, "forbidden",
                               "this server answers only requests addressed to "
                               "this machine's loopback address")
            parsed = urlparse(self.path)
            if parsed.path == "/api" or parsed.path.startswith("/api/"):
                self._api(method, parsed.path, parse_qs(parsed.query))
            elif method == "GET":
                self._static(parsed.path)
            else:
                raise not_found()
        except Exception as error:  # every failure is an answer, never a traceback
            status, body = error_answer(error)
            try:
                self._send_json(status, body)
            except OSError:
                pass

    # -- the API ---------------------------------------------------------------

    def _api(self, method: str, path: str, query: dict[str, list[str]]) -> None:
        # A write's body is checked before its route is looked up, so a
        # request that is not JSON or too large never reaches any handler.
        body: dict[str, Any] = self._json_body() if method in WRITES else {}
        found = None
        for candidate in self.server.routes:
            if candidate.method == method:
                match = candidate.pattern.fullmatch(path)
                if match:
                    found = (candidate, match)
                    break
        if found is None:
            raise not_found(f"no API route {method} {path}")
        request = Request(method, path, query, body, self.server, found[1])
        status, value = found[0].handler(request)
        self._send_json(status, value)

    def _json_body(self) -> dict[str, Any]:
        """The request's JSON object: the content type first, then the size
        before reading and again after."""
        content_type = (self.headers.get("Content-Type") or "").split(";")[0]
        if content_type.strip().lower() != "application/json":
            raise usage("a write must be sent as application/json")
        declared = self.headers.get("Content-Length")
        if declared is None:
            raise usage("a write must carry a Content-Length header")
        try:
            length = int(declared)
        except ValueError:
            raise usage("the Content-Length header is not a number") from None
        if length < 0:
            raise usage("the Content-Length header is not a number")
        if length > MAX_BODY_BYTES:
            # A body up to twice the cap is read and dropped, so the client,
            # still sending, receives the 413 rather than a reset connection.
            # A larger one is not read at all.
            if length <= 2 * MAX_BODY_BYTES:
                self._discard(length)
            else:
                self.close_connection = True
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "too-large",
                           f"request body too large (at most {MAX_BODY_BYTES} bytes)")
        raw = self.rfile.read(length)
        if len(raw) > MAX_BODY_BYTES:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "too-large",
                           f"request body too large (at most {MAX_BODY_BYTES} bytes)")
        if not raw:
            raise usage("the request body is empty")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise usage(f"the request body is not JSON: {error}") from None
        if not isinstance(body, dict):
            raise usage("the request body must be a JSON object")
        return body

    def _discard(self, length: int) -> None:
        while length > 0:
            chunk = self.rfile.read(min(length, 64 * 1024))
            if not chunk:
                return
            length -= len(chunk)

    # -- the client ------------------------------------------------------------

    def _static(self, path: str) -> None:
        """A file of the prebuilt client, or `index.html` for any other path so
        a deep link loads the app. A path that leads outside the client
        folder is not found."""
        root = self.server.client_dir.resolve()
        relative = unquote(path).lstrip("/")
        if "\x00" in relative:
            raise not_found()
        target = root / "index.html"
        if relative:
            candidate = (root / relative).resolve()
            if not candidate.is_relative_to(root):
                raise not_found()
            if candidate.is_file():
                target = candidate
        content_type = CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream")
        self._send(HTTPStatus.OK, target.read_bytes(), content_type)


# ---------------------------------------------------------------------------
# Running it


def serve(project_root: Path, port: int = DEFAULT_PORT, open_browser: bool = True) -> int:
    """Serve until Ctrl-C or SIGTERM. stdout carries the URL alone, flushed
    as soon as the socket listens; everything else goes to stderr."""
    with ExitStack() as stack:
        client = packaged_client(stack)
        try:
            httpd = TcwServer((HOST, port), project_root, client_dir=client)
        except OSError as error:
            raise BackendError(f"cannot listen on {HOST} port {port}: "
                               f"{error.strerror or error}") from None
        stack.callback(httpd.server_close)
        url = f"http://{HOST}:{httpd.server_port}/"
        print(url, flush=True)
        if open_browser:
            threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
        in_main = threading.current_thread() is threading.main_thread()
        if in_main:
            previous = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGTERM, _interrupt)
            stack.callback(signal.signal, signal.SIGTERM, previous)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        print("stopped", file=sys.stderr)
        return 0


def _interrupt(_signum, _frame) -> None:
    raise KeyboardInterrupt
