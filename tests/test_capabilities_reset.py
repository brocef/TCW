"""Drop/reset a local capability override → re-inherit upstream
(spec: 2026-07-16-drop-or-reset-a-local-capability-override-...)."""

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import FsCapabilitiesStore, write_sentinel
from tcw.errors import TcwError
from tests.projectfiles import write_config, write_manifest
from tests.statefiles import write_state, CAPABILITY_STATE


def repo(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root, name.replace("_", "-"))
    return root


def write_cap(root: Path, path: str, *, id=None, body="", complete=True, **meta) -> None:
    """One capability's files. `complete=False` writes an override as TCW
    4.0 keeps one (TCW-112 Design 2.2): only the fields given, with no name
    unless one is given and no `description.md` unless a body is."""
    d = root / "docs" / "capabilities" / path
    d.mkdir(parents=True, exist_ok=True)
    m = {}
    if id is not None:
        m["id"] = id
    if complete or "name" in meta:
        m["name"] = meta.pop("name", path.rsplit("/", 1)[-1].replace("-", " ").title())
    m.update(meta)
    # An override holding nothing but a description has an empty state file.
    write_state(d / CAPABILITY_STATE,
                yaml.safe_dump(m, sort_keys=False, allow_unicode=True) if m else "")
    if complete or body:
        (d / "description.md").write_text(body)


def federated(tmp_path):
    base = repo(tmp_path, "base")
    write_cap(base, "auth/login", Status="Supported", body="Log in.")
    child = repo(tmp_path, "child")
    connect(child, base)
    return base, child


def test_cli_reset_removes_the_organising_folder_it_empties(tmp_path, monkeypatch, capsys):
    """Resetting the only override under `auth/` removes `auth/` too, names
    it, and leaves validate nothing to warn about."""
    from tcw.cli import main
    base, child = federated(tmp_path)
    write_cap(child, "auth/login", complete=False, Status="Missing")
    monkeypatch.chdir(child)
    assert main(["capabilities", "reset", "auth/login"]) == 0
    assert "removed docs/capabilities/auth" in capsys.readouterr().err.splitlines()
    assert not (child / "docs" / "capabilities" / "auth").exists()
    main(["validate"])
    assert "holds no TCW object" not in "".join(capsys.readouterr())


def connect(anchor, *sources):
    """`anchor` names each source as a parent passing its capabilities, found
    through `anchor`'s manifest; the sources name nothing."""
    anchor_id = anchor.name.replace("_", "-")
    parents = "".join(
        f"- id: {source.name.replace('_', '-')}\n  inherit: [capabilities]\n"
        for source in sources
    )
    write_config(anchor, f"id: {anchor_id}\nparents:\n{parents}")
    write_manifest(anchor, {source.name.replace("_", "-"): f"../{source.name}"
                            for source in sources})


def store(root: Path) -> FsCapabilitiesStore:
    return FsCapabilitiesStore.open(root)          # reopened, so nothing is cached


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
    assert store(child).get_view("auth/login").status == "Missing"
    assert (child / "docs/capabilities/auth/login").is_dir()

    store(child).reset("auth/login")
    cap = store(child).get_view("auth/login")
    assert cap.status == "Supported"                               # re-inherited
    assert cap.origin == "base"
    assert not (child / "docs/capabilities/auth/login").exists()   # override folder gone


def test_reset_leaves_upstream_untouched(tmp_path):
    base, child = federated(tmp_path)
    store(child).set("auth/login", {"Status": "Missing"})
    before = tree_hash(base)
    store(child).reset("auth/login")
    assert tree_hash(base) == before


@pytest.mark.parametrize("ref", ["base.capabilities/auth/login",
                                 "child.capabilities/auth/login"])
def test_reset_by_a_full_identifier_drops_the_override_at_the_same_path(tmp_path, ref):
    """An override is the project's own object at the inherited path (TCW-112
    Design 2.2), so reset accepts the full identifier of what it overrides as
    well as its own, and deletes the folder at that path."""
    base, child = federated(tmp_path)
    write_cap(child, "auth/login", complete=False, Status="Missing")
    assert str(store(child).get_view("auth/login").overrides) == "base.capabilities/auth/login"
    store(child).reset(ref)
    assert not (child / "docs/capabilities/auth/login").exists()
    cap = store(child).get_view("auth/login")
    assert (cap.owner, cap.status, cap.overrides) == ("base", "Supported", None)


def test_reset_refuses_an_override_another_capability_still_names(tmp_path):
    """Once removed, the override's full identifier names nothing, so reset
    refuses while another of the project's own capabilities names it."""
    base, child = federated(tmp_path)
    write_cap(child, "auth/login", complete=False, Status="Missing")
    write_cap(child, "other", Status="Supported",
              **{"Superseded by": "child.capabilities/auth/login"})
    before = tree_hash(child)
    with pytest.raises(TcwError) as caught:
        store(child).reset("auth/login")
    message = str(caught.value)
    assert message.startswith("cannot reset 'auth/login': child.capabilities/auth/login "
                              "is still named by "), message
    assert message.endswith("; repoint each at base.capabilities/auth/login first"), message
    # TCW-112 AC 24: the referrer is named by its full identifier, with the field.
    assert "child.capabilities/other" in message and "Superseded by" in message, message
    assert tree_hash(child) == before


# ── refusals (fail closed, change nothing) ───────────────────────────────────

def test_reset_refuses_standalone_local(tmp_path):
    base, child = federated(tmp_path)
    write_cap(child, "extra", Status="Missing")
    with pytest.raises(TcwError, match="local capability"):
        store(child).reset("extra")
    assert (child / "docs/capabilities/extra").is_dir()


def test_reset_refuses_uninherited_verbatim(tmp_path):
    base, child = federated(tmp_path)                              # no override yet
    with pytest.raises(TcwError, match="no local override"):
        store(child).reset("auth/login")


def test_reset_unknown_path(tmp_path):
    base, child = federated(tmp_path)
    with pytest.raises(TcwError, match="no such capability"):
        store(child).reset("does/not/exist")


def test_reset_with_two_parents_reshows_the_nearer_one(tmp_path):
    """Two parents declaring the same path are no longer an ambiguity (TCW-112
    Design 2.5): the bare path names the one override, and reset shows the
    object the view picks again, not a guess between stores."""
    base_a = repo(tmp_path, "base_a")
    write_cap(base_a, "auth/login", Status="Supported")
    base_b = repo(tmp_path, "base_b")
    write_cap(base_b, "auth/login", Status="Missing")
    child = repo(tmp_path, "child")
    connect(child, base_a, base_b)
    inherited = store(child).get_view("auth/login")
    store(child).set("auth/login", {"Status": "Partial"})
    assert store(child).get_view("auth/login").overrides == inherited.full_id
    store(child).reset("auth/login")
    assert not (child / "docs/capabilities/auth/login").exists()
    again = store(child).get_view("auth/login")
    assert (again.full_id, again.status) == (inherited.full_id, inherited.status)
