"""serve POST /api/resolve — batch tcw:// resolution for the SPA."""

import json
import subprocess
import threading
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from tcw.serve import HOST, RESOLVE_MAX_URIS, TcwServer
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore, init


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["taxonomy", "capabilities", "work"], root)
    return root


def _start(root: Path, include_descendants: bool = False):
    httpd = TcwServer((HOST, 0), root, include_descendants)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://{HOST}:{httpd.server_port}"


def _resolve(base: str, uris, headers=None) -> tuple[int, dict | None]:
    data = json.dumps({"uris": uris}).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = Request(f"{base}/api/resolve", data=data, headers=hdrs, method="POST")
    try:
        with urlopen(req) as res:
            raw = res.read()
            return res.status, (json.loads(raw) if raw else None)
    except HTTPError as e:
        return e.code, None


def test_resolve_local_axes(tmp_path):
    root = _node(tmp_path)
    FsTaxonomyStore.open(root).add("Login", slug="auth")
    FsCapabilitiesStore.open(root).add("web", name="Browse")
    item = FsWorkStore.open(root).create("A task", created="2026-01-01")
    httpd, base = _start(root)
    try:
        status, body = _resolve(base, [
            "tcw://T/auth", "tcw://C/web", f"tcw://W/{item.slug}"])
        assert status == HTTPStatus.OK
        assert body["tcw://T/auth"] == {"ok": True, "axis": "taxonomy", "key": "auth"}
        assert body["tcw://C/web"] == {"ok": True, "axis": "capabilities", "key": "web"}
        assert body[f"tcw://W/{item.slug}"] == {
            "ok": True, "axis": "work", "key": item.slug}
    finally:
        httpd.shutdown()


def test_resolve_federated_capability(tmp_path):
    base_repo = _node(tmp_path, "base")
    FsCapabilitiesStore.open(base_repo).add("auth/login", name="Sign in")
    child = _node(tmp_path, "child")
    FsCapabilitiesStore.open(child).extends_add("shared", "../base")
    httpd, base = _start(child)
    try:
        _, body = _resolve(base, ["tcw://shared/C/auth/login"])
        assert body["tcw://shared/C/auth/login"] == {
            "ok": True, "axis": "capabilities", "key": "shared/auth/login"}
    finally:
        httpd.shutdown()


def test_resolve_descendant_work_gated(tmp_path):
    root = _node(tmp_path)
    sub = root / "sub" / "proj"
    sub.mkdir(parents=True)
    init(["work"], sub)
    item = FsWorkStore.open(sub).create("Child", created="2026-01-01")
    uri = f"tcw://sub/proj/W/{item.slug}"

    # Not aggregating descendants -> unhosted.
    httpd, base = _start(root, include_descendants=False)
    try:
        _, body = _resolve(base, [uri])
        assert body[uri] == {"ok": False}
    finally:
        httpd.shutdown()

    # Aggregating -> resolves to the qualified key.
    httpd, base = _start(root, include_descendants=True)
    try:
        _, body = _resolve(base, [uri])
        assert body[uri] == {
            "ok": True, "axis": "work", "key": f"sub/proj/{item.slug}"}
    finally:
        httpd.shutdown()


def test_resolve_foreign_and_malformed(tmp_path):
    root = _node(tmp_path)
    httpd, base = _start(root)
    try:
        _, body = _resolve(base, ["tcw://C/nope", "tcw://garbage"])
        assert body["tcw://C/nope"] == {"ok": False}
        assert body["tcw://garbage"] == {"ok": False}
    finally:
        httpd.shutdown()


def test_resolve_caps_the_batch(tmp_path):
    root = _node(tmp_path)
    httpd, base = _start(root)
    try:
        # Over-cap payload is truncated, not hung or errored.
        uris = [f"tcw://C/x{i}" for i in range(RESOLVE_MAX_URIS + 50)]
        status, body = _resolve(base, uris)
        assert status == HTTPStatus.OK
        assert len(body) == RESOLVE_MAX_URIS
    finally:
        httpd.shutdown()


def test_resolve_rejects_non_loopback_origin(tmp_path):
    root = _node(tmp_path)
    httpd, base = _start(root)
    try:
        status, _ = _resolve(base, ["tcw://C/x"], headers={"Origin": "http://evil.test"})
        assert status == HTTPStatus.BAD_REQUEST
    finally:
        httpd.shutdown()
