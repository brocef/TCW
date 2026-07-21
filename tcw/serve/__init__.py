"""Local web viewer and editor for TCW content."""

from __future__ import annotations

import json
import hmac
import os
import re
import subprocess
import sys
import threading
import webbrowser
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from tcw.store.base import (
    CAP_FIELDS, CAP_STATUSES, WORK_ARTIFACTS, WORK_SIDECARS, _UNSET,
    IllegalTransition, RefError, StaleRevision,
)
from tcw.store.fs import (
    FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore, descendant_nodes,
    find_node_root, heading_slug, registered_project_id, resolve_qualified_work_ref,
)
from tcw.refs import resolve_tcw_ref

# tcw:// axis letter -> SPA axis word (the client does no TCW parsing itself).
_AXIS_WORD = {"T": "taxonomy", "C": "capabilities", "W": "work"}
# Max uris accepted per /api/resolve batch (a rendered body's link count).
RESOLVE_MAX_URIS = 256

DEFAULT_PORT = 8765
HOST = "127.0.0.1"

# Maximum request body size (1 MiB) — enforced before full body read/parse.
MAX_BODY_BYTES = 1 * 1024 * 1024

# Loopback addresses allowed for Host/Origin on mutating requests.
# 0.0.0.0 is a bind address, not a client origin — deliberately excluded.
_LOOPBACK_ADDRS = frozenset({
    "127.0.0.1", "localhost", "::1",
})

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


# ── JSON serialization helpers ────────────────────────────────────────────────


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


def _valid_sidecar_token(supplied: str, expected: str | None) -> bool:
    """Validate the private sidecar credential without timing-sensitive equality."""
    return expected is None or hmac.compare_digest(supplied, expected)


# ── Static file helpers ───────────────────────────────────────────────────────


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


# ── Route parsing helpers ─────────────────────────────────────────────────────

# Pattern to extract taxonomy ref (may contain percent-encoded / and #)
# e.g. /api/taxonomy/store%2Fadapter  or /api/taxonomy/web%2Fediting%23edit-...
_RE_TAXONOMY_REF = re.compile(
    r"^/api/taxonomy/([^/]+)$"
)

# Pattern for capability ref — format: path#heading-slug
# path may be percent-encoded, heading is the last segment after #
# e.g. /api/capabilities/web or /api/capabilities/web%2Fediting
_RE_CAPABILITY_REF = re.compile(
    r"^/api/capabilities/([^/]+)$"
)


def _decode_path_param(param: str) -> str:
    """Decode a URL path parameter exactly once (RFC 3986 percent-encoding).

    Handles single-segment refs that contain / and # encoded as %2F and %23.
    """
    return unquote(param)


def _parse_ref_param(path: str, prefix: str) -> str | None:
    """Extract and decode a ref from `path` after `prefix`.

    The ref is a single URL path segment (everything after the prefix up to
    the next / or end-of-string). Percent-encoded characters are decoded once.
    Returns None if there is nothing after the prefix.
    """
    rest = path[len(prefix):]
    if not rest:
        return None
    # Split on first literal '/' to get a single path segment
    segment = rest.split("/", 1)[0]
    return _decode_path_param(segment)


# ── Response helpers ──────────────────────────────────────────────────────────


def _err_json(value: dict) -> bytes:
    """Serialize an error dict to JSON bytes."""
    return json.dumps(value).encode("utf-8")


def _err(status: int, message: str, **extra: Any) -> tuple[int, bytes]:
    """Build a (status, body) error response."""
    envelope = {"error": message}
    if extra:
        envelope.update(extra)
    return status, _err_json(envelope)


def _ok_json(value) -> tuple[int, bytes]:
    return HTTPStatus.OK, _json_bytes(value)


# ── Exception mapping ─────────────────────────────────────────────────────────


def _map_store_error(e: Exception) -> tuple[int, bytes]:
    """Map store-level exceptions to HTTP status codes and JSON error bodies.

    "no such" / "no heading" ValueError messages → 404.
    StaleRevision → 409.
    IllegalTransition / validation ValueError / RefError → 422.
    Everything else → 500.
    """
    msg = str(e).lower()
    if isinstance(e, StaleRevision):
        return _err(HTTPStatus.CONFLICT, str(e))
    if isinstance(e, IllegalTransition):
        return _err(HTTPStatus.UNPROCESSABLE_ENTITY, str(e))
    if isinstance(e, RefError):
        return _err(HTTPStatus.UNPROCESSABLE_ENTITY, str(e))
    if isinstance(e, ValueError):
        # "no such" errors (unknown slug/ref) are 404
        if "no such" in msg or "no heading" in msg:
            return _err(HTTPStatus.NOT_FOUND, str(e))
        return _err(HTTPStatus.UNPROCESSABLE_ENTITY, str(e))
    # I/O or unexpected errors → 500
    return _err(HTTPStatus.INTERNAL_SERVER_ERROR, f"server error: {e}")


