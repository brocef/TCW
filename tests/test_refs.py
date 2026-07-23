"""tcw:// reference grammar (parse) + resolution (resolve).

`parse_tcw_uri` is a pure total function (never raises); `resolve_tcw_ref` is
thin adapter glue over the existing FS stores that never propagates a store
exception to a link-scanning caller.
"""

import subprocess
import yaml
from pathlib import Path

from tcw.refs import TcwRef, parse_tcw_uri, resolve_tcw_ref
from tcw.store.fs import (
    FsCapabilitiesStore,
    FsTaxonomyStore,
    FsWorkStore,
    init,
)


# ── parse: grammar round-trips ────────────────────────────────────────────────

def test_parse_local_capability():
    assert parse_tcw_uri("tcw://C/auth/login") == TcwRef("", "C", "auth/login")


def test_parse_namespaced_capability():
    assert parse_tcw_uri("tcw://shared/C/auth/providers/github") == TcwRef(
        "shared", "C", "auth/providers/github")


def test_parse_local_work():
    assert parse_tcw_uri("tcw://W/2026-01-01-x") == TcwRef("", "W", "2026-01-01-x")


def test_parse_taxonomy():
    assert parse_tcw_uri("tcw://T/domain/term") == TcwRef("", "T", "domain/term")


def test_parse_axis_case_insensitive_normalizes_upper():
    assert parse_tcw_uri("tcw://c/auth").axis == "C"


def test_parse_namespaced_work():
    assert parse_tcw_uri("tcw://sub/proj/W/2026-01-01-x") == TcwRef(
        "sub/proj", "W", "2026-01-01-x")


# ── parse: rejections (returns None, never raises) ────────────────────────────

def test_parse_requires_scheme():
    assert parse_tcw_uri("C/auth/login") is None
    assert parse_tcw_uri("http://C/auth") is None


def test_parse_missing_axis():
    assert parse_tcw_uri("tcw://foo/bar/baz") is None


def test_parse_empty_ref():
    assert parse_tcw_uri("tcw://C") is None
    assert parse_tcw_uri("tcw://C/") is None
    assert parse_tcw_uri("tcw://shared/C") is None


def test_parse_rejects_ref_traversal():
    assert parse_tcw_uri("tcw://C/../etc/passwd") is None


def test_parse_rejects_namespace_traversal():
    assert parse_tcw_uri("tcw://../evil/C/x") is None


def test_parse_rejects_control_char():
    assert parse_tcw_uri("tcw://C/a\x00b") is None
    assert parse_tcw_uri("tcw://C/a\x01b") is None


# ── parse: documented collision + slash handling ──────────────────────────────

def test_parse_first_bare_axis_wins():
    # tcw://T/C/ref — the first bare T/C/W segment is the axis (documented limit).
    assert parse_tcw_uri("tcw://T/C/ref") == TcwRef("", "T", "C/ref")


def test_parse_collapses_multiple_slashes():
    assert parse_tcw_uri("tcw://C//auth/login") == TcwRef("", "C", "auth/login")


def test_parse_splits_before_percent_decode():
    # %2F inside a segment stays inside it — it can't inject a separator/axis.
    assert parse_tcw_uri("tcw://C/auth%2Flogin") == TcwRef("", "C", "auth/login")


# ── resolve fixtures ──────────────────────────────────────────────────────────

def node(tmp_path: Path, name: str = "repo", components=("taxonomy", "capabilities", "work")) -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(list(components), root, name)
    return root


def subnode(parent: Path, rel: str) -> Path:
    d = parent / rel
    d.mkdir(parents=True)
    project_id = d.name
    init(["work"], d, project_id)
    connect(parent, d)
    return d


def connect(anchor: Path, *others: Path) -> None:
    anchor_cfg = yaml.safe_load((anchor / "tcw-config.yaml").read_text()) or {}
    for other in others:
        other_id = (yaml.safe_load((other / "tcw-config.yaml").read_text()) or {})["id"]
        anchor_cfg.setdefault("connected-projects", {}).setdefault("children", {})[
            other_id
        ] = str(other.resolve())
        other_cfg = yaml.safe_load((other / "tcw-config.yaml").read_text()) or {}
        other_cfg["connected-projects"] = {
            "parent": {anchor_cfg["id"]: str(anchor.resolve())}
        }
        (other / "tcw-config.yaml").write_text(
            yaml.safe_dump(other_cfg, sort_keys=False)
        )
    (anchor / "tcw-config.yaml").write_text(
        yaml.safe_dump(anchor_cfg, sort_keys=False)
    )


# ── resolve: local ────────────────────────────────────────────────────────────

