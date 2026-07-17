"""Drop/reset a local capability override → re-inherit upstream
(spec: 2026-07-16-drop-or-reset-a-local-capability-override-...)."""

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import AmbiguousRef
from tcw.store.fs import FsCapabilitiesStore, write_sentinel


def repo(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root)
    return root


def write_cap(root: Path, path: str, *, id=None, body="", **meta) -> None:
    d = root / "docs" / "capabilities" / path
    d.mkdir(parents=True, exist_ok=True)
    m = {}
    if id is not None:
        m["id"] = id
    m["name"] = meta.pop("name", path.rsplit("/", 1)[-1].replace("-", " ").title())
    m.update(meta)
    (d / "meta.yaml").write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True))
    (d / "description.md").write_text(body)


def federated(tmp_path):
    base = repo(tmp_path, "base")
    write_cap(base, "auth/login", id="cap-aaa111", Status="Supported", body="Log in.")
    child = repo(tmp_path, "child")
    FsCapabilitiesStore.open(child).extends_add("shared", "../base")
    return base, child


def store(root: Path) -> FsCapabilitiesStore:
    return FsCapabilitiesStore.open(root)          # reopen so extends resolves


def tree_hash(root: Path) -> str:
    caps = root / "docs" / "capabilities"
    h = hashlib.sha256()
    for f in sorted(caps.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(caps)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


# ── happy path ───────────────────────────────────────────────────────────────

def test_reset_drops_override_and_reinherits(tmp_path):
    base, child = federated(tmp_path)
    store(child).set("auth/login", {"Status": "Missing"})          # create override
    assert store(child).get("auth/login").status == "Missing"
    assert (child / "docs/capabilities/auth/login").is_dir()

    store(child).reset("auth/login")
    cap = store(child).get("auth/login")
    assert cap.status == "Supported"                               # re-inherited
    assert cap.origin == "shared"
    assert not (child / "docs/capabilities/auth/login").exists()   # override folder gone


def test_reset_leaves_upstream_untouched(tmp_path):
    base, child = federated(tmp_path)
    store(child).set("auth/login", {"Status": "Missing"})
    before = tree_hash(base)
    store(child).reset("auth/login")
    assert tree_hash(base) == before


def test_reset_qualified_placement_variant(tmp_path):
    """An override can live at the alias-qualified folder; reset finds it by id."""
    base, child = federated(tmp_path)
    write_cap(child, "auth/login", id="cap-loc999", Status="Missing")   # local shadow at bare path
    store(child).set("shared/auth/login", {"Status": "Partial"})        # override → qualified folder
    assert (child / "docs/capabilities/shared/auth/login").is_dir()
    store(child).reset("shared/auth/login")
    assert not (child / "docs/capabilities/shared/auth/login").exists()
    assert store(child).get("shared/auth/login").status == "Supported"  # re-inherited
    assert (child / "docs/capabilities/auth/login").is_dir()            # local shadow untouched


# ── refusals (fail closed, change nothing) ───────────────────────────────────

def test_reset_refuses_standalone_local(tmp_path):
    base, child = federated(tmp_path)
    write_cap(child, "extra", id="cap-loc001", Status="Missing")
    with pytest.raises(ValueError, match="local capability"):
        store(child).reset("extra")
    assert (child / "docs/capabilities/extra").is_dir()


def test_reset_refuses_uninherited_verbatim(tmp_path):
    base, child = federated(tmp_path)                              # no override yet
    with pytest.raises(ValueError, match="no local override"):
        store(child).reset("auth/login")


def test_reset_unknown_path(tmp_path):
    base, child = federated(tmp_path)
    with pytest.raises(ValueError, match="no such capability"):
        store(child).reset("does/not/exist")


def test_reset_ambiguous_ref(tmp_path):
    """A bare ref matching two extended stores raises AmbiguousRef (not a silent
    wrong-store reset)."""
    base_a = repo(tmp_path, "base_a")
    write_cap(base_a, "auth/login", id="cap-a11111", Status="Supported")
    base_b = repo(tmp_path, "base_b")
    write_cap(base_b, "auth/login", id="cap-b22222", Status="Missing")
    child = repo(tmp_path, "child")
    st = FsCapabilitiesStore.open(child)
    st.extends_add("a", "../base_a")
    st.extends_add("b", "../base_b")
    with pytest.raises(AmbiguousRef):
        store(child).reset("auth/login")           # bare ref matches both