# ── CSRF / origin helpers ─────────────────────────────────────────────────────


def _is_loopback_origin(host: str | None, origin: str | None) -> bool:
    """Check whether Host/Origin headers indicate a loopback origin.

    Security rule:
    - If Origin is present, it MUST be loopback (rejects cross-origin requests
      from malicious pages that set Origin to themselves while reaching 127.0.0.1
      via DNS rebinding).
    - If Origin is absent, Host must be loopback (direct curl-style requests).
    - If both are absent, reject.
    """
    if not host and not origin:
        return False

    def _extract_addr(hdr: str) -> str:
        """Extract the hostname from a header value."""
        # Remove protocol
        if hdr.startswith("http://"):
            hdr = hdr[7:]
        elif hdr.startswith("https://"):
            hdr = hdr[8:]
        # Remove userinfo
        if "@" in hdr:
            hdr = hdr.rsplit("@", 1)[-1]
        # Remove path
        hdr = hdr.split("/", 1)[0]
        # Bracketed IPv6 literal, e.g. "[::1]:8765" -> "::1"
        if hdr.startswith("["):
            return hdr[1:hdr.find("]")] if "]" in hdr else hdr[1:]
        # Remove :port (IPv4 / hostname)
        return hdr.split(":")[0]

    # If Origin is set, it MUST be loopback
    if origin:
        addr = _extract_addr(origin)
        if addr not in _LOOPBACK_ADDRS:
            return False

    # If Host is set, it must be loopback
    if host:
        addr = _extract_addr(host)
        if addr not in _LOOPBACK_ADDRS:
            return False

    return True


def _validate_mutating_request(
    handler: "TcwHandler",
) -> tuple[int, bytes] | None:
    """Validate a mutating request (POST/PATCH/PUT/DELETE).

    Returns (status, body) if the request should be rejected, or None if OK.
    Checks: Content-Type must be application/json; origin must be loopback.
    """
    ct = handler.headers.get("Content-Type", "")
    # Accept application/json with optional charset
    ct_base = ct.split(";")[0].strip().lower() if ct else ""
    if ct_base != "application/json":
        return _err(
            HTTPStatus.BAD_REQUEST,
            "Content-Type must be application/json for mutating requests",
        )

    host = handler.headers.get("Host")
    origin = handler.headers.get("Origin")
    if not _is_loopback_origin(host, origin):
        return _err(
            HTTPStatus.BAD_REQUEST,
            "mutating requests are only allowed from loopback origins",
        )
    return None


# ── Body reading ──────────────────────────────────────────────────────────────