def test_resolve_local_taxonomy(tmp_path):
    root = node(tmp_path)
    FsTaxonomyStore.open(root).add("Login", slug="auth")
    r = resolve_tcw_ref(root, "tcw://T/auth")
    assert r.ok and r.axis == "T" and r.key == "auth"


def test_resolve_local_capability(tmp_path):
    root = node(tmp_path)
    FsCapabilitiesStore.open(root).add("auth/login", name="Sign in")
    r = resolve_tcw_ref(root, "tcw://C/auth/login")
    assert r.ok and r.axis == "C" and r.key == "auth/login"


def test_resolve_local_work(tmp_path):
    root = node(tmp_path)
    item = FsWorkStore.open(root).create("A task", created="2026-01-01")
    r = resolve_tcw_ref(root, f"tcw://W/{item.slug}")
    assert r.ok and r.axis == "W" and r.key == item.slug


# ── resolve: federation (extends alias) ───────────────────────────────────────

def test_resolve_federated_capability(tmp_path):
    base = node(tmp_path, "base")
    FsCapabilitiesStore.open(base).add("auth/login", name="Sign in")
    child = node(tmp_path, "child")
    connect(child, base)
    FsCapabilitiesStore.open(child).extends_add("base")
    r = resolve_tcw_ref(child, "tcw://base/C/auth/login")
    assert r.ok and r.key == "base/auth/login"


# ── resolve: foreign work (resolves in the graph; hosting is the viewer's call) ─

def test_resolve_foreign_work_resolves_and_reports_project(tmp_path):
    """Both spellings of a foreign work ref resolve and carry the owning project.

    `parse_tcw_uri` reads `tcw://<id>/W/<slug>` with a parsed namespace and
    `tcw://W/<id>/<slug>` as a bare ref whose qualifier is a project id; both must
    land on the same qualified key and expose `project`, so the SPA can gate on
    whether it hosts that project.
    """
    root = node(tmp_path)
    sub = subnode(root, "sub/proj")
    item = FsWorkStore.open(sub).create("Child task", created="2026-01-01")
    for uri in (f"tcw://proj/W/{item.slug}", f"tcw://W/proj/{item.slug}"):
        r = resolve_tcw_ref(root, uri)
        assert r.ok and r.axis == "W" and r.key == f"proj/{item.slug}"
        assert r.project == "proj"


def test_resolve_local_work_reports_no_project(tmp_path):
    root = node(tmp_path)
    item = FsWorkStore.open(root).create("Local", created="2026-01-01")
    r = resolve_tcw_ref(root, f"tcw://W/{item.slug}")
    assert r.ok and r.key == item.slug and r.project == ""


def test_resolve_parent_work_from_child(tmp_path):
    """The cross-node epic back-link: a child slice points at the parent's epic
    (GitHub issue #7). Resolves upward, and marks the parent as the owning project.
    """
    root = node(tmp_path)
    sub = subnode(root, "proj")
    epic = FsWorkStore.open(root).create("Parent epic", created="2026-01-01")
    r = resolve_tcw_ref(sub, f"tcw://W/repo/{epic.slug}")
    assert r.ok and r.axis == "W" and r.project == "repo"


def test_resolve_unregistered_project_names_the_cause(tmp_path):
    root = node(tmp_path)
    r = resolve_tcw_ref(root, "tcw://W/ghost/2026-01-01-x")
    assert r.ok is False and r.reason == "no such project in this graph: ghost"


# ── resolve: failure modes (never raises) ─────────────────────────────────────

def test_resolve_dangling_capability(tmp_path):
    root = node(tmp_path)
    r = resolve_tcw_ref(root, "tcw://C/nope")
    assert r.ok is False and r.reason


def test_resolve_malformed_uri(tmp_path):
    root = node(tmp_path)
    r = resolve_tcw_ref(root, "tcw://foo/bar")
    assert r.ok is False and r.reason


def test_resolve_foreign_namespace_capability(tmp_path):
    root = node(tmp_path)
    r = resolve_tcw_ref(root, "tcw://missing/C/auth")
    assert r.ok is False and r.reason


def test_resolve_ambiguous_does_not_raise(tmp_path):
    # Two extends aliases with the same bare ref -> AmbiguousRef, swallowed.
    base_a = node(tmp_path, "a")
    FsCapabilitiesStore.open(base_a).add("dup", name="A dup")
    base_b = node(tmp_path, "b")
    FsCapabilitiesStore.open(base_b).add("dup", name="B dup")
    child = node(tmp_path, "child")
    connect(child, base_a, base_b)
    st = FsCapabilitiesStore.open(child)
    st.extends_add("a")
    st.extends_add("b")
    r = resolve_tcw_ref(child, "tcw://C/dup")   # bare, matches both aliases
    assert r.ok is False and r.reason
