"""serve --include-descendants — aggregate descendant boards + resolve qualified
slugs across the work API. Resolution is GATED on the flag: without it, serve is
byte-for-byte unchanged (a qualified slug 404s on every route, read and mutate).
"""

import json
import subprocess
import threading
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest
import yaml

from tcw.serve import HOST, TcwServer
from tcw.store.fs import FsWorkStore, init


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


def _subnode(parent: Path, rel: str) -> Path:
    d = parent / rel
    d.mkdir(parents=True)
    project_id = d.name.lower()
    init(["work"], d, project_id)
    parent_cfg = yaml.safe_load((parent / "tcw-config.yaml").read_text()) or {}
    parent_cfg.setdefault("connected-projects", {}).setdefault("children", {})[
        project_id
    ] = rel
    (parent / "tcw-config.yaml").write_text(
        yaml.safe_dump(parent_cfg, sort_keys=False)
    )
    child_cfg = yaml.safe_load((d / "tcw-config.yaml").read_text()) or {}
    child_cfg["connected-projects"] = {
        "parent": {parent_cfg["id"]: str(parent.resolve())}
    }
    (d / "tcw-config.yaml").write_text(yaml.safe_dump(child_cfg, sort_keys=False))
    return d


def _server(root: Path, include_descendants: bool):
    httpd = TcwServer((HOST, 0), root, include_descendants)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://{HOST}:{httpd.server_port}"


def _req(base: str, method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if method != "GET" else {}
    req = Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req) as res:
            raw = res.read()
            return res.status, (json.loads(raw) if raw else None)
    except HTTPError as e:
        raw = e.read()
        try:
            return e.code, (json.loads(raw) if raw else None)
        except json.JSONDecodeError:
            return e.code, None


@pytest.fixture
def tree(tmp_path):
    """Anchor with one item plus a registered descendant."""
    root = _node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    sub = _subnode(root, "project-a")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    return root, sub, slug


def test_board_flag_on_qualifies_descendant(tree):
    root, sub, slug = tree
    httpd, base = _server(root, include_descendants=True)
    try:
        status, board = _req(base, "GET", "/api/work")
        slugs = {it["slug"] for it in board}
        assert f"project-a/{slug}" in slugs               # descendant qualified
        assert "2026-01-01-root-thing" in slugs           # anchor bare
    finally:
        httpd.shutdown(); httpd.server_close()


def test_board_flag_off_is_single_node(tree):
    root, sub, slug = tree
    httpd, base = _server(root, include_descendants=False)
    try:
        status, board = _req(base, "GET", "/api/work")
        assert [it["slug"] for it in board] == ["2026-01-01-root-thing"]
    finally:
        httpd.shutdown(); httpd.server_close()


def test_detail_via_qualified_slug_flag_on(tree):
    root, sub, slug = tree
    httpd, base = _server(root, include_descendants=True)
    try:
        q = quote(f"project-a/{slug}", safe="")
        status, detail = _req(base, "GET", f"/api/work/{q}")
        assert status == HTTPStatus.OK
        # echoes the QUALIFIED slug so the UI keeps addressing the descendant
        assert detail["item"]["slug"] == f"project-a/{slug}"
    finally:
        httpd.shutdown(); httpd.server_close()


def test_mutating_action_on_descendant_flag_on(tree):
    root, sub, slug = tree
    httpd, base = _server(root, include_descendants=True)
    try:
        q = quote(f"project-a/{slug}", safe="")
        status, item = _req(base, "POST", f"/api/work/{q}/actions/start", {})
        assert status == HTTPStatus.OK
        assert item["slug"] == f"project-a/{slug}"
        assert FsWorkStore.open(sub).get(slug).status == "active"   # really moved
    finally:
        httpd.shutdown(); httpd.server_close()


def test_qualified_slug_404_when_flag_off(tree):
    """Serve unchanged without the flag: a qualified slug 404s on read AND mutate,
    and the descendant is neither read nor mutated."""
    root, sub, slug = tree
    httpd, base = _server(root, include_descendants=False)
    try:
        q = quote(f"project-a/{slug}", safe="")
        status, _ = _req(base, "GET", f"/api/work/{q}")
        assert status == HTTPStatus.NOT_FOUND
        status, _ = _req(base, "DELETE", f"/api/work/{q}")
        assert status == HTTPStatus.NOT_FOUND
        assert FsWorkStore.open(sub).get(slug) is not None          # untouched
    finally:
        httpd.shutdown(); httpd.server_close()


def test_traversal_absolute_worktrees_404_flag_on(tree):
    root, sub, slug = tree
    httpd, base = _server(root, include_descendants=True)
    try:
        for bad in (f"../escape/{slug}", f"/etc/{slug}", f".worktrees/x/{slug}"):
            q = quote(bad, safe="")
            status, _ = _req(base, "GET", f"/api/work/{q}")
            assert status == HTTPStatus.NOT_FOUND, bad
    finally:
        httpd.shutdown(); httpd.server_close()