def _read_json_body(
    handler: "TcwHandler",
) -> tuple[Any, tuple[int, bytes] | None]:
    """Read and parse a JSON request body with size enforcement.

    Returns (parsed_body, error_or_none).  On error, parsed_body is None.
    Enforces Content-Length against MAX_BODY_BYTES before reading.
    """
    cl_str = handler.headers.get("Content-Length")
    if cl_str is not None:
        try:
            cl = int(cl_str)
        except (ValueError, TypeError):
            return None, _err(
                HTTPStatus.BAD_REQUEST,
                f"malformed Content-Length header",
            )
        if cl > MAX_BODY_BYTES:
            return None, _err(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                f"request body too large (max {MAX_BODY_BYTES} bytes, "
                f"got {cl})",
            )
    else:
        # Missing Content-Length: for non-Chunked requests this is unusual;
        # we still attempt to read but cap at MAX_BODY_BYTES.
        cl = MAX_BODY_BYTES

    raw = handler.rfile.read(cl)
    if not raw:
        return None, _err(HTTPStatus.BAD_REQUEST, "empty request body")
    # Safety cap: if Content-Length was missing, raw might exceed MAX_BODY_BYTES
    # due to server buffering. Check total read.
    if len(raw) > MAX_BODY_BYTES:
        return None, _err(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            f"request body too large (max {MAX_BODY_BYTES} bytes, "
            f"got {len(raw)})",
        )
    try:
        body = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, _err(HTTPStatus.BAD_REQUEST, f"invalid JSON: {exc}")
    if not isinstance(body, dict):
        return None, _err(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return body, None


# ── Server classes ────────────────────────────────────────────────────────────


class TcwServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], node_root: Path,
                 include_descendants: bool = False, *, token: str | None = None,
                 api_only: bool = False):
        super().__init__(server_address, TcwHandler)
        self.node_root = node_root
        self.include_descendants = include_descendants
        self.token = token
        self.api_only = api_only


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

    def _send_err(self, status: int, message: str, **extra: Any) -> None:
        _, body = _err(status, message, **extra)
        self._send(status, body, "application/json; charset=utf-8")

    def _authorized(self) -> bool:
        expected = self.server.token
        supplied = self.headers.get("X-TCW-Sidecar-Token", "")
        if _valid_sidecar_token(supplied, expected):
            return True
        self._send_err(HTTPStatus.FORBIDDEN, "sidecar authentication required")
        return False

    def _stores(self) -> tuple[FsWorkStore, FsTaxonomyStore, FsCapabilitiesStore]:
        root = self.server.node_root
        return (
            FsWorkStore.open(root),
            FsTaxonomyStore.open(root),
            FsCapabilitiesStore.open(root),
        )

    def _resolve_work(self, slug: str) -> "tuple[FsWorkStore, str] | None":
        """(store, bare_slug) for a work slug — gated on --include-descendants.

        Flag off: always (anchor store, slug), so a bare slug works as before and a
        '/'-bearing slug matches no folder name → 404 (serve byte-for-byte
        unchanged, no descendant read or mutated). Flag on: resolve sub/proj/<slug>
        to the descendant store; None (unknown/traversal) → the caller sends 404."""
        if self.server.include_descendants:
            return resolve_qualified_work_ref(self.server.node_root, slug)
        return FsWorkStore.open(self.server.node_root), slug

    def _board(self) -> list:
        """The board; with --include-descendants, the anchor plus every descendant
        node's board, each descendant item's slug qualified (`sub/proj/<slug>`)."""
        anchor = self.server.node_root.resolve()
        if not self.server.include_descendants:
            return FsWorkStore.open(anchor).board()
        items = []
        for root in [anchor, *descendant_nodes(anchor)]:
            prefix = "" if root == anchor else f"{registered_project_id(anchor, root)}/"
            for it in FsWorkStore.open(root).board():
                it.slug = f"{prefix}{it.slug}"        # fresh WorkItems — safe to mutate
                items.append(it)
        return items

    # ── HTTP method dispatchers ───────────────────────────────────────────

    def do_GET(self) -> None:
        if not self._authorized():
            return
        try:
            self._get()
        except Exception as e:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, str(e).encode("utf-8"))

    def do_POST(self) -> None:
        if not self._authorized():
            return
        try:
            self._post()
        except Exception as e:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, str(e).encode("utf-8"))

    def do_PATCH(self) -> None:
        if not self._authorized():
            return
        try:
            self._patch()
        except Exception as e:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, str(e).encode("utf-8"))

    def do_PUT(self) -> None:
        if not self._authorized():
            return
        try:
            self._put()
        except Exception as e:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, str(e).encode("utf-8"))

    def do_DELETE(self) -> None:
        if not self._authorized():
            return
        try:
            self._delete()
        except Exception as e:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, str(e).encode("utf-8"))

    # ── GET routes ────────────────────────────────────────────────────────

    def _get(self) -> None:
        path = urlparse(self.path).path

        # Static files
        if not self.server.api_only and path == "/":
            body, ctype = _static_bytes("index.html")
            self._send(HTTPStatus.OK, body, ctype)
            return
        if not self.server.api_only and path in ("/app.js", "/style.css", "/marked.min.js", "/tree.js"):
            body, ctype = _static_bytes(path.lstrip("/"))
            self._send(HTTPStatus.OK, body, ctype)
            return

        # SPA fallback: any non-API GET that isn't a known static asset serves the
        # app shell, so History-API deep links / reloads work (/work/<slug>,
        # /taxonomy, /sub/proj/work/<slug>, …). API paths keep their own 404s.
        if not self.server.api_only and not path.startswith("/api/"):
            body, ctype = _static_bytes("index.html")
            self._send(HTTPStatus.OK, body, ctype)
            return

        work, taxonomy, capabilities = self._stores()

        # ── Work routes ──

        if path == "/api/work":
            self._send_json(HTTPStatus.OK, self._board())
            return

        # Subresource routes for work must be matched BEFORE the catch-all
        # work-detail route.

        # GET /api/work/<slug>/artifacts/<name>
        m = re.match(r"^/api/work/([^/]+)/artifacts/([^/]+)$", path)
        if m:
            slug = _decode_path_param(m.group(1))
            name = _decode_path_param(m.group(2))
            if name not in WORK_ARTIFACTS:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown artifact")
                return
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            item = work.get(slug)
            if item is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            try:
                resource = work.read_artifact(slug, name)
            except ValueError as e:
                self._send(HTTPStatus.BAD_REQUEST, str(e).encode("utf-8"))
                return
            if resource is None:
                self._send(HTTPStatus.NOT_FOUND, b"artifact not present")
                return
            self._send_json(HTTPStatus.OK, {
                "name": resource.name,
                "content": resource.content,
                "mediaType": resource.media_type,
                "revision": resource.revision,
            })
            return

        # GET /api/work/<slug>/sidecars/<name>
        m = re.match(r"^/api/work/([^/]+)/sidecars/([^/]+)$", path)
        if m:
            slug = _decode_path_param(m.group(1))
            name = _decode_path_param(m.group(2))
            if name not in WORK_SIDECARS:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown sidecar")
                return
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            item = work.get(slug)
            if item is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            try:
                resource = work.read_sidecar(slug, name)
            except ValueError as e:
                self._send(HTTPStatus.BAD_REQUEST, str(e).encode("utf-8"))
                return
            if resource is None:
                self._send(HTTPStatus.NOT_FOUND, b"sidecar not present")
                return
            self._send_json(HTTPStatus.OK, {
                "name": resource.name,
                "content": resource.content,
                "mediaType": resource.media_type,
                "revision": resource.revision,
            })
            return

        # GET /api/work/<slug>/sidecars (discovery endpoint)
        m = re.match(r"^/api/work/([^/]+)/sidecars$", path)
        if m:
            slug = _decode_path_param(m.group(1))
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            item = work.get(slug)
            if item is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            detail = work.get_detail(slug)
            # Build discovery list from registry
            sidecars = []
            for sc_name, sc_info in WORK_SIDECARS.items():
                present = False
                revision = ""
                if detail and sc_name in detail.sidecar_revisions:
                    present = True
                    revision = detail.sidecar_revisions[sc_name]
                sidecars.append({
                    "name": sc_name,
                    "mediaType": sc_info["media_type"],
                    "present": present,
                    "revision": revision,
                })
            self._send_json(HTTPStatus.OK, sidecars)
            return

        # GET /api/work/tags — the node's registered tag set (read-only).
        # Placed before the catch-all so "tags" isn't parsed as a slug.
        if path == "/api/work/tags":
            self._send_json(HTTPStatus.OK, {"tags": work.registered_tags()})
            return

        # Catch-all work detail: /api/work/<slug>
        if path.startswith("/api/work/"):
            slug = _parse_ref_param(path, "/api/work/")
            if not slug:
                self._send(HTTPStatus.NOT_FOUND, b"not found")
                return
            qslug = slug                          # preserve the addressed (qualified) slug
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            detail = work.get_detail(slug)
            if detail is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            # Build response with revision-bearing detail. Echo the *qualified*
            # slug so the (unchanged) web UI keeps addressing this descendant item
            # when it derives artifact/sidecar/action URLs from item.slug.
            item_data = _jsonable(detail.item)
            item_data["slug"] = qslug
            artifacts_list = []
            for name in WORK_ARTIFACTS:
                try:
                    res = work.read_artifact(slug, name)
                    if res is not None:
                        artifacts_list.append({
                            "name": res.name,
                            "present": True,
                            "revision": res.revision,
                            "mediaType": res.media_type,
                        })
                    else:
                        artifacts_list.append({"name": name, "present": False})
                except ValueError:
                    pass
            # Sidecar discovery in detail
            sidecars = []
            for sc_name, sc_info in WORK_SIDECARS.items():
                present = sc_name in detail.sidecar_revisions
                sidecars.append({
                    "name": sc_name,
                    "mediaType": sc_info["media_type"],
                    "present": present,
                    "revision": detail.sidecar_revisions.get(sc_name, ""),
                })
            self._send_json(HTTPStatus.OK, {
                "item": item_data,
                "artifacts": artifacts_list,
                "sidecars": sidecars,
                "coreRevision": detail.core_revision,
                "dodChecklist": work.dod_checklist(),
            })
            return

        # ── Taxonomy routes ──

        if path == "/api/taxonomy":
            self._send_json(HTTPStatus.OK, taxonomy.list_all())
            return

        # GET /api/taxonomy/<ref> — detail with revision
        m = _RE_TAXONOMY_REF.match(path)
        if m:
            ref = _decode_path_param(m.group(1))
            try:
                detail = taxonomy.get_term_detail(ref)
            except (AmbiguousRef, RefError) as e:
                self._send(HTTPStatus.UNPROCESSABLE_ENTITY, str(e).encode("utf-8"))
                return
            if detail is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such term")
                return
            term_data = _jsonable(detail.term)
            self._send_json(HTTPStatus.OK, {
                "term": term_data,
                "coreRevision": detail.core_revision,
            })
            return

        # ── Capability routes ──

        if path == "/api/capabilities":
            self._send_json(HTTPStatus.OK, capabilities.list_all())
            return

        # GET /api/capabilities/<ref> — detail with revision
        m = _RE_CAPABILITY_REF.match(path)
        if m:
            ref = _decode_path_param(m.group(1))
            try:
                detail = capabilities.get_capability_detail(ref)
            except (RefError,) as e:
                self._send(HTTPStatus.UNPROCESSABLE_ENTITY, str(e).encode("utf-8"))
                return
            if detail is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such capability")
                return
            cap_data = _jsonable(detail.capability)
            self._send_json(HTTPStatus.OK, {
                "capability": cap_data,
                "coreRevision": detail.core_revision,
            })
            return

        self._send(HTTPStatus.NOT_FOUND, b"not found")

    # ── POST routes ───────────────────────────────────────────────────────

    def _post(self) -> None:
        path = urlparse(self.path).path

        # Every POST is a mutating action — including the artifact /open endpoint,
        # which spawns the desktop opener. Enforce CSRF/loopback + JSON content
        # type for ALL of them before dispatching (a cross-origin simple POST must
        # not reach /open).
        reject = _validate_mutating_request(self)
        if reject:
            self._send(reject[0], reject[1], "application/json; charset=utf-8")
            return

        # ── Legacy: artifact open endpoint ──
        # POST /api/work/<slug>/artifacts/<name>/open
        prefix = "/api/work/"
        suffix = "/open"
        marker = "/artifacts/"
        if (path.startswith(prefix) and path.endswith(suffix)
                and marker in path):
            self._handle_open(path)
            return

        body, err = _read_json_body(self)
        if err:
            self._send(err[0], err[1], "application/json; charset=utf-8")
            return

        work, taxonomy, capabilities = self._stores()

        # ── POST /api/work — create work item ──
        if path == "/api/work":
            try:
                title = body.get("title", "")
                if not title:
                    self._send_err(HTTPStatus.BAD_REQUEST, "title is required")
                    return
                created = body.get("created")
                body_text = body.get("body", "")
                priority = body.get("priority")
                effort = body.get("effort", "")
                complexity = body.get("complexity", "")
                blockers = body.get("blockers")
                parent = body.get("parent")
                initiative = body.get("initiative", "")
                type_val = body.get("type", "")
                tags = body.get("tags") or None
                detail = work.create_work(
                    title=title,
                    created=created,
                    body=body_text,
                    priority=priority,
                    effort=effort if effort else "",
                    complexity=complexity if complexity else "",
                    blockers=blockers,
                    parent=parent,
                    initiative=initiative if initiative else "",
                    type=type_val if type_val else "",
                    tags=tags,
                )
                self._send_json(HTTPStatus.CREATED, {
                    "item": _jsonable(detail.item),
                    "coreRevision": detail.core_revision,
                    "artifactRevisions": detail.artifact_revisions,
                    "sidecarRevisions": detail.sidecar_revisions,
                })
            except (ValueError, StaleRevision, RefError, IllegalTransition) as e:
                status_code, body_bytes = _map_store_error(e)
                self._send(status_code, body_bytes, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        # ── POST /api/work/<slug>/actions/<action> ──
        m = re.match(r"^/api/work/([^/]+)/actions/([^/]+)$", path)
        if m:
            slug = _decode_path_param(m.group(1))
            action = _decode_path_param(m.group(2))
            qslug = slug                          # preserve the addressed (qualified) slug
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            if action == "start":
                force = bool(body.get("force", False))
                try:
                    item = work.start(slug, force=force)
                    item.slug = qslug             # echo the qualified slug to the UI
                    self._send_json(HTTPStatus.OK, _jsonable(item))
                except (ValueError, StaleRevision, IllegalTransition, RefError) as e:
                    sc, bb = _map_store_error(e)
                    self._send(sc, bb, "application/json; charset=utf-8")
                except Exception as e:
                    self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                               f"server error: {e}".encode("utf-8"))
                return
            elif action == "complete":
                resolution = body.get("resolution")
                dod_ack = body.get("dod_ack") or body.get("dodAck")
                force = bool(body.get("force", False))
                if not resolution:
                    self._send_err(HTTPStatus.BAD_REQUEST,
                                   "resolution is required")
                    return
                if not isinstance(dod_ack, list):
                    dod_ack = []
                try:
                    item = work.complete(slug, resolution, dod_ack, force=force)
                    item.slug = qslug             # echo the qualified slug to the UI
                    self._send_json(HTTPStatus.OK, _jsonable(item))
                except (ValueError, StaleRevision, IllegalTransition, RefError) as e:
                    sc, bb = _map_store_error(e)
                    self._send(sc, bb, "application/json; charset=utf-8")
                except Exception as e:
                    self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                               f"server error: {e}".encode("utf-8"))
                return
            else:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown action")
                return

        # ── POST /api/taxonomy — create taxonomy term ──
        if path == "/api/taxonomy":
            try:
                name = body.get("name", "")
                if not name:
                    self._send_err(HTTPStatus.BAD_REQUEST, "name is required")
                    return
                slug_param = body.get("slug")
                parent = body.get("parent")
                description = body.get("description", "")
                kind = body.get("kind", "Vocabulary")
                vocabulary = body.get("vocabulary")
                term = taxonomy.add(
                    name=name,
                    slug=slug_param,
                    parent=parent,
                    description=description,
                    kind=kind,
                    vocabulary=vocabulary,
                )
                # Return with revision
                ref = term.slug
                detail = taxonomy.get_term_detail(ref)
                response = {
                    "term": _jsonable(term),
                    "coreRevision": detail.core_revision if detail else "",
                }
                # Run post-write check and include warnings
                warnings = taxonomy.check()
                if warnings:
                    response["warnings"] = warnings
                self._send_json(HTTPStatus.CREATED, response)
            except (ValueError, RefError) as e:
                sc, bb = _map_store_error(e)
                self._send(sc, bb, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        # ── POST /api/capabilities — create a capability folder ──
        if path == "/api/capabilities":
            try:
                cap_path = body.get("path", "")
                if not cap_path:
                    self._send_err(HTTPStatus.BAD_REQUEST, "path is required")
                    return
                name = body.get("name") or None
                status = body.get("status", "Missing")
                body_text = body.get("body", "")
                fields = body.get("fields")
                capabilities.add(cap_path, name=name, status=status, body=body_text)
                if fields:
                    capabilities.set(cap_path, fields)
                detail = capabilities.get_capability_detail(cap_path)
                response = {
                    "capability": _jsonable(detail.capability),
                    "coreRevision": detail.core_revision,
                }
                # Run post-write check and include warnings
                warnings = capabilities.check(taxonomy=taxonomy)
                if warnings:
                    response["warnings"] = warnings
                self._send_json(HTTPStatus.CREATED, response)
            except (ValueError, RefError) as e:
                sc, bb = _map_store_error(e)
                self._send(sc, bb, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        # ── POST /api/resolve — resolve tcw:// links for the SPA (a read over POST
        #    so it can carry a body). Descendant work resolves only when the viewer
        #    aggregates descendants. ──
        if path == "/api/resolve":
            uris = body.get("uris")
            if not isinstance(uris, list):
                self._send_err(HTTPStatus.BAD_REQUEST, "uris must be a list")
                return
            result = {}
            for uri in uris[:RESOLVE_MAX_URIS]:
                if not isinstance(uri, str):
                    continue
                r = resolve_tcw_ref(self.server.node_root, uri,
                                    include_descendants=self.server.include_descendants)
                result[uri] = ({"ok": True, "axis": _AXIS_WORD.get(r.axis), "key": r.key}
                               if r.ok else {"ok": False})
            self._send_json(HTTPStatus.OK, result)
            return

        self._send(HTTPStatus.NOT_FOUND, b"not found")

    # ── PATCH routes ──────────────────────────────────────────────────────

    def _patch(self) -> None:
        path = urlparse(self.path).path

        # All PATCH routes require CSRF + JSON validation
        reject = _validate_mutating_request(self)
        if reject:
            self._send(reject[0], reject[1], "application/json; charset=utf-8")
            return

        body, err = _read_json_body(self)
        if err:
            self._send(err[0], err[1], "application/json; charset=utf-8")
            return

        work, taxonomy, capabilities = self._stores()

        # ── PATCH /api/work/<slug> ──
        m = re.match(r"^/api/work/([^/]+)$", path)
        if m:
            slug = _decode_path_param(m.group(1))
            qslug = slug                          # preserve the addressed (qualified) slug
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            core_revision = body.get("revision")
            fields = body.get("fields", {})
            body_text = body.get("body")

            # Build keyword args: only pass keys that are present in fields
            kw: dict[str, Any] = {}
            work_field_keys = {
                "title", "priority", "effort", "complexity",
                "blockers", "initiative", "parent", "tags",
            }
            for k, v in fields.items():
                if k not in work_field_keys:
                    self._send_err(HTTPStatus.BAD_REQUEST,
                                   f"unknown work field '{k}'")
                    return
                kw[k] = v
            # Handle body separately
            if "body" in body:
                kw["body"] = body_text
            if core_revision is not None:
                kw["core_revision"] = core_revision

            try:
                detail = work.update_work(slug, **kw)
                item_data = _jsonable(detail.item)
                item_data["slug"] = qslug         # echo the qualified slug to the UI
                self._send_json(HTTPStatus.OK, {
                    "item": item_data,
                    "coreRevision": detail.core_revision,
                    "artifactRevisions": detail.artifact_revisions,
                    "sidecarRevisions": detail.sidecar_revisions,
                })
            except (ValueError, StaleRevision, RefError) as e:
                sc, bb = _map_store_error(e)
                self._send(sc, bb, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        # ── PATCH /api/taxonomy/<ref> ──
        m = _RE_TAXONOMY_REF.match(path)
        if m:
            ref = _decode_path_param(m.group(1))
            core_revision = body.get("revision")
            fields = body.get("fields", {})
            body_text = body.get("body")

            kw: dict[str, Any] = {}
            # Map API field names to store field names
            field_map = {
                "name": "name",
                "description": "description",
                "kind": "kind",
                "relates_to": "relates_to",
                "relatesTo": "relates_to",
                "vocabulary": "vocabulary",
            }
            for api_key, store_key in field_map.items():
                if api_key in fields:
                    kw[store_key] = fields[api_key]
            if "body" in body:
                # body maps to description for taxonomy
                kw["description"] = body_text
            if core_revision is not None:
                kw["core_revision"] = core_revision

            try:
                detail = taxonomy.update_term(ref, **kw)
                response = {
                    "term": _jsonable(detail.term),
                    "coreRevision": detail.core_revision,
                }
                # Run post-write check and include warnings
                warnings = taxonomy.check()
                if warnings:
                    response["warnings"] = warnings
                self._send_json(HTTPStatus.OK, response)
            except (ValueError, StaleRevision, RefError) as e:
                sc, bb = _map_store_error(e)
                self._send(sc, bb, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        # ── PATCH /api/capabilities/<ref> ──
        m = _RE_CAPABILITY_REF.match(path)
        if m:
            ref = _decode_path_param(m.group(1))
            core_revision = body.get("revision")
            fields = body.get("fields")
            body_text = body.get("body")

            kw: dict[str, Any] = {}
            if fields is not None:
                kw["fields"] = fields
            if "body" in body:
                kw["body"] = body_text
            if core_revision is not None:
                kw["core_revision"] = core_revision

            try:
                detail = capabilities.update_capability(ref, **kw)
                response = {
                    "capability": _jsonable(detail.capability),
                    "coreRevision": detail.core_revision,
                }
                # Run post-write check and include warnings
                warnings = capabilities.check(taxonomy=taxonomy)
                if warnings:
                    response["warnings"] = warnings
                self._send_json(HTTPStatus.OK, response)
            except (ValueError, StaleRevision, RefError) as e:
                sc, bb = _map_store_error(e)
                self._send(sc, bb, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        self._send(HTTPStatus.NOT_FOUND, b"not found")

    # ── PUT routes ────────────────────────────────────────────────────────

    def _put(self) -> None:
        path = urlparse(self.path).path

        # All PUT routes require CSRF + JSON validation
        reject = _validate_mutating_request(self)
        if reject:
            self._send(reject[0], reject[1], "application/json; charset=utf-8")
            return

        body, err = _read_json_body(self)
        if err:
            self._send(err[0], err[1], "application/json; charset=utf-8")
            return

        work, taxonomy, capabilities = self._stores()

        # ── PUT /api/work/<slug>/artifacts/<name> ──
        m = re.match(r"^/api/work/([^/]+)/artifacts/([^/]+)$", path)
        if m:
            slug = _decode_path_param(m.group(1))
            name = _decode_path_param(m.group(2))
            if name not in WORK_ARTIFACTS:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown artifact")
                return
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            item = work.get(slug)
            if item is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            content = body.get("content")
            if content is None:
                self._send_err(HTTPStatus.BAD_REQUEST, "content is required")
                return
            revision = body.get("revision")
            try:
                resource = work.write_artifact(slug, name, content,
                                               revision=revision)
                self._send_json(HTTPStatus.OK, {
                    "name": resource.name,
                    "content": resource.content,
                    "mediaType": resource.media_type,
                    "revision": resource.revision,
                })
            except (ValueError, StaleRevision) as e:
                sc, bb = _map_store_error(e)
                self._send(sc, bb, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        # ── PUT /api/work/<slug>/sidecars/<name> ──
        m = re.match(r"^/api/work/([^/]+)/sidecars/([^/]+)$", path)
        if m:
            slug = _decode_path_param(m.group(1))
            name = _decode_path_param(m.group(2))
            if name not in WORK_SIDECARS:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown sidecar")
                return
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            item = work.get(slug)
            if item is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            content = body.get("content")
            if content is None:
                self._send_err(HTTPStatus.BAD_REQUEST, "content is required")
                return
            media_type = body.get("mediaType")
            revision = body.get("revision")
            try:
                resource = work.write_sidecar(slug, name, content,
                                              media_type=media_type,
                                              revision=revision)
                self._send_json(HTTPStatus.OK, {
                    "name": resource.name,
                    "content": resource.content,
                    "mediaType": resource.media_type,
                    "revision": resource.revision,
                })
            except (ValueError, StaleRevision) as e:
                sc, bb = _map_store_error(e)
                self._send(sc, bb, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        self._send(HTTPStatus.NOT_FOUND, b"not found")

    # ── DELETE routes ────────────────────────────────────────────────────

    def _delete(self) -> None:
        path = urlparse(self.path).path

        # All DELETE routes require CSRF validation (no body needed)
        reject = _validate_mutating_request(self)
        if reject:
            self._send(reject[0], reject[1], "application/json; charset=utf-8")
            return

        work, taxonomy, capabilities = self._stores()

        # ── DELETE /api/work/<slug> ──
        m = re.match(r"^/api/work/([^/]+)$", path)
        if m:
            slug = _decode_path_param(m.group(1))
            resolved = self._resolve_work(slug)
            if resolved is None:
                self._send(HTTPStatus.NOT_FOUND, b"no such work item")
                return
            work, slug = resolved
            try:
                work.drop(slug)
                self._send(HTTPStatus.NO_CONTENT)
            except (ValueError, IllegalTransition) as e:
                sc, bb = _map_store_error(e)
                self._send(sc, bb, "application/json; charset=utf-8")
            except Exception as e:
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR,
                           f"server error: {e}".encode("utf-8"))
            return

        self._send(HTTPStatus.NOT_FOUND, b"not found")

    # ── Legacy: artifact open handler ────────────────────────────────────

    def _handle_open(self, path: str) -> None:
        prefix = "/api/work/"
        suffix = "/open"
        marker = "/artifacts/"
        if not (path.startswith(prefix) and path.endswith(suffix) and marker in path):
            self._send(HTTPStatus.NOT_FOUND, b"not found")
            return
        middle = path[len(prefix):-len(suffix)]
        slug_q, _, name_q = middle.partition(marker)
        slug = _decode_path_param(slug_q)
        name = _decode_path_param(name_q)
        if name not in WORK_ARTIFACTS:
            self._send(HTTPStatus.BAD_REQUEST, b"unknown artifact")
            return

        resolved = self._resolve_work(slug)
        if resolved is None:
            self._send(HTTPStatus.NOT_FOUND, b"no such work item")
            return
        work, slug = resolved
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


# Import AmbiguousRef at module level (used in _get but defined in base)
from tcw.store.base import AmbiguousRef  # noqa: E402, isort:skip


def serve(port: int = DEFAULT_PORT, open_browser: bool = True,
          node_root: Path | None = None, include_descendants: bool = False) -> int:
    from tcw.serve.runtime import run_server
    return run_server(port=port, open_browser=open_browser, node_root=node_root,
                      include_descendants=include_descendants)
