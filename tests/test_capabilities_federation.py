"""Capability inheritance (TCW-112): parent links, overrides at the same
path, and body composition."""

import subprocess
from pathlib import Path

import pytest
import yaml

from nodeconfig import declare_extends
from tcw.locate import find_tree
from tcw.store.fs import FsCapabilitiesStore, write_sentinel
from tcw.errors import InheritedUnavailable, TcwError
from tests.projectfiles import write_config, write_manifest
from tests.statefiles import CAPABILITY_STATE, read_state, write_state


def repo(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root, name)
    return root


def write_cap(root: Path, path: str, *, id=None, body="", docs=None, complete=True,
              **meta) -> None:
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
    for fn, text in (docs or {}).items():
        (d / fn).parent.mkdir(parents=True, exist_ok=True)
        (d / fn).write_text(text)


def child_of(tmp_path, base_caps: dict) -> tuple[Path, Path]:
    """Return (base, child) where child names base as a parent, inheriting
    everything from it."""
    base = repo(tmp_path, "base")
    for path, kw in base_caps.items():
        write_cap(base, path, **kw)
    child = repo(tmp_path, "child")
    write_config(base, "id: base\nchildren:\n- child\n")
    write_manifest(base, {"child": "../child"})
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    return base, child


def store(root: Path) -> FsCapabilitiesStore:
    return FsCapabilitiesStore.open(root)         # reopened, so nothing is cached


def connect_many(anchor: Path, *sources: Path) -> None:
    """`anchor` names each source as a parent passing its capabilities, found
    in the folder next to it through `anchor`'s manifest; the sources name
    nothing."""
    parents = "".join(f"- id: {p.name}\n  inherit: [capabilities]\n" for p in sources)
    write_config(anchor, f"id: {anchor.name}\nparents:\n{parents}")
    write_manifest(anchor, {p.name: f"../{p.name}" for p in sources})


# ── inheritance (read-through) ───────────────────────────────────────────────

