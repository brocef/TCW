"""Phase B — capability federation: extends + override + body composition."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import AmbiguousRef
from tcw.store.fs import FsCapabilitiesStore, write_sentinel


from nodeconfig import declare_extends
from tcw.errors import InheritedUnavailable, TcwError, UsageError
from tests.projectfiles import write_config, write_manifest
from tests.statefiles import write_state, CAPABILITY_STATE


def repo(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root, name)
    return root


def write_cap(root: Path, path: str, *, id=None, body="", docs=None, **meta) -> None:
    d = root / "docs" / "capabilities" / path
    d.mkdir(parents=True, exist_ok=True)
    m = {}
    if id is not None:
        m["id"] = id
    m["name"] = meta.pop("name", path.rsplit("/", 1)[-1].replace("-", " ").title())
    m.update(meta)
    write_state(d / CAPABILITY_STATE, yaml.safe_dump(m, sort_keys=False, allow_unicode=True))
    (d / "description.md").write_text(body)
    for fn, text in (docs or {}).items():
        (d / fn).write_text(text)


def child_of(tmp_path, base_caps: dict) -> tuple[Path, Path]:
    """Return (base, child) where child explicitly extends registered base."""
    base = repo(tmp_path, "base")
    for path, kw in base_caps.items():
        write_cap(base, path, **kw)
    child = repo(tmp_path, "child")
    write_config(base, "id: base\nchildren:\n- child\n")
    write_manifest(base, {"child": "../child"})
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    FsCapabilitiesStore.open(child).extends_add("base")
    return base, child


def store(root: Path) -> FsCapabilitiesStore:
    return FsCapabilitiesStore.open(root)         # reopen so extends resolves


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
        "auth/login": {"id": "cap-aaa111", "Status": "Supported", "body": "Log in."}})
    caps = {str(c.full_id): c for c in store(child).list_all()}
    assert "base.capabilities/auth/login" in caps
    assert caps["base.capabilities/auth/login"].origin == "base"
    assert caps["base.capabilities/auth/login"].status == "Supported"


def test_local_only_excludes_inherited(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "extra", id="cap-loc001", Status="Missing")
    paths = {c.path for c in store(child).list_all(local_only=True)}
    assert paths == {"extra"}


def test_get_inherited_by_prefixed_and_bare(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    st = store(child)
    assert st.get_inherited("base", "auth/login").origin == "base"
    assert st.get_view("auth/login").origin == "base"          # bare-wins resolution


# ── override: metadata + body ────────────────────────────────────────────────

def test_override_status(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported", "body": "Log in."}})
    write_cap(child, "ov/login", overrides="cap-aaa111", Status="Missing")
    st = store(child)
    assert st.get_view("auth/login").status == "Missing"         # child view overridden
    assert store(base).get_view("auth/login").status == "Supported"   # upstream untouched


def test_override_body_append(tmp_path):
    base, child = child_of(tmp_path, {
        "media/upload": {"id": "cap-bbb222", "Status": "Supported",
                         "body": "Upload an image via a UI control."}})
    write_cap(child, "ov/upload", overrides="cap-bbb222",
              appendedDocs=["camera.md"],
              docs={"camera.md": "Or take a photo with the device camera."})
    body = store(child).get_view("media/upload").body
    assert "Upload an image" in body and "take a photo" in body


def test_override_body_replace(tmp_path):
    base, child = child_of(tmp_path, {
        "media/upload": {"id": "cap-bbb222", "Status": "Supported", "body": "UPSTREAM."}})
    write_cap(child, "ov/upload", overrides="cap-bbb222", body="MOBILE STORY.")
    body = store(child).get_view("media/upload").body
    assert body.strip() == "MOBILE STORY." and "UPSTREAM" not in body


def test_override_omitted_still_listed(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/login", overrides="cap-aaa111", Status="Omitted")
    caps = {str(c.full_id): c.status for c in store(child).list_all()}
    assert caps.get("base.capabilities/auth/login") == "Omitted"


def test_override_null_clears_field(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported", "Priority": "P1"}})
    write_cap(child, "ov/login", overrides="cap-aaa111", Priority=None)
    assert "Priority" not in store(child).get_view("auth/login").fields


# ── read-only structure ──────────────────────────────────────────────────────

def test_remove_inherited_raises(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    with pytest.raises(TcwError, match="cannot remove inherited"):
        store(child).remove("auth/login")


# ── validation ───────────────────────────────────────────────────────────────

def test_check_dangling_override(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/x", overrides="cap-nope99", Status="Missing")
    assert any("dangling id" in p for p in map(str, store(child).check()))


def test_check_unknown_alias_override_names_the_undeclared_extends(tmp_path):
    """`<alias>/<id>` with an alias this project does not extend. The only way
    that happens on the store being checked is that the alias is missing from
    `capabilities.extends` — often because it is still sitting in a pre-2.5.0
    `.config.yaml` — so the message says where it has to be declared rather than
    only that the alias is unknown."""
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/x", overrides="shared/cap-aaa111", Status="Missing")
    problems = [p for p in map(str, store(child).check()) if "unknown alias" in p]
    assert len(problems) == 1, problems
    assert problems[0].startswith(
        "error: docs/capabilities/ov/x: overrides → unknown alias 'shared'"), problems
    assert "capabilities.extends" in problems[0], problems
    assert "tcw-config.yaml" in problems[0], problems
    assert problems[0] != "ov/x: overrides → unknown alias 'shared'"     # the old text


def test_check_local_target_override(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "local", id="cap-loc001", Status="Missing")
    write_cap(child, "ov/x", overrides="cap-loc001", Status="Missing")
    assert any("targets a local capability" in p for p in map(str, store(child).check()))


def test_check_ambiguous_override(tmp_path):
    base = repo(tmp_path, "base")
    write_cap(base, "a", id="cap-dup", Status="Supported")
    base2 = repo(tmp_path, "base2")
    write_cap(base2, "b", id="cap-dup", Status="Supported")
    child = repo(tmp_path, "child")
    connect_many(child, base, base2)
    st = FsCapabilitiesStore.open(child)
    st.extends_add("base")
    st.extends_add("base2")
    write_cap(child, "ov/x", overrides="cap-dup", Status="Missing")
    assert any("ambiguous id" in p for p in map(str, store(child).check()))


def test_check_missing_attachment(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Supported", appendedDocs=["ghost.md"])
    assert any("missing attachment" in p for p in map(str, store(root).check()))


def test_check_unlisted_extra_doc(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Supported",
              docs={"stray.md": "unreferenced"})
    assert any("unlisted extra doc" in p for p in map(str, store(root).check()))


def test_check_federation_cycle(tmp_path):
    a = repo(tmp_path, "a")
    b = repo(tmp_path, "b")
    # `a` names `b` as a parent and `b` lists `a`: `a` may extend `b`, and
    # `b` may not extend its descendant `a`, so the cycle cannot be written
    # (TCW-108 Design 3.6).
    write_config(a, "id: a\nparents:\n- id: b\n  inherit: [capabilities]\n")
    write_manifest(a, {"b": "../b"})
    write_config(b, "id: b\nchildren:\n- a\n")
    write_manifest(b, {"a": "../a"})
    FsCapabilitiesStore.open(a).extends_add("b")
    before = (b / ".tcw" / "tcw-config.yaml").read_bytes()
    with pytest.raises(UsageError) as refused:
        FsCapabilitiesStore.open(b).extends_add("a")
    assert str(refused.value) == (
        "'a' is in capabilities.extends, but 'b' does not inherit its capabilities "
        "from it: name it under 'parents:' with an 'inherit' that includes capabilities")
    assert refused.value.code == 2
    assert (b / ".tcw" / "tcw-config.yaml").read_bytes() == before


# ── get_by_id + qualified override target ────────────────────────────────────

def test_qualified_override_target(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/login", overrides="base/cap-aaa111", Status="Missing")
    assert store(child).get_view("auth/login").status == "Missing"
    assert store(child).check() == []


def test_get_by_id_local(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Supported")
    assert store(root).get_by_id("cap-x").path == "x"


# ── set on an inherited path: materialize the override (issue #3) ────────────

def ov_meta(child: Path, path: str) -> dict:
    return yaml.safe_load((child / "docs" / "capabilities" / path / CAPABILITY_STATE)
                          .read_text())


def test_set_inherited_qualified(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    cap = store(child).set("base.capabilities/moderation/report-content", {"Status": "Missing"})
    assert cap.status == "Missing" and cap.origin == "base"
    assert store(child).get_view("moderation/report-content").status == "Missing"
    assert store(base).get_view("moderation/report-content").status == "Supported"


def test_set_inherited_bare(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("moderation/report-content", {"Status": "Missing"})
    assert store(child).get_view("moderation/report-content").status == "Missing"


def test_set_inherited_materializes_mirrored_override(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("moderation/report-content", {"Status": "Missing"})
    assert ov_meta(child, "moderation/report-content") == {
        "overrides": "base/cap-aaa111", "Status": "Missing"}
    # No stray description.md — an empty one would still fall through, but the
    # override must stay a pure delta.
    assert not (child / "docs" / "capabilities" / "moderation" / "report-content"
                / "description.md").exists()
    assert store(child).check() == []


def test_set_inherited_twice_updates_in_place(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("moderation/report-content", {"Status": "Missing"})
    store(child).set("moderation/report-content", {"Status": "Partial",
                                                   "Gaps": "half done"})
    assert ov_meta(child, "moderation/report-content") == {
        "overrides": "base/cap-aaa111", "Status": "Partial", "Gaps": "half done"}
    caps = [c for c in store(child).list_all() if c.path == "moderation/report-content"]
    assert len(caps) == 1 and caps[0].status == "Partial"


def test_set_inherited_is_idempotent(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("auth/login", {"Status": "Missing"})
    first = ov_meta(child, "auth/login")
    store(child).set("auth/login", {"Status": "Missing"})
    assert ov_meta(child, "auth/login") == first


def test_set_inherited_reuses_hand_authored_override(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/login", overrides="cap-aaa111", Status="Missing")
    store(child).set("auth/login", {"Status": "Partial", "Gaps": "wip"})
    assert ov_meta(child, "ov/login")["Status"] == "Partial"     # in place
    assert not (child / "docs" / "capabilities" / "auth" / "login").exists()
    assert store(child).get_view("auth/login").status == "Partial"


def test_set_local_unchanged_by_override_machinery(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Missing")
    cap = store(root).set("x", {"Status": "Supported"})
    assert cap.status == "Supported" and cap.origin == "local"
    assert "overrides" not in ov_meta(root, "x")


def test_set_inherited_validates_status(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    with pytest.raises(TcwError, match="invalid Status"):
        store(child).set("auth/login", {"Status": "Bogus"})
    with pytest.raises(TcwError, match="unknown field"):
        store(child).set("auth/login", {"Nonsense": "x"})
    assert not (child / "docs" / "capabilities" / "auth" / "login").exists()


def test_set_unknown_path_still_raises(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    with pytest.raises(TcwError, match="no such capability"):
        store(child).set("nope/missing", {"Status": "Missing"})


def test_set_inherited_falls_back_when_local_occupies_path(tmp_path):
    """`alias/x/y` addressed explicitly while a local `x/y` also exists: mirror
    to `<alias>/x/y` instead — never clobber the local declaration, and never
    refuse a path `show` accepts."""
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "auth/login", id="cap-loc001", Status="Missing")
    before = (child / "docs" / "capabilities" / "auth" / "login" / CAPABILITY_STATE).read_bytes()

    store(child).set("base.capabilities/auth/login", {"Status": "Partial", "Gaps": "wip"})

    assert (child / "docs" / "capabilities" / "auth" / "login"
            / CAPABILITY_STATE).read_bytes() == before          # local untouched
    assert ov_meta(child, "base/auth/login") == {
        "overrides": "base/cap-aaa111", "Status": "Partial", "Gaps": "wip"}
    assert store(child).get_inherited("base", "auth/login").status == "Partial"
    assert store(child).get_view("auth/login").status == "Missing"   # bare wins local
    assert store(child).check() == []


def test_set_second_alias_same_path(tmp_path):
    """Two aliases exporting the same path: the first override occupies the
    mirrored path, so the second must qualify rather than become un-settable."""
    base = repo(tmp_path, "base")
    write_cap(base, "a/thing", id="cap-one", Status="Supported")
    base2 = repo(tmp_path, "base2")
    write_cap(base2, "a/thing", id="cap-two", Status="Supported")
    child = repo(tmp_path, "child")
    connect_many(child, base, base2)
    st = FsCapabilitiesStore.open(child)
    st.extends_add("base")
    st.extends_add("base2")

    store(child).set("base.capabilities/a/thing", {"Status": "Missing"})
    store(child).set("base2.capabilities/a/thing", {"Status": "Omitted"})

    assert store(child).get_inherited("base", "a/thing").status == "Missing"
    assert store(child).get_inherited("base2", "a/thing").status == "Omitted"
    assert ov_meta(child, "a/thing")["overrides"] == "base/cap-one"
    assert ov_meta(child, "base2/a/thing")["overrides"] == "base2/cap-two"
    assert store(child).check() == []
    # Re-entrant: each updates its own override in place.
    store(child).set("base2.capabilities/a/thing", {"Status": "Partial", "Gaps": "x"})
    assert store(child).get_inherited("base2", "a/thing").status == "Partial"
    assert store(child).get_inherited("base", "a/thing").status == "Missing"


def test_set_ambiguous_bare_ref_raises(tmp_path):
    base = repo(tmp_path, "base")
    write_cap(base, "a/thing", id="cap-one", Status="Supported")
    base2 = repo(tmp_path, "base2")
    write_cap(base2, "a/thing", id="cap-two", Status="Supported")
    child = repo(tmp_path, "child")
    connect_many(child, base, base2)
    st = FsCapabilitiesStore.open(child)
    st.extends_add("base")
    st.extends_add("base2")
    with pytest.raises(AmbiguousRef):
        store(child).set("a/thing", {"Status": "Missing"})


def test_set_inherited_null_clears_inherited_field(tmp_path):
    """None on an override writes explicit YAML null (clear), not a pop —
    popping would silently mean 're-inherit', a different intent."""
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported", "Priority": "P1"}})
    store(child).set("auth/login", {"Priority": None})
    assert ov_meta(child, "auth/login") == {"overrides": "base/cap-aaa111",
                                            "Priority": None}
    assert "Priority" not in store(child).get_view("auth/login").fields
    assert store(child).get_view("auth/login").status == "Supported"   # rest inherited


def test_set_local_null_pops_field(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Supported", Priority="P1")
    store(root).set("x", {"Priority": None})
    assert "Priority" not in ov_meta(root, "x")


def test_remove_inherited_still_refuses_after_override(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("auth/login", {"Status": "Missing"})
    with pytest.raises(TcwError, match="cannot remove inherited"):
        store(child).remove("auth/login")


# ── unreviewed vs decided (drift mechanism 2) ────────────────────────────────

def test_unreviewed_bare_inherited(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    unreviewed = {str(c.full_id) for c in store(child).unreviewed_inherited()}
    assert unreviewed == {"base.capabilities/auth/login"}


def test_override_setting_status_is_reviewed(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("auth/login", {"Status": "Missing"})   # sets Status
    assert store(child).unreviewed_inherited() == []


def test_override_without_status_still_unreviewed(tmp_path):
    """An override editing only a body/field re-inherits the master Status, so
    the status is still not a local decision."""
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/login", overrides="cap-aaa111", Priority="P1")  # no Status
    unreviewed = {str(c.full_id) for c in store(child).unreviewed_inherited()}
    assert unreviewed == {"base.capabilities/auth/login"}


def test_local_capability_never_unreviewed(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Missing")
    assert store(root).unreviewed_inherited() == []


def test_reviewed_via_alias_qualified_override_key(tmp_path):
    """An override keyed by the alias-qualified id (base/cap-...) counts as a
    local status decision, same as the bare-id form."""
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/login", overrides="base/cap-aaa111", Status="Missing")
    assert store(child).unreviewed_inherited() == []


def test_extending_a_declared_but_absent_project_says_so(tmp_path):
    """A node whose extended sibling is in a repository this checkout lacks.

    The declaration is written straight into the node config rather than
    through `extends_add`, because that is how such a config arrives: authored
    on a machine that had the sibling, then cloned somewhere that does not.
    `extends_add` would refuse it here, which is the point — this exercises the
    read path against a declaration no command on this machine could produce.
    """
    child = repo(tmp_path, "child")
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    declare_extends(child, "capabilities",
        "extends:\n  - base\n"
    )
    with pytest.raises(InheritedUnavailable) as excinfo:
        store(child).list_all()
    message = str(excinfo.value)
    # TCW-108 Design 6.3: exit 7, with TCW-107 Design 6.2's sentence.
    assert excinfo.value.code == 7
    assert message.startswith("'child' inherits its capabilities from project 'base', "
                              "which is not on this machine: ")
    # TCW-108 AC 36: the folder the entry was resolved to, not its text.
    assert f"places it at {(tmp_path / 'base').resolve()}" in message


def test_extending_a_project_that_was_never_declared_is_unchanged(tmp_path):
    child = repo(tmp_path, "child")
    write_config(child, "id: child\n")
    declare_extends(child, "capabilities",
        "extends:\n  - nowhere\n"
    )
    with pytest.raises(ValueError) as excinfo:
        store(child).list_all()
    # TCW-108 Design 3.6: held to the parent links.
    assert "'nowhere' is in capabilities.extends, but 'child' does not inherit its " \
        "capabilities from it" in str(excinfo.value)


def test_extends_add_names_a_declared_but_absent_project(tmp_path):
    child = repo(tmp_path, "child")
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    with pytest.raises(TcwError) as excinfo:
        FsCapabilitiesStore.open(child).extends_add("base")
    # TCW-108 Design 6.3: a parent passing the axis, not on this machine.
    assert excinfo.value.code == 7
    assert "from project 'base', which is not on this machine" in str(excinfo.value)


# ── the extended store is resolved, not composed ─────────────────────────────


def test_a_sibling_that_moved_its_tree_can_still_be_extended(tmp_path):
    """`capabilities.path` is exactly what `tcw init --capabilities-path` writes.

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
    write_cap(base, "auth/login", id="cap-aaa111", Status="Supported", body="Log in.")
    import shutil
    shutil.move(str(base / "docs" / "capabilities" / "auth"), str(elsewhere / "auth"))
    shutil.rmtree(base / "docs" / "capabilities")

    child = repo(tmp_path, "child")
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    declare_extends(child, "capabilities", "extends:\n  - base\n")

    caps = {str(c.full_id) for c in store(child).list_all()}
    assert "base.capabilities/auth/login" in caps


