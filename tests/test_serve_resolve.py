"""serve POST /api/resolve — batch tcw:// resolution for the SPA."""

import json
import subprocess
import threading
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
import yaml

from tcw.serve import HOST, RESOLVE_MAX_URIS, TcwServer
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore, init


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["taxonomy", "capabilities", "work"], root, name)
    return root


def _connect(anchor: Path, child: Path) -> None:
    anchor_cfg = yaml.safe_load((anchor / "tcw-config.yaml").read_text()) or {}
    child_cfg = yaml.safe_load((child / "tcw-config.yaml").read_text()) or {}
    child_id = child_cfg["id"]
    anchor_cfg.setdefault("connected-projects", {}).setdefault("children", {})[
        child_id
    ] = str(child.resolve())
    child_cfg["connected-projects"] = {
        "parent": {anchor_cfg["id"]: str(anchor.resolve())}
    }
    (anchor / "tcw-config.yaml").write_text(yaml.safe_dump(anchor_cfg, sort_keys=False))
    (child / "tcw-config.yaml").write_text(yaml.safe_dump(child_cfg, sort_keys=False))


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
    _connect(child, base_repo)
    FsCapabilitiesStore.open(child).extends_add("base")
    httpd, base = _start(child)
    try:
        _, body = _resolve(base, ["tcw://base/C/auth/login"])
        assert body["tcw://base/C/auth/login"] == {
            "ok": True, "axis": "capabilities", "key": "base/auth/login"}
    finally:
        httpd.shutdown()


def test_resolve_descendant_work_gated(tmp_path):
    root = _node(tmp_path)
    sub = root / "sub" / "proj"
    sub.mkdir(parents=True)
    init(["work"], sub, "proj")
    _connect(root, sub)
    item = FsWorkStore.open(sub).create("Child", created="2026-01-01")
    uri = f"tcw://proj/W/{item.slug}"

    # Not aggregating descendants -> unhosted, and it says so by name.
    httpd, base = _start(root, include_descendants=False)
    try:
        _, body = _resolve(base, [uri])
        assert body[uri] == {
            "ok": False, "reason": "unhosted-project", "project": "proj"}
    finally:
        httpd.shutdown()

    # Aggregating -> resolves to the qualified key.
    httpd, base = _start(root, include_descendants=True)
    try:
        _, body = _resolve(base, [uri])
        assert body[uri] == {
            "ok": True, "axis": "work", "key": f"proj/{item.slug}"}
    finally:
        httpd.shutdown()


def test_resolve_ancestor_work_is_unhosted(tmp_path):
    """A child's viewer resolves an upward link in the graph but cannot open it —
    it aggregates descendants, never ancestors — so /api/resolve reports ok:false
    rather than handing the SPA a key that dead-ends. Both spellings, since that
    is precisely the pair that used to diverge."""
    root = _node(tmp_path, "root")
    child = _node(tmp_path, "child")
    _connect(root, child)
    epic = FsWorkStore.open(root).create("Parent epic", created="2026-01-01")
    unhosted = {"ok": False, "reason": "unhosted-project", "project": "root"}
    for aggregating in (False, True):
        httpd, base = _start(child, include_descendants=aggregating)
        try:
            _, body = _resolve(base, [
                f"tcw://W/root/{epic.slug}", f"tcw://root/W/{epic.slug}"])
            assert body[f"tcw://W/root/{epic.slug}"] == unhosted
            assert body[f"tcw://root/W/{epic.slug}"] == unhosted
        finally:
            httpd.shutdown()


def test_resolve_foreign_and_malformed(tmp_path):
    root = _node(tmp_path)
    httpd, base = _start(root)
    try:
        _, body = _resolve(base, [
            "tcw://C/nope", "tcw://garbage", "tcw://W/ghost/2026-01-01-x"])
        assert body["tcw://C/nope"] == {
            "ok": False, "reason": "unresolved", "detail": "no capability: nope"}
        assert body["tcw://garbage"] == {
            "ok": False, "reason": "unresolved", "detail": "malformed tcw:// uri"}
        assert body["tcw://W/ghost/2026-01-01-x"] == {
            "ok": False, "reason": "unresolved",
            "detail": "no such project in this graph: ghost"}
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


