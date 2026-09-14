"""Delete a local capability: `CapabilitiesStore.remove` and `tcw capabilities rm`
(spec: 2026-09-14-delete-a-capability-with-tcw-capabilities-rm)."""

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
    write_sentinel(root, name.replace("_", "-"))
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
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)


def connect(anchor, *sources):
    anchor_id = anchor.name.replace("_", "-")
    children = "".join(
        f"    {source.name.replace('_', '-')}: ../{source.name}\n"
        for source in sources
    )
    (anchor / "tcw-config.yaml").write_text(
        f"id: {anchor_id}\nconnected-projects:\n  children:\n{children}"
    )
    for source in sources:
        source_id = source.name.replace("_", "-")
        (source / "tcw-config.yaml").write_text(
            f"id: {source_id}\nconnected-projects:\n  parent:\n"
            f"    {anchor_id}: ../{anchor.name}\n"
        )


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


def federated(tmp_path):
    base = repo(tmp_path, "base")
    write_cap(base, "auth/login", id="cap-aaa111", Status="Supported", body="Log in.")
    child = repo(tmp_path, "child")
    connect(child, base)
    FsCapabilitiesStore.open(child).extends_add("base")
    return base, child


def _assert_nothing_removed(root: Path, before: str) -> None:
    """One property, one helper: a refused delete leaves the tree byte-identical."""
    assert tree_hash(root) == before


# ── deletes ──────────────────────────────────────────────────────────────────

def test_remove_deletes_local_capability_and_stages_it(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x00001", Status="Supported")
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    store(root).remove("x")
    assert store(root).get("x") is None
    status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                            capture_output=True, text=True, check=True).stdout
    assert "D  docs/capabilities/x/meta.yaml" in status


