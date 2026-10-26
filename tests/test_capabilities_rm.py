"""Delete a local capability: `CapabilitiesStore.remove` and `tcw capabilities rm`
(spec: 2026-09-14-delete-a-capability-with-tcw-capabilities-rm)."""

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.ids import FullId
from tcw.store.fs import FsCapabilitiesStore, write_sentinel
from tcw.errors import TcwError
from tests.fullids import fid
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


def S(path: str) -> str:
    """A capability of the project `solo`, as a record stores it (TCW-110)."""
    return fid("solo", "capabilities", path)


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
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)


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
    write_cap(base, "auth/login", Status="Supported", body="Log in.")
    child = repo(tmp_path, "child")
    connect(child, base)
    return base, child


def _assert_nothing_removed(root: Path, before: str) -> None:
    """One property, one helper: a refused delete leaves the tree byte-identical."""
    assert tree_hash(root) == before


# ── deletes ──────────────────────────────────────────────────────────────────

def test_remove_deletes_local_capability_and_stages_nothing(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Supported")
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    store(root).remove("x")
    assert store(root).get_view("x") is None
    status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                            capture_output=True, text=True, check=True).stdout
    assert " D docs/capabilities/x/tcw-capability.yaml" in status        # deleted, not staged


def test_remove_ignores_unresolvable_reference_tokens(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Supported")
    write_cap(root, "y", Status="Blocked", **{"Blocked by": S("ghost/path")})
    store(root).remove("x")
    assert store(root).get_view("x") is None


def test_remove_succeeds_after_referrer_repointed(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "old", Status="Supported")
    write_cap(root, "new", Status="Supported")
    write_cap(root, "other", Status="Supported",
              **{"Superseded by": S("old")})
    with pytest.raises(TcwError):
        store(root).remove("old")
    store(root).set("other", {"Superseded by": "new"})
    store(root).remove("old")
    assert store(root).get_view("old") is None


# ── refusals (fail closed, change nothing) ───────────────────────────────────

def test_remove_unknown_path_changes_nothing(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Supported")
    before = tree_hash(root)
    with pytest.raises(TcwError, match="no such capability: nope"):
        store(root).remove("nope")
    _assert_nothing_removed(root, before)


def test_remove_path_escaping_store_changes_nothing(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Supported")
    outside = root / "docs" / "taxonomy" / "thing"
    outside.mkdir(parents=True)
    write_state(outside / CAPABILITY_STATE, "name: Thing\nStatus: Supported\n")
    before = tree_hash(root)
    with pytest.raises(TcwError, match="is not a full identifier"):
        store(root).remove("../taxonomy/thing")
    _assert_nothing_removed(root, before)
    assert (outside / CAPABILITY_STATE).is_file()


@pytest.mark.parametrize("ref", ["auth/login", "base.capabilities/auth/login"])
def test_remove_inherited_refuses_bare_and_qualified(tmp_path, ref):
    base, child = federated(tmp_path)
    before_base, before_child = tree_hash(base), tree_hash(child)
    with pytest.raises(TcwError, match="^base.capabilities/auth/login belongs to "
                                       "project 'base'; run the command there: tcw -C "):
        store(child).remove(ref)
    _assert_nothing_removed(base, before_base)
    _assert_nothing_removed(child, before_child)


def test_remove_deletes_an_override_and_the_path_shows_the_inherited_one(tmp_path):
    """`rm` removes any of the project's own objects, an override included
    (TCW-112 Design 4.4), so the path shows the inherited capability again."""
    base, child = federated(tmp_path)
    store(child).set("auth/login", {"Status": "Missing"})
    override = child / "docs" / "capabilities" / "auth" / "login"
    assert (override / CAPABILITY_STATE).is_file()
    before_base = tree_hash(base)
    store(child).remove("auth/login")
    assert not override.exists()
    cap = store(child).get_view("auth/login")
    assert (str(cap.full_id), cap.status) == ("base.capabilities/auth/login", "Supported")
    _assert_nothing_removed(base, before_base)


def test_remove_of_a_path_two_parents_declare_names_the_one_the_view_shows(tmp_path):
    """Two parents declaring one path are no longer ambiguous (TCW-112 Design
    3.6): the bare path names the object the view shows, which is another
    project's, so `rm` refuses naming that project, and removes nothing."""
    base_a = repo(tmp_path, "base_a")
    write_cap(base_a, "auth/login", Status="Supported")
    base_b = repo(tmp_path, "base_b")
    write_cap(base_b, "auth/login", Status="Missing")
    child = repo(tmp_path, "child")
    connect(child, base_a, base_b)
    shown = store(child).get_view("auth/login")
    before = tree_hash(child)
    with pytest.raises(TcwError) as caught:
        store(child).remove("auth/login")
    assert str(caught.value) == (f"{shown.full_id} belongs to project '{shown.owner}'; "
                                 f"run the command there: tcw -C {base_b.resolve()} …")
    _assert_nothing_removed(child, before)


def test_remove_refuses_nested_capability(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "routes", Status="Supported")
    write_cap(root, "routes/login", Status="Supported")
    before = tree_hash(root)
    with pytest.raises(TcwError, match="routes/login"):
        store(root).remove("routes")
    _assert_nothing_removed(root, before)
    assert store(root).get_view("routes") is not None
    assert store(root).get_view("routes/login") is not None


def test_remove_refuses_capability_nested_in_a_dot_directory(tmp_path):
    """`_object_dirs` (the walk) skips dot-directories, but `git rm -rf` does not."""
    root = repo(tmp_path, "solo")
    write_cap(root, "routes", Status="Supported")
    write_cap(root, "routes/.drafts/login", Status="Supported")
    before = tree_hash(root)
    with pytest.raises(TcwError, match=r"routes/\.drafts/login"):
        store(root).remove("routes")
    _assert_nothing_removed(root, before)


def test_remove_treats_a_glob_character_in_the_path_literally(tmp_path):
    """A path is a git pathspec to `git rm`, where `a*` also matches `abc`."""
    root = repo(tmp_path, "solo")
    write_cap(root, "a*", Status="Supported")
    write_cap(root, "abc", Status="Supported")
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    # The name breaks the identifier rule, so only a full identifier built in
    # code names it; a command refuses the text (TCW-110 Design 1.6).
    store(root).remove(FullId("solo", "capabilities", "a*"))
    assert store(root).get_view("a*") is None
    assert store(root).get_view("abc") is not None
    assert (root / "docs" / "capabilities" / "abc" / CAPABILITY_STATE).is_file()


def test_remove_skips_a_folder_that_vanished_after_listing(tmp_path, monkeypatch):
    """The listing and the identity comparison are not atomic; a folder gone in
    between is no referrer, not a traceback."""
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Supported")
    st = store(root)
    listed = st._object_dirs()
    monkeypatch.setattr(st, "_object_dirs", lambda: [*listed, "gone/away"])
    st.remove("x")
    assert store(root).get_view("x") is None


def test_remove_does_not_proceed_when_comparing_folders_fails_for_another_reason(
        tmp_path, monkeypatch):
    """Only a missing folder means "not the target". Any other read error leaves
    the question unanswered, so the delete must not go ahead."""
    root = repo(tmp_path, "solo")
    write_cap(root, "old", Status="Supported")
    write_cap(root, "other", Status="Supported",
              **{"Superseded by": S("old")})
    before = tree_hash(root)

    def refuse(self, other):
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "samefile", refuse)
    with pytest.raises(PermissionError):
        store(root).remove("old")
    monkeypatch.undo()
    _assert_nothing_removed(root, before)
    assert store(root).get_view("old") is not None


def test_remove_nested_check_respects_the_path_boundary(tmp_path):
    """`routes-v2` is a sibling of `routes`, not nested under it."""
    root = repo(tmp_path, "solo")
    write_cap(root, "routes", Status="Supported")
    write_cap(root, "routes-v2", Status="Supported")
    store(root).remove("routes")
    assert store(root).get_view("routes") is None
    assert store(root).get_view("routes-v2") is not None


@pytest.mark.parametrize("ref", ["routes/", "./routes", "routes/.", "routes//", "Routes",
                                 "routes/login/.."])
def test_remove_refuses_non_canonical_path_spelling(tmp_path, ref):
    """`get` resolved these spellings to the `routes` folder but reported the
    spelling back as the path, so the nested check compared against the wrong
    prefix and `git rm -rf` took `routes/login` with it. Since TCW-110 the
    letter case is not found and the rest break the identifier rule."""
    root = repo(tmp_path, "solo")
    write_cap(root, "routes", Status="Supported")
    write_cap(root, "routes/login", Status="Supported")
    before = tree_hash(root)
    with pytest.raises(TcwError, match="no such capability|names no capability|"
                                       "is not a full identifier"):
        store(root).remove(ref)
    _assert_nothing_removed(root, before)


def test_remove_refuses_nested_override_folder(tmp_path):
    base, child = federated(tmp_path)
    write_cap(child, "auth", Status="Supported")
    store(child).set("auth/login", {"Status": "Missing"})   # override lands at auth/login
    assert (child / "docs" / "capabilities" / "auth" / "login" / CAPABILITY_STATE).is_file()
    before = tree_hash(child)
    with pytest.raises(TcwError, match="auth/login"):
        store(child).remove("auth")
    _assert_nothing_removed(child, before)


@pytest.mark.parametrize("field, target, value", [
    ("Superseded by", "billing/old-refund", S("billing/old-refund")),
    ("Blocked by", "billing/old-refund", S("billing/old-refund")),
    ("Roles", "roles/admin", [f"!{S('roles/admin')}"]),
    ("Roles", "roles/admin", f"{S('roles/other')}, {S('roles/admin')}"),
    ("When", "conditions/signed-in", S("conditions/signed-in")),
])
def test_remove_refuses_referenced_target(tmp_path, field, target, value):
    root = repo(tmp_path, "solo")
    write_cap(root, target, Status="Supported")
    write_cap(root, "roles/other", Status="Supported")
    write_cap(root, "billing/refund", Status="Supported", **{field: value})
    before = tree_hash(root)
    with pytest.raises(TcwError) as e:
        store(root).remove(target)
    assert f"solo.capabilities/billing/refund ({field})" in str(e.value)
    _assert_nothing_removed(root, before)
    assert store(root).get_view(target) is not None


@pytest.mark.parametrize("field, value", [
    ("Superseded by", f" {S('roles/admin')} "),  # check reads the value as written
    ("Blocked by", f"!{S('roles/admin')}"),     # `!` negates only in Roles/When
    ("Blocked by", [S("roles/admin")]),         # a list is not a single identifier
    ("When", S("roles/admin")),                 # When tokens must be conditions/
    ("Roles", S("conditions/roles/admin")),
    ("Superseded by", "roles/admin"),           # a 3.x value names nothing
])
def test_remove_ignores_a_value_check_does_not_resolve_to_the_target(tmp_path, field, value):
    """`_referrers` reads each field exactly as `check` does, so a value `check`
    already reports as broken does not also block the delete."""
    root = repo(tmp_path, "solo")
    write_cap(root, "roles/admin", Status="Supported")
    write_cap(root, "billing/refund", Status="Supported", **{field: value})
    store(root).remove("roles/admin")
    assert store(root).get_view("roles/admin") is None


def test_gate_removed_ignores_an_inherited_capability_at_the_same_path(tmp_path):
    """After a local `auth/login` is deleted, the bare path falls through to the
    inherited one, which `rm` refuses — so only a local hit may fail the gate."""
    from tcw.store.fs import FsWorkStore, init
    from tcw.work.recursion import capability_gate
    base, child = federated(tmp_path)
    init(["work"], child)
    ws = FsWorkStore.open(child)
    slug = ws.create("Task", created="2026-01-01").slug
    (ws.path(slug) / "capabilities.yaml").write_text("removed:\n  - child.capabilities/auth/login\n")
    assert capability_gate(ws, ws.get(slug)) == []
    write_cap(child, "auth/login", Status="Supported")
    problems = capability_gate(ws, ws.get(slug))
    assert len(problems) == 1 and "declared (removed) but still resolves" in problems[0]


def test_remove_refuses_reference_held_by_override(tmp_path):
    base, child = federated(tmp_path)
    write_cap(child, "roles/admin", Status="Supported")
    store(child).set("auth/login", {"Roles": "roles/admin"})
    before = tree_hash(child)
    with pytest.raises(TcwError, match=r"auth/login \(Roles\)"):
        store(child).remove("roles/admin")
    _assert_nothing_removed(child, before)


# ── the command ──────────────────────────────────────────────────────────────

def test_cli_rm_removes_and_reports(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Supported")
    monkeypatch.chdir(root)
    assert main(["capabilities", "rm", "x"]) == 0
    printed = capsys.readouterr()
    assert printed.out == ""
    assert "removed docs/capabilities/x/tcw-capability.yaml" in printed.err.splitlines()
    assert main(["capabilities", "show", "x"]) == 4


def test_cli_rm_unknown_path(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = repo(tmp_path, "solo")
    monkeypatch.chdir(root)
    assert main(["capabilities", "rm", "nope"]) == 4
    out, err = capsys.readouterr()
    assert out == ""
    assert "tcw capabilities rm: no such capability: nope" in err


def test_cli_rm_of_an_override_says_what_the_path_now_shows(tmp_path, monkeypatch, capsys):
    """TCW-112 AC 25: removing an override names, on standard error, the
    object its path shows afterwards."""
    from tcw.cli import main
    base, child = federated(tmp_path)
    write_cap(child, "auth/login", complete=False, Status="Missing")
    monkeypatch.chdir(child)
    assert main(["capabilities", "rm", "auth/login"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert "auth/login now shows base.capabilities/auth/login" in err.splitlines()
    assert not (child / "docs" / "capabilities" / "auth" / "login").exists()


def test_cli_rm_of_another_projects_capability_is_refused(tmp_path, monkeypatch, capsys):
    """TCW-112 AC 25: `rm` of another project's full identifier exits 3 and
    removes nothing."""
    from tcw.cli import main
    base, child = federated(tmp_path)
    before_base, before_child = tree_hash(base), tree_hash(child)
    monkeypatch.chdir(child)
    assert main(["capabilities", "rm", "base.capabilities/auth/login"]) == 3
    err = capsys.readouterr().err
    assert err.startswith("tcw capabilities rm: ")
    assert "belongs to project 'base'" in err
    _assert_nothing_removed(base, before_base)
    _assert_nothing_removed(child, before_child)
    assert main(["capabilities", "show", "base.capabilities/auth/login"]) == 0


def test_cli_rm_refusal_reports_referrer(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = repo(tmp_path, "solo")
    write_cap(root, "old", Status="Supported")
    write_cap(root, "other", Status="Supported",
              **{"Superseded by": S("old")})
    monkeypatch.chdir(root)
    assert main(["capabilities", "rm", "old"]) == 3
    err = capsys.readouterr().err
    assert err.startswith("tcw capabilities rm: ")
    assert "other (Superseded by)" in err


def test_cli_help_lists_rm(capsys):
    from tcw.cli import main
    with pytest.raises(SystemExit):
        main(["capabilities", "--help"])
    assert "remove a local capability" in capsys.readouterr().out