def test_resolve_failure_objects_share_one_shape(tmp_path):
    """Every failure carries a `reason` from a closed two-value set, and the
    field that goes with it: `project` for an unhosted destination, `detail` for
    an unresolved one. The SPA branches on `reason`, so an object that carries
    neither — or both — would leave it guessing."""
    root = _node(tmp_path, "root")
    child = _node(tmp_path, "child")
    _connect(root, child)
    epic = FsWorkStore.open(root).create("Parent epic", created="2026-01-01")
    httpd, base = _start(child)
    try:
        _, body = _resolve(base, [
            f"tcw://W/root/{epic.slug}",          # valid, not on this board
            "tcw://garbage",                       # malformed
            "tcw://C/nope",                        # dangling
            "tcw://W/ghost/2026-01-01-x",          # unregistered project
        ])
        assert len(body) == 4
        for uri, obj in body.items():
            assert obj["ok"] is False, uri
            assert obj["reason"] in ("unhosted-project", "unresolved"), uri
            if obj["reason"] == "unhosted-project":
                assert obj["project"], uri
                assert "detail" not in obj, uri
            else:
                assert obj["detail"], uri
                assert "project" not in obj, uri
    finally:
        httpd.shutdown()


def test_resolve_does_not_read_the_graph_for_a_batch_with_no_foreign_ref(tmp_path):
    """The hosted-projects snapshot is taken on the first foreign ref, not up
    front. A batch of purely local, malformed, or dangling refs must neither pay
    for the descendant walk nor be able to fail on it — an unreadable graph is
    not a reason for `tcw://garbage` to stop being classifiable."""
    root = _node(tmp_path)
    sub = root / "sub" / "proj"
    sub.mkdir(parents=True)
    init(["work"], sub, "proj")
    _connect(root, sub)
    item = FsWorkStore.open(root).create("Local", created="2026-01-01")
    httpd, base = _start(root, include_descendants=True)
    calls = []
    handler = httpd.RequestHandlerClass
    real = handler._hosted_projects

    def counting(self):
        calls.append(1)
        return real(self)

    handler._hosted_projects = counting
    try:
        status, body = _resolve(base, [])
        assert status == HTTPStatus.OK and body == {}
        assert calls == []                       # empty batch: no walk

        _, body = _resolve(base, ["tcw://garbage", "tcw://C/nope",
                                  f"tcw://W/{item.slug}"])
        assert body["tcw://garbage"]["reason"] == "unresolved"
        assert body[f"tcw://W/{item.slug}"]["ok"] is True
        assert calls == []                       # no foreign ref: still no walk

        uri = f"tcw://proj/W/{FsWorkStore.open(sub).create('C', created='2026-01-01').slug}"
        _, body = _resolve(base, [uri, uri, uri])
        assert body[uri]["ok"] is True
        assert len(calls) == 1                   # three foreign refs, one walk
    finally:
        handler._hosted_projects = real
        httpd.shutdown()


def test_resolve_archived_work_is_inert_and_says_why(tmp_path):
    """A reference to finished work is sound but has nothing to navigate to: the
    item's documents left the tracked tree when it was resolved. So it is
    reported the way an off-board target is — `ok: false` with a reason, which is
    what makes the SPA neutralize the anchor instead of writing a link that 404s
    — rather than as a broken reference, which is what it looked like before the
    graveyard existed.

    `detail` rather than a bare reason: the SPA's fallback branch renders any
    unrecognized reason inert with `detail` as the tooltip, so this reads
    correctly on a client that knows nothing about archived work.
    """
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create_work("A finished thing").item.slug
    st.start(slug, owner="t")
    st.complete(slug, "done", [])
    import shutil
    shutil.rmtree(root / "docs" / "work" / "completed" / slug, ignore_errors=True)
    uri = f"tcw://W/{slug}"

    httpd, base = _start(root)
    try:
        _, body = _resolve(base, [uri])
        assert body[uri]["ok"] is False
        assert body[uri]["reason"] == "archived"
        assert body[uri]["resolution"] == "done"
        assert slug in body[uri]["detail"]
    finally:
        httpd.shutdown()


def test_resolve_a_slug_that_never_existed_is_still_unresolved(tmp_path):
    """The distinction, at the viewer boundary too."""
    root = _node(tmp_path)
    httpd, base = _start(root)
    try:
        uri = "tcw://W/2026-01-01-never-created"
        _, body = _resolve(base, [uri])
        assert body[uri]["ok"] is False
        assert body[uri]["reason"] == "unresolved"
    finally:
        httpd.shutdown()