def test_inherited_listed_with_origin(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported", "body": "Log in."}})
    caps = {str(c.full_id): c for c in store(child).list_all()}
    assert "base.capabilities/auth/login" in caps
    assert caps["base.capabilities/auth/login"].origin == "base"
    assert caps["base.capabilities/auth/login"].status == "Supported"


def test_local_only_excludes_inherited(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "extra", Status="Missing")
    paths = {c.path for c in store(child).list_all(local_only=True)}
    assert paths == {"extra"}


def test_a_full_identifier_and_a_path_both_name_the_inherited_capability(tmp_path):
    """TCW-112 Design 3.1: the full identifier names base's own object, and
    the path names the object in the child's view, which is the same one."""
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    st = store(child)
    assert find_tree(st, "base.capabilities/auth/login").owner == "base"
    assert st.get_view("auth/login").origin == "base"


# ── override: metadata + body ────────────────────────────────────────────────

def test_override_status(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported", "body": "Log in."}})
    write_cap(child, "auth/login", complete=False, Status="Missing")
    st = store(child)
    assert st.get_view("auth/login").status == "Missing"         # child view overridden
    assert str(st.get_view("auth/login").overrides) == "base.capabilities/auth/login"
    assert store(base).get_view("auth/login").status == "Supported"   # upstream untouched


def test_override_body_append(tmp_path):
    base, child = child_of(tmp_path, {
        "media/upload": {"Status": "Supported",
                         "body": "Upload an image via a UI control."}})
    write_cap(child, "media/upload", complete=False,
              appendedDocs=["resources/camera.md"],
              docs={"resources/camera.md": "Or take a photo with the device camera."})
    body = store(child).get_view("media/upload").body
    assert "Upload an image" in body and "take a photo" in body


def test_override_body_replace(tmp_path):
    base, child = child_of(tmp_path, {
        "media/upload": {"Status": "Supported", "body": "UPSTREAM."}})
    write_cap(child, "media/upload", complete=False, body="MOBILE STORY.")
    body = store(child).get_view("media/upload").body
    assert body.strip() == "MOBILE STORY." and "UPSTREAM" not in body


def test_override_omitted_still_listed(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "auth/login", complete=False, Status="Omitted")
    caps = [(c.path, c.status) for c in store(child).list_all()]
    assert caps == [("auth/login", "Omitted")]          # listed once, as overridden


def test_override_null_clears_field(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported", "Priority": "P1"}})
    write_cap(child, "auth/login", complete=False, Priority=None)
    assert "Priority" not in store(child).get_view("auth/login").fields


# ── read-only structure ──────────────────────────────────────────────────────

def test_remove_inherited_raises(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    with pytest.raises(TcwError, match="belongs to project 'base'; run the command there"):
        store(child).remove("auth/login")


# ── validation ───────────────────────────────────────────────────────────────

def test_check_reports_a_3x_overrides_pointer(tmp_path):
    """TCW-112 Design 6.4: the `overrides:` pointer key is gone, and a state
    file still holding one is an error at that file."""
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "ov/x", overrides="cap-nope99", Status="Missing")
    problems = list(map(str, store(child).check()))
    assert ("error: docs/capabilities/ov/x/tcw-capability.yaml: 'overrides' was removed "
            "in TCW 4.0: an override is an object at the same path as the object it "
            "overrides; run 'tcw migrate' in this project, or move this folder to that "
            "path and delete the key") in problems, problems


def test_check_reports_an_object_that_overrides_nothing_and_is_incomplete(tmp_path):
    """TCW-112 Design 6.1: an object that overrides nothing must be complete."""
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "ov/x", complete=False, Status="Missing")
    problems = list(map(str, store(child).check()))
    assert ("error: docs/capabilities/ov/x/tcw-capability.yaml: child.capabilities/ov/x "
            "is incomplete: it overrides nothing, and has no name or description.md; if "
            "it overrode an object that moved or was removed, complete it or remove it"
            ) in problems, problems


def test_check_missing_attachment(tmp_path):
    root = repo(tmp_path, "solo")
    # Under `resources/`, the only place a listed document is read from
    # (TCW-111 Design 2.2).
    write_cap(root, "x", Status="Supported", appendedDocs=["resources/ghost.md"])
    assert any("missing attachment" in p for p in map(str, store(root).check()))


def test_check_unlisted_extra_doc(tmp_path):
    """The "unlisted extra doc" check is gone since TCW-111: a loose file in a
    capability's folder, `.md` or not, is the shape check's row a."""
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Supported",
              docs={"stray.md": "unreferenced"})
    problems = list(map(str, store(root).check()))
    assert any("stray.md: is not one of" in p and "move it into resources/" in p
               for p in problems), problems


# ── an override at the same path ─────────────────────────────────────────────

def test_an_override_at_the_same_path_checks_clean(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "auth/login", complete=False, Status="Missing")
    assert store(child).get_view("auth/login").status == "Missing"
    assert store(child).check() == []


# ── set on an inherited path: materialize the override (issue #3) ────────────

def ov_meta(child: Path, path: str) -> dict:
    return read_state(child / "docs" / "capabilities" / path / CAPABILITY_STATE)


def test_set_inherited_qualified(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"Status": "Supported"}})
    cap = store(child).set("base.capabilities/moderation/report-content", {"Status": "Missing"})
    # The capability as the child then sees it: its own override (Design 4.2).
    assert cap.status == "Missing" and cap.owner == "child"
    assert str(cap.overrides) == "base.capabilities/moderation/report-content"
    assert store(child).get_view("moderation/report-content").status == "Missing"
    assert store(base).get_view("moderation/report-content").status == "Supported"


def test_set_inherited_bare(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"Status": "Supported"}})
    store(child).set("moderation/report-content", {"Status": "Missing"})
    assert store(child).get_view("moderation/report-content").status == "Missing"