def test_a_sibling_with_no_component_names_the_project(tmp_path):
    base = repo(tmp_path, "base")
    (base / "docs" / "capabilities").rmdir()
    write_config(base, "id: base\nchildren:\n- child\n")
    write_manifest(base, {"child": "../child"})
    child = repo(tmp_path, "child")
    write_config(child, "id: child\nparents:\n- base\n")
    write_manifest(child, {"base": "../base"})
    declare_extends(child, "capabilities", "extends:\n  - base\n")
    with pytest.raises(ValueError) as excinfo:
        store(child).list_all()
    assert "project 'base' has no capabilities component" in str(excinfo.value)


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
    declare_extends(child, "capabilities", "extends:\n  - base\n")
    with pytest.raises(ValueError) as excinfo:
        store(child).list_all()
    message = str(excinfo.value)
    assert "project 'base'" in message
    assert "https://example.invalid/ledger.git" in message
    assert "tcw provision" in message


def _chain(tmp_path, depth: int, moved: set[int] = frozenset()):
    """A linear `extends` chain `n0 → n1 → …`, optionally with moved trees."""
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
            # Each node extends the next, so the next is its parent passing
            # capabilities.
            doc["parents"] = [{"id": f"n{i+1}", "inherit": ["capabilities"]}]
            write_manifest(d, {f"n{i+1}": f"../n{i+1}"})
        write_config(d, yaml.safe_dump(doc, sort_keys=False))
        if i + 1 < depth:
            # On the node, not the store dir: a moved node's `capabilities.path`
            # is already in this section and must survive the merge.
            declare_extends(d, "capabilities", f"extends:\n  - n{i+1}\n")
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
        "id: cap-ddd222\nname: Own\nStatus: Supported\n")
    (tmp_path / "n1" / "ledger" / "own" / "description.md").write_text("")
    assert {str(c.full_id) for c in store(root).list_all()} == {"n1.capabilities/own"}
    assert store(root).check() == []