def test_remove_ignores_unresolvable_reference_tokens(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x00001", Status="Supported")
    write_cap(root, "y", id="cap-y00001", Status="Blocked", **{"Blocked by": "ghost/path"})
    store(root).remove("x")
    assert store(root).get("x") is None


def test_remove_succeeds_after_referrer_repointed(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "old", id="cap-old001", Status="Supported")
    write_cap(root, "new", id="cap-new001", Status="Supported")
    write_cap(root, "other", id="cap-oth001", Status="Supported",
              **{"Superseded by": "old"})
    with pytest.raises(ValueError):
        store(root).remove("old")
    store(root).set("other", {"Superseded by": "new"})
    store(root).remove("old")
    assert store(root).get("old") is None


# ── refusals (fail closed, change nothing) ───────────────────────────────────

def test_remove_unknown_path_changes_nothing(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x00001", Status="Supported")
    before = tree_hash(root)
    with pytest.raises(ValueError, match="no such capability: nope"):
        store(root).remove("nope")
    _assert_nothing_removed(root, before)


def test_remove_path_escaping_store_changes_nothing(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x00001", Status="Supported")
    outside = root / "docs" / "taxonomy" / "thing"
    outside.mkdir(parents=True)
    (outside / "meta.yaml").write_text("id: cap-out001\nname: Thing\nStatus: Supported\n")
    before = tree_hash(root)
    with pytest.raises(ValueError, match="no such capability"):
        store(root).remove("../taxonomy/thing")
    _assert_nothing_removed(root, before)
    assert (outside / "meta.yaml").is_file()


@pytest.mark.parametrize("ref", ["auth/login", "base/auth/login"])
def test_remove_inherited_refuses_bare_and_qualified(tmp_path, ref):
    base, child = federated(tmp_path)
    before_base, before_child = tree_hash(base), tree_hash(child)
    with pytest.raises(ValueError, match="cannot remove inherited capability"):
        store(child).remove(ref)
    _assert_nothing_removed(base, before_base)
    _assert_nothing_removed(child, before_child)


def test_remove_overridden_inherited_names_reset(tmp_path):
    base, child = federated(tmp_path)
    store(child).set("auth/login", {"Status": "Missing"})
    override = child / "docs" / "capabilities" / "auth" / "login"
    assert (override / "meta.yaml").is_file()
    before = tree_hash(child)
    with pytest.raises(ValueError, match="tcw capabilities reset"):
        store(child).remove("auth/login")
    _assert_nothing_removed(child, before)


def test_remove_ambiguous_bare_ref_raises(tmp_path):
    base_a = repo(tmp_path, "base_a")
    write_cap(base_a, "auth/login", id="cap-a11111", Status="Supported")
    base_b = repo(tmp_path, "base_b")
    write_cap(base_b, "auth/login", id="cap-b22222", Status="Missing")
    child = repo(tmp_path, "child")
    connect(child, base_a, base_b)
    st = FsCapabilitiesStore.open(child)
    st.extends_add("base-a")
    st.extends_add("base-b")
    before = tree_hash(child)
    with pytest.raises(AmbiguousRef):
        store(child).remove("auth/login")
    _assert_nothing_removed(child, before)


def test_remove_refuses_nested_capability(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "routes", id="cap-rou001", Status="Supported")
    write_cap(root, "routes/login", id="cap-log001", Status="Supported")
    before = tree_hash(root)
    with pytest.raises(ValueError, match="routes/login"):
        store(root).remove("routes")
    _assert_nothing_removed(root, before)
    assert store(root).get("routes") is not None
    assert store(root).get("routes/login") is not None


@pytest.mark.parametrize("ref", ["routes/", "./routes", "routes/.", "routes//"])
def test_remove_refuses_non_canonical_path_spelling(tmp_path, ref):
    """`get` resolves these spellings to the `routes` folder but reports the
    spelling back as the path, so the nested check compared against the wrong
    prefix and `git rm -rf` took `routes/login` with it."""
    root = repo(tmp_path, "solo")
    write_cap(root, "routes", id="cap-rou001", Status="Supported")
    write_cap(root, "routes/login", id="cap-log001", Status="Supported")
    before = tree_hash(root)
    with pytest.raises(ValueError, match="no such capability"):
        store(root).remove(ref)
    _assert_nothing_removed(root, before)


def test_remove_refuses_nested_override_folder(tmp_path):
    base, child = federated(tmp_path)
    write_cap(child, "auth", id="cap-aut001", Status="Supported")
    store(child).set("auth/login", {"Status": "Missing"})   # override lands at auth/login
    assert (child / "docs" / "capabilities" / "auth" / "login" / "meta.yaml").is_file()
    before = tree_hash(child)
    with pytest.raises(ValueError, match="auth/login"):
        store(child).remove("auth")
    _assert_nothing_removed(child, before)


@pytest.mark.parametrize("field, target, value", [
    ("Superseded by", "billing/old-refund", "billing/old-refund"),
    ("Blocked by", "billing/old-refund", "billing/old-refund"),
    # `set` accepts a loose spelling, because `get` resolves it.
    ("Superseded by", "billing/old-refund", "billing/old-refund/"),
    ("Blocked by", "billing/old-refund", "./billing//old-refund"),
    ("Roles", "roles/admin", ["!roles/admin"]),
    ("Roles", "roles/admin", "roles/other, roles/admin"),
    ("When", "conditions/signed-in", "conditions/signed-in"),
])
def test_remove_refuses_referenced_target(tmp_path, field, target, value):
    root = repo(tmp_path, "solo")
    write_cap(root, target, id="cap-tgt001", Status="Supported")
    write_cap(root, "roles/other", id="cap-oth001", Status="Supported")
    write_cap(root, "billing/refund", id="cap-ref001", Status="Supported", **{field: value})
    before = tree_hash(root)
    with pytest.raises(ValueError) as e:
        store(root).remove(target)
    assert f"billing/refund ({field})" in str(e.value)
    _assert_nothing_removed(root, before)
    assert store(root).get(target) is not None


def test_remove_refuses_reference_held_by_override(tmp_path):
    base, child = federated(tmp_path)
    write_cap(child, "roles/admin", id="cap-adm001", Status="Supported")
    store(child).set("auth/login", {"Roles": "roles/admin"})
    before = tree_hash(child)
    with pytest.raises(ValueError, match=r"auth/login \(Roles\)"):
        store(child).remove("roles/admin")
    _assert_nothing_removed(child, before)


# ── the command ──────────────────────────────────────────────────────────────

def test_cli_rm_removes_and_reports(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x00001", Status="Supported")
    monkeypatch.chdir(root)
    assert main(["capabilities", "rm", "x"]) == 0
    assert capsys.readouterr().out.strip() == "Removed capability x"
    assert main(["capabilities", "show", "x"]) == 1


def test_cli_rm_unknown_path(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = repo(tmp_path, "solo")
    monkeypatch.chdir(root)
    assert main(["capabilities", "rm", "nope"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "tcw capabilities rm: no such capability: nope" in err


def test_cli_rm_ambiguous(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    base_a = repo(tmp_path, "base_a")
    write_cap(base_a, "auth/login", id="cap-a11111", Status="Supported")
    base_b = repo(tmp_path, "base_b")
    write_cap(base_b, "auth/login", id="cap-b22222", Status="Missing")
    child = repo(tmp_path, "child")
    connect(child, base_a, base_b)
    st = FsCapabilitiesStore.open(child)
    st.extends_add("base-a")
    st.extends_add("base-b")
    monkeypatch.chdir(child)
    assert main(["capabilities", "rm", "auth/login"]) == 1
    assert "tcw capabilities rm: ambiguous ref 'auth/login'" in capsys.readouterr().err


def test_cli_rm_refusal_reports_referrer(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = repo(tmp_path, "solo")
    write_cap(root, "old", id="cap-old001", Status="Supported")
    write_cap(root, "other", id="cap-oth001", Status="Supported",
              **{"Superseded by": "old"})
    monkeypatch.chdir(root)
    assert main(["capabilities", "rm", "old"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("tcw capabilities rm: ")
    assert "other (Superseded by)" in err


def test_cli_help_lists_rm(capsys):
    from tcw.cli import main
    with pytest.raises(SystemExit):
        main(["capabilities", "--help"])
    assert "remove a local capability" in capsys.readouterr().out