def test_set_inherited_materializes_mirrored_override(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"Status": "Supported"}})
    store(child).set("moderation/report-content", {"Status": "Missing"})
    assert ov_meta(child, "moderation/report-content") == {"Status": "Missing"}
    # No stray description.md — an empty one would still fall through, but the
    # override must stay a pure delta.
    assert not (child / "docs" / "capabilities" / "moderation" / "report-content"
                / "description.md").exists()
    assert store(child).check() == []


def test_set_inherited_twice_updates_in_place(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"Status": "Supported"}})
    store(child).set("moderation/report-content", {"Status": "Missing"})
    store(child).set("moderation/report-content", {"Status": "Partial",
                                                   "Gaps": "half done"})
    assert ov_meta(child, "moderation/report-content") == {
        "Status": "Partial", "Gaps": "half done"}
    caps = [c for c in store(child).list_all() if c.path == "moderation/report-content"]
    assert len(caps) == 1 and caps[0].status == "Partial"


def test_set_inherited_is_idempotent(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    store(child).set("auth/login", {"Status": "Missing"})
    first = ov_meta(child, "auth/login")
    store(child).set("auth/login", {"Status": "Missing"})
    assert ov_meta(child, "auth/login") == first


def test_set_inherited_updates_a_hand_written_override_in_place(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "auth/login", complete=False, Status="Missing", Priority="P1")
    store(child).set("auth/login", {"Status": "Partial", "Gaps": "wip"})
    assert ov_meta(child, "auth/login") == {"Status": "Partial", "Priority": "P1",
                                            "Gaps": "wip"}
    assert store(child).get_view("auth/login").status == "Partial"


def test_set_local_unchanged_by_override_machinery(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Missing")
    cap = store(root).set("x", {"Status": "Supported"})
    assert cap.status == "Supported" and cap.origin == "local"
    assert "overrides" not in ov_meta(root, "x")


def test_set_refuses_a_parent_that_is_the_capability_itself(tmp_path):
    """`set --parent` naming the object itself is refused before anything is
    written, not left for validate to find."""
    root = repo(tmp_path, "solo")
    write_cap(root, "cli/a")
    before = (root / "docs" / "capabilities" / "cli" / "a" / CAPABILITY_STATE).read_bytes()
    with pytest.raises(TcwError, match="parent names the capability itself"):
        store(root).set("cli/a", {}, parent="cli/a")
    assert (root / "docs" / "capabilities" / "cli" / "a" / CAPABILITY_STATE).read_bytes() \
        == before


@pytest.mark.parametrize("parent, existing", [
    ("auth/login", False), ("base.capabilities/auth/login", False),
    ("auth/login", True), ("base.capabilities/auth/login", True),
    ("child.capabilities/auth/login", True)])
def test_set_refuses_an_override_naming_itself_or_its_original_as_parent(
        tmp_path, parent, existing):
    """An override's `parent` naming the same path, which resolves to the
    capability it overrides, names the capability itself: refused, with
    nothing written, whether or not the override exists yet."""
    base, child = child_of(tmp_path, {"auth/login": {"Status": "Supported"}})
    if existing:
        write_cap(child, "auth/login", complete=False, Status="Missing")
    folder = child / "docs" / "capabilities"
    before = sorted(str(p) for p in folder.rglob("*")) if folder.exists() else []
    state = folder / "auth" / "login" / CAPABILITY_STATE
    old = state.read_bytes() if existing else None
    with pytest.raises(TcwError, match="parent names the capability itself"):
        store(child).set("auth/login", {}, parent=parent)
    assert (sorted(str(p) for p in folder.rglob("*")) if folder.exists() else []) == before
    if existing:
        assert state.read_bytes() == old


def test_set_refuses_a_parent_whose_chain_returns_to_the_capability(tmp_path):
    """`b` names `a` as its parent: setting `a`'s parent to `b` would make a
    loop, so it is refused and `a`'s state file is unchanged."""
    root = repo(tmp_path, "solo")
    write_cap(root, "a")
    write_cap(root, "b")
    store(root).set("b", {}, parent="a")
    before = (root / "docs" / "capabilities" / "a" / CAPABILITY_STATE).read_bytes()
    with pytest.raises(TcwError, match=r"parent would form a loop: "
                                       r"solo\.capabilities/a -> solo\.capabilities/b -> "
                                       r"solo\.capabilities/a"):
        store(root).set("a", {}, parent="b")
    assert (root / "docs" / "capabilities" / "a" / CAPABILITY_STATE).read_bytes() == before


def test_set_inherited_validates_status(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    with pytest.raises(TcwError, match="invalid Status"):
        store(child).set("auth/login", {"Status": "Bogus"})
    with pytest.raises(TcwError, match="unknown field"):
        store(child).set("auth/login", {"Nonsense": "x"})
    assert not (child / "docs" / "capabilities" / "auth" / "login").exists()


def test_set_unknown_path_still_raises(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    with pytest.raises(TcwError, match="no such capability"):
        store(child).set("nope/missing", {"Status": "Missing"})


def test_set_by_the_inherited_full_identifier_writes_the_object_at_the_same_path(
        tmp_path):
    """TCW-112 Design 4.2: whichever input names it, `set` writes the child's
    own object at the id-path; there is no second folder for an override."""
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "auth/login", Status="Missing")

    store(child).set("base.capabilities/auth/login", {"Status": "Partial", "Gaps": "wip"})

    assert not (child / "docs" / "capabilities" / "base").exists()
    assert ov_meta(child, "auth/login") == {"name": "Login", "Status": "Partial",
                                            "Gaps": "wip"}
    assert store(child).get_view("auth/login").status == "Partial"
    assert store(base).get_view("auth/login").status == "Supported"
    assert store(child).check() == []


def _two_parents(tmp_path):
    """`child` names `base` and `base2` as parents passing capabilities, and
    both declare `a/thing`. Returns (child, the full identifier the view
    shows there, the other parent's)."""
    base = repo(tmp_path, "base")
    write_cap(base, "a/thing", Status="Supported")
    base2 = repo(tmp_path, "base2")
    write_cap(base2, "a/thing", Status="Supported")
    child = repo(tmp_path, "child")
    connect_many(child, base, base2)
    shown = store(child).get_view("a/thing").full_id
    other = {"base": "base2", "base2": "base"}[shown.project]
    return child, str(shown), f"{other}.capabilities/a/thing"


def test_set_of_the_parent_the_view_does_not_show_is_refused(tmp_path):
    """Two parents declaring one path: the view shows one of them (TCW-112
    Design 2.5), and the other is not in the path's chain, so it cannot be
    overridden here (Design 4.2)."""
    child, shown, other = _two_parents(tmp_path)
    store(child).set(shown, {"Status": "Missing"})
    assert ov_meta(child, "a/thing") == {"Status": "Missing"}
    with pytest.raises(TcwError) as refused:
        store(child).set(other, {"Status": "Omitted"})
    other_id = other.split(".")[0]
    assert str(refused.value) == (
        f"{other} belongs to project '{other_id}', and 'child' does not inherit it, so "
        f"it cannot be overridden here; run the command there: tcw -C "
        f"{(child.parent / other_id).resolve()} …")
    assert refused.value.code == 3
    assert ov_meta(child, "a/thing") == {"Status": "Missing"}


def test_set_of_a_path_two_parents_declare_overrides_the_one_shown(tmp_path):
    """No path is ambiguous any more (TCW-112 Design 3.6)."""
    child, shown, _ = _two_parents(tmp_path)
    cap = store(child).set("a/thing", {"Status": "Missing"})
    assert (cap.status, str(cap.overrides)) == ("Missing", shown)


def test_set_inherited_null_clears_inherited_field(tmp_path):
    """None on an override writes explicit YAML null (clear), not a pop —
    popping would silently mean 're-inherit', a different intent."""
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported", "Priority": "P1"}})
    store(child).set("auth/login", {"Priority": None})
    assert ov_meta(child, "auth/login") == {"Priority": None}
    assert "Priority" not in store(child).get_view("auth/login").fields
    assert store(child).get_view("auth/login").status == "Supported"   # rest inherited


def test_set_local_null_writes_an_explicit_null(tmp_path):
    """TCW-112 Design 4.2: a cleared field is written as `null` on every own
    object, so `set` need not know whether it overrides one; over no
    inherited value it means what an absent key means."""
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Supported", Priority="P1")
    store(root).set("x", {"Priority": None})
    assert ov_meta(root, "x")["Priority"] is None
    assert "Priority" not in store(root).get_view("x").fields


def test_remove_of_the_inherited_full_identifier_still_refuses_after_override(tmp_path):
    """After an override, `rm auth/login` would remove the child's own
    override (TCW-112 Design 4.4); base's own object still cannot be removed."""
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    store(child).set("auth/login", {"Status": "Missing"})
    with pytest.raises(TcwError, match="belongs to project 'base'; run the command there"):
        store(child).remove("base.capabilities/auth/login")
    assert ov_meta(child, "auth/login") == {"Status": "Missing"}


# ── unreviewed vs decided (drift mechanism 2) ────────────────────────────────

def test_unreviewed_bare_inherited(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    unreviewed = {str(c.full_id) for c in store(child).unreviewed_inherited()}
    assert unreviewed == {"base.capabilities/auth/login"}


def test_override_setting_status_is_reviewed(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    store(child).set("auth/login", {"Status": "Missing"})   # sets Status
    assert store(child).unreviewed_inherited() == []


def test_override_without_status_still_unreviewed(tmp_path):
    """An override editing only a body/field re-inherits the master Status, so
    the status is still not a local decision."""
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "auth/login", complete=False, Priority="P1")  # no Status
    unreviewed = {c.path for c in store(child).unreviewed_inherited()}
    assert unreviewed == {"auth/login"}


def test_local_capability_never_unreviewed(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", Status="Missing")
    assert store(root).unreviewed_inherited() == []


def test_a_hand_written_override_setting_status_is_reviewed(tmp_path):
    """An override written by hand at the same path counts as a local status
    decision, the same as one `set` wrote."""
    base, child = child_of(tmp_path, {
        "auth/login": {"Status": "Supported"}})
    write_cap(child, "auth/login", complete=False, Status="Missing")
    assert store(child).unreviewed_inherited() == []


def test_inheriting_from_a_parent_not_on_this_machine_says_so(tmp_path):
    """A parent passing capabilities, in a repository this checkout lacks."""
    child = repo(tmp_path, "child")
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    with pytest.raises(InheritedUnavailable) as excinfo:
        store(child).list_all()
    message = str(excinfo.value)
    # TCW-108 Design 6.3: exit 7, with TCW-107 Design 6.2's sentence.
    assert excinfo.value.code == 7
    assert message.startswith("'child' inherits its capabilities from project 'base', "
                              "which is not on this machine: ")
    # TCW-108 AC 36: the folder the entry was resolved to, not its text.
    assert f"places it at {(tmp_path / 'base').resolve()}" in message


def test_capabilities_extends_in_the_projects_own_file_is_refused(tmp_path):
    """TCW-112 Design 1.5: the key is gone, and in the project's own file it
    stops the store from opening, naming the file and what to do instead."""
    base = repo(tmp_path, "base")
    write_cap(base, "billing/refund", body="Refund a charge.")
    child = repo(tmp_path, "child")
    write_config(base, "id: base\nchildren:\n- child\n")
    write_manifest(base, {"child": "../child"})
    config = write_config(child,
        "id: child\nparents:\n- base\n"
        "capabilities:\n  extends:\n    - base\n"
    )
    write_manifest(child, {"base": "../base"})
    with pytest.raises(ValueError) as excinfo:
        FsCapabilitiesStore.open(child)
    assert str(excinfo.value) == (
        f"{config}: 'capabilities.extends' was removed in TCW 4.0: a project inherits "
        f"its capabilities from its parents; name each project it inherits from under "
        f"'parents:' with an 'inherit' that includes capabilities, and delete this key")


# ── the extended store is resolved, not composed ─────────────────────────────


def test_a_sibling_that_moved_its_tree_can_still_be_extended(tmp_path):
    """`capabilities.path` is exactly what `tcw project new --capabilities-path` writes.

    The extended project's store used to be composed as `docs/capabilities` under
    its root, so moving it made the project unextendable and the error blamed a
    path nobody had written.
    """
    base = repo(tmp_path, "base")
    elsewhere = tmp_path / "base" / "ledger"
    elsewhere.mkdir(parents=True)
    (base / "docs" / "capabilities").rmdir()
    write_config(base,
        "id: base\ncapabilities:\n  path: ledger\n"
        "children:\n- child\n"
    )
    write_manifest(base, {"child": "../child"})
    (base / "docs" / "capabilities").mkdir(parents=True, exist_ok=True)
    write_cap(base, "auth/login", Status="Supported", body="Log in.")
    import shutil
    shutil.move(str(base / "docs" / "capabilities" / "auth"), str(elsewhere / "auth"))
    shutil.rmtree(base / "docs" / "capabilities")

    child = repo(tmp_path, "child")
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})

    caps = {str(c.full_id) for c in store(child).list_all()}
    assert "base.capabilities/auth/login" in caps


def test_a_parent_with_no_capabilities_store_contributes_nothing(tmp_path):
    """TCW-112 Design 1.2: a source with no store for the axis adds no
    objects and is not an error."""
    base = repo(tmp_path, "base")
    (base / "docs" / "capabilities").rmdir()
    write_config(base, "id: base\nchildren:\n- child\n")
    write_manifest(base, {"child": "../child"})
    child = repo(tmp_path, "child")
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    write_cap(child, "own", Status="Supported")
    assert [c.path for c in store(child).list_all()] == ["own"]


def test_a_sibling_whose_tree_is_declared_but_absent_says_to_provision(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    base = repo(tmp_path, "base")
    (base / "docs" / "capabilities").rmdir()
    write_config(base,
        "id: base\ncapabilities:\n"
        "  path: ledger\n"
        "  repository:\n    url: https://example.invalid/ledger.git\n"
        "children:\n- child\n"
    )
    write_manifest(base, {"child": "../child"})
    child = repo(tmp_path, "child")
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    with pytest.raises(InheritedUnavailable) as excinfo:     # TCW-112 Design 1.3
        store(child).list_all()
    message = str(excinfo.value)
    assert "project 'base'" in message
    assert "https://example.invalid/ledger.git" in message
    # The command run where the store is declared (TCW-115 Design 7.2).
    assert f"tcw -C {base} project provision --component capabilities" in message


def _chain(tmp_path, depth: int, moved: set[int] = frozenset()):
    """A linear chain of parents `n0 → n1 → …`, optionally with moved trees."""
    import subprocess
    import yaml
    from tcw.store.fs import write_sentinel

    for i in range(depth):
        d = tmp_path / f"n{i}"
        tree = d / ("ledger" if i in moved else "docs/capabilities")
        tree.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        write_sentinel(d, f"n{i}")
    for i in range(depth):
        d = tmp_path / f"n{i}"
        doc = {"id": f"n{i}"}
        if i in moved:
            doc["capabilities"] = {"path": "ledger"}
        if i + 1 < depth:
            # The next node is each node's parent passing capabilities.
            doc["parents"] = [{"id": f"n{i+1}", "inherit": ["capabilities"]}]
            write_manifest(d, {f"n{i+1}": f"../n{i+1}"})
        write_config(d, yaml.safe_dump(doc, sort_keys=False))
    return tmp_path / "n0"


def test_a_moved_sibling_that_extends_further_still_resolves(tmp_path):
    """Resolving the sibling's store enabled this, and rebuilding it broke it.

    The nested store used to be reconstructed from its root with no `project_root`,
    and `FsTreeStore` falls back to `root.parent.parent` — correct only for the
    `docs/<component>` shape this resolution exists to stop assuming. A sibling
    whose tree had moved got a node root two levels above its repo, so its own
    `extends` was resolved against the wrong project graph and the chain broke
    one link past the hop that had just been made to work.
    """
    root = _chain(tmp_path, 3, moved={1})
    (tmp_path / "n1" / "ledger" / "own").mkdir()
    write_state(tmp_path / "n1" / "ledger" / "own" / CAPABILITY_STATE,
        "name: Own\nStatus: Supported\n")
    (tmp_path / "n1" / "ledger" / "own" / "description.md").write_text("")
    assert {str(c.full_id) for c in store(root).list_all()} == {"n1.capabilities/own"}
    assert store(root).check() == []


def test_extends_in_a_parents_own_file_is_ignored(tmp_path):
    """TCW-112 Design 1.5: `capabilities.extends` is refused only in the
    active project's own file; in another project's file it is ignored, so a
    parent not yet migrated still passes its capabilities."""
    base, child = child_of(tmp_path, {"billing/refund": {"Status": "Supported"}})
    declare_extends(base, "capabilities",
        "extends:\n  nope: ../somewhere\n"          # the 3.x legacy map form
    )
    listed = store(child).list_all()
    assert [(c.path, c.owner) for c in listed] == [("billing/refund", "base")]


def _diamond(tmp_path, levels: int):
    """`levels` pairs of nodes, each pair inheriting from *both* nodes of the
    next.

    Every node is a child of one hub, and also names the two nodes of the
    next pair as parents passing capabilities — those edges are what form the
    graph this measures.
    """
    import subprocess
    import yaml
    from tcw.store.fs import write_sentinel

    names = [f"n{level}x{side}" for level in range(levels) for side in (0, 1)]
    for name in [*names, "hub"]:
        d = tmp_path / name
        (d / "docs" / "capabilities").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        write_sentinel(d, name)
    write_config(tmp_path / "hub", yaml.safe_dump(
        {"id": "hub", "children": names}, sort_keys=False))
    write_manifest(tmp_path / "hub", {n: f"../{n}" for n in names})
    for level in range(levels):
        for side in (0, 1):
            d = tmp_path / f"n{level}x{side}"
            parents = ["hub"]
            if level + 1 < levels:
                parents += [{"id": f"n{level+1}x{other}", "inherit": ["capabilities"]}
                            for other in (0, 1)]
            write_config(d, yaml.safe_dump(
                {"id": f"n{level}x{side}", "parents": parents}, sort_keys=False))
            write_manifest(d, {"hub": "../hub"})
    return tmp_path / "n0x0"


def test_a_shared_subtree_is_built_once(tmp_path, monkeypatch):
    """A graph where two parents reach a common ancestor used to rebuild that
    subtree once per route: 2^levels − 1 constructions, measured at 1023 and
    twelve seconds for ten levels. The view opens each source's store once
    (TCW-112 Design 1.4); the count is asserted rather than the time, because
    the count is the property."""
    opened = []
    real = FsCapabilitiesStore.open.__func__

    def counted(cls, project_root, *args, **kwargs):
        opened.append(Path(project_root).resolve())
        return real(cls, project_root, *args, **kwargs)

    root = _diamond(tmp_path, 8)
    monkeypatch.setattr(FsCapabilitiesStore, "open", classmethod(counted))
    store(root).list_all()
    assert len(opened) == len(set(opened)), opened       # no store opened twice
    assert len(opened) <= 4 * 8


def test_federation_stays_linear_in_chain_depth(tmp_path):
    """Each edge used to build the same subtree twice — 2^depth, measured at
    15.7 s for eleven links. The bound is generous; what it guards is the shape.
    """
    import time

    root = _chain(tmp_path, 14)
    started = time.monotonic()
    store(root).list_all()
    assert time.monotonic() - started < 5.0