def test_a_broken_sibling_reports_its_own_error(tmp_path):
    """Every ValueError used to be rewritten as "has no capabilities component",
    which sends the reader to create a store that already exists."""
    base, child = child_of(tmp_path, {})
    declare_extends(base, "capabilities",
        "extends:\n  nope: ../somewhere\n"          # the legacy map form
    )
    with pytest.raises(ValueError) as excinfo:
        store(child).list_all()
    message = str(excinfo.value)
    assert "legacy extends map is unsupported" in message
    assert "has no capabilities component" not in message


def test_a_cycle_is_reported_from_the_top_of_the_chain(tmp_path):
    """A cycle needs one project to extend its descendant, which TCW-108
    Design 3.6 refuses, so the store opened on the way names that instead."""
    base, child = child_of(tmp_path, {})
    declare_extends(base, "capabilities", "extends:\n  - child\n")
    declare_extends(child, "capabilities", "extends:\n  - base\n")
    with pytest.raises(ValueError, match="'child' is in capabilities.extends, but "
                                         "'base' does not inherit"):
        store(child).check()


def _diamond(tmp_path, levels: int):
    """`levels` pairs of nodes, each pair extending *both* nodes of the next.

    Every node is a child of one hub, and also names the two nodes of the
    next pair as parents passing capabilities, because it extends them — the
    `extends` edges are what form the DAG, which is the graph this measures.
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
            if level + 1 < levels:
                declare_extends(d, "capabilities",
                    f"extends:\n  - n{level+1}x0\n  - n{level+1}x1\n")
    return tmp_path / "n0x0"


def test_a_shared_subtree_is_built_once(tmp_path, monkeypatch):
    """`seen_nodes` terminated a cycle and memoised nothing, so a graph where two
    extended projects reach a common ancestor rebuilt that subtree once per
    route: 2^levels − 1 constructions, measured at 1023 and twelve seconds for
    ten levels. The count is asserted rather than the time, because the count is
    the property."""
    from tcw.store import fs as fs_module

    calls = []
    real = fs_module._extended_component_stores

    def counted(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(fs_module, "_extended_component_stores", counted)
    root = _diamond(tmp_path, 8)
    store(root).list_all()
    # One per node on the path plus the root's own: linear, not 255.
    assert len(calls) <= 4 * 8


def test_federation_stays_linear_in_chain_depth(tmp_path):
    """Each edge used to build the same subtree twice — 2^depth, measured at
    15.7 s for eleven links. The bound is generous; what it guards is the shape.
    """
    import time

    root = _chain(tmp_path, 14)
    started = time.monotonic()
    store(root).list_all()
    assert time.monotonic() - started < 5.0


def test_extends_is_read_from_the_node_config_with_no_store_file(tmp_path):
    """Spec criterion 2 — the capabilities half. `capabilities.extends` in
    `tcw-config.yaml`, and no `.config.yaml` inside the store."""
    base = repo(tmp_path, "base")
    write_cap(base, "billing/refund", body="Refund a charge.")
    child = repo(tmp_path, "child")
    write_config(base, "id: base\nchildren:\n- child\n")
    write_manifest(base, {"child": "../child"})
    write_config(child,
        "id: child\nparents:\n- base\n"
        "capabilities:\n  extends:\n    - base\n"
    )
    write_manifest(child, {"base": "../base"})

    assert not (child / "docs" / "capabilities" / ".config.yaml").exists()
    listed = FsCapabilitiesStore.open(child).list_all()
    assert {(cap.path, cap.origin) for cap in listed} == {("billing/refund", "base")}
