"""Phase B — capability federation: extends + override + body composition."""

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


def write_cap(root: Path, path: str, *, id=None, body="", docs=None, **meta) -> None:
    d = root / "docs" / "capabilities" / path
    d.mkdir(parents=True, exist_ok=True)
    m = {}
    if id is not None:
        m["id"] = id
    m["name"] = meta.pop("name", path.rsplit("/", 1)[-1].replace("-", " ").title())
    m.update(meta)
    (d / "meta.yaml").write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True))
    (d / "description.md").write_text(body)
    for fn, text in (docs or {}).items():
        (d / fn).write_text(text)


def child_of(tmp_path, base_caps: dict) -> tuple[Path, Path]:
    """Return (base, child) where child extends base under alias 'shared'."""
    base = repo(tmp_path, "base")
    for path, kw in base_caps.items():
        write_cap(base, path, **kw)
    child = repo(tmp_path, "child")
    FsCapabilitiesStore.open(child).extends_add("shared", "../base")
    return base, child


def store(root: Path) -> FsCapabilitiesStore:
    return FsCapabilitiesStore.open(root)         # reopen so extends resolves


# ── inheritance (read-through) ───────────────────────────────────────────────

def test_inherited_listed_with_origin(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported", "body": "Log in."}})
    caps = {c.qualified: c for c in store(child).list_all()}
    assert "shared/auth/login" in caps
    assert caps["shared/auth/login"].origin == "shared"
    assert caps["shared/auth/login"].status == "Supported"


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
    assert st.get("shared/auth/login").origin == "shared"
    assert st.get("auth/login").origin == "shared"          # bare-wins resolution


# ── override: metadata + body ────────────────────────────────────────────────

def test_override_status(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported", "body": "Log in."}})
    write_cap(child, "ov/login", overrides="cap-aaa111", Status="Missing")
    st = store(child)
    assert st.get("auth/login").status == "Missing"         # child view overridden
    assert store(base).get("auth/login").status == "Supported"   # upstream untouched


def test_override_body_append(tmp_path):
    base, child = child_of(tmp_path, {
        "media/upload": {"id": "cap-bbb222", "Status": "Supported",
                         "body": "Upload an image via a UI control."}})
    write_cap(child, "ov/upload", overrides="cap-bbb222",
              appendedDocs=["camera.md"],
              docs={"camera.md": "Or take a photo with the device camera."})
    body = store(child).get("media/upload").body
    assert "Upload an image" in body and "take a photo" in body


def test_override_body_replace(tmp_path):
    base, child = child_of(tmp_path, {
        "media/upload": {"id": "cap-bbb222", "Status": "Supported", "body": "UPSTREAM."}})
    write_cap(child, "ov/upload", overrides="cap-bbb222", body="MOBILE STORY.")
    body = store(child).get("media/upload").body
    assert body.strip() == "MOBILE STORY." and "UPSTREAM" not in body


def test_override_omitted_still_listed(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/login", overrides="cap-aaa111", Status="Omitted")
    caps = {c.qualified: c.status for c in store(child).list_all()}
    assert caps.get("shared/auth/login") == "Omitted"


def test_override_null_clears_field(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported", "Priority": "P1"}})
    write_cap(child, "ov/login", overrides="cap-aaa111", Priority=None)
    assert "Priority" not in store(child).get("auth/login").fields


# ── read-only structure ──────────────────────────────────────────────────────

def test_remove_inherited_raises(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    with pytest.raises(ValueError, match="cannot remove inherited"):
        store(child).remove("auth/login")


# ── validation ───────────────────────────────────────────────────────────────

def test_check_dangling_override(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/x", overrides="cap-nope99", Status="Missing")
    assert any("dangling id" in p for p in store(child).check())


def test_check_local_target_override(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "local", id="cap-loc001", Status="Missing")
    write_cap(child, "ov/x", overrides="cap-loc001", Status="Missing")
    assert any("targets a local capability" in p for p in store(child).check())


def test_check_ambiguous_override(tmp_path):
    base = repo(tmp_path, "base")
    write_cap(base, "a", id="cap-dup", Status="Supported")
    base2 = repo(tmp_path, "base2")
    write_cap(base2, "b", id="cap-dup", Status="Supported")
    child = repo(tmp_path, "child")
    st = FsCapabilitiesStore.open(child)
    st.extends_add("one", "../base")
    st.extends_add("two", "../base2")
    write_cap(child, "ov/x", overrides="cap-dup", Status="Missing")
    assert any("ambiguous id" in p for p in store(child).check())


def test_check_missing_attachment(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Supported", appendedDocs=["ghost.md"])
    assert any("missing attachment" in p for p in store(root).check())


def test_check_unlisted_extra_doc(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Supported",
              docs={"stray.md": "unreferenced"})
    assert any("unlisted extra doc" in p for p in store(root).check())


def test_check_federation_cycle(tmp_path):
    a = repo(tmp_path, "a")
    b = repo(tmp_path, "b")
    FsCapabilitiesStore.open(a).extends_add("b", "../b")
    FsCapabilitiesStore.open(b).extends_add("a", "../a")     # a→b→a
    assert any("cycle in capability federation" in p for p in store(a).check())


# ── get_by_id + qualified override target ────────────────────────────────────

def test_qualified_override_target(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "ov/login", overrides="shared/cap-aaa111", Status="Missing")
    assert store(child).get("auth/login").status == "Missing"
    assert store(child).check() == []


def test_get_by_id_local(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Supported")
    assert store(root).get_by_id("cap-x").path == "x"


# ── set on an inherited path: materialize the override (issue #3) ────────────

def ov_meta(child: Path, path: str) -> dict:
    return yaml.safe_load((child / "docs" / "capabilities" / path / "meta.yaml")
                          .read_text())


def test_set_inherited_qualified(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    cap = store(child).set("shared/moderation/report-content", {"Status": "Missing"})
    assert cap.status == "Missing" and cap.origin == "shared"
    assert store(child).get("moderation/report-content").status == "Missing"
    assert store(base).get("moderation/report-content").status == "Supported"


def test_set_inherited_bare(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("moderation/report-content", {"Status": "Missing"})
    assert store(child).get("moderation/report-content").status == "Missing"


def test_set_inherited_materializes_mirrored_override(tmp_path):
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("moderation/report-content", {"Status": "Missing"})
    assert ov_meta(child, "moderation/report-content") == {
        "overrides": "shared/cap-aaa111", "Status": "Missing"}
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
        "overrides": "shared/cap-aaa111", "Status": "Partial", "Gaps": "half done"}
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
    assert store(child).get("auth/login").status == "Partial"


def test_set_local_unchanged_by_override_machinery(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Missing")
    cap = store(root).set("x", {"Status": "Supported"})
    assert cap.status == "Supported" and cap.origin == "local"
    assert "overrides" not in ov_meta(root, "x")


def test_set_inherited_validates_status(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    with pytest.raises(ValueError, match="invalid Status"):
        store(child).set("auth/login", {"Status": "Bogus"})
    with pytest.raises(ValueError, match="unknown field"):
        store(child).set("auth/login", {"Nonsense": "x"})
    assert not (child / "docs" / "capabilities" / "auth" / "login").exists()


def test_set_unknown_path_still_raises(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    with pytest.raises(ValueError, match="no such capability"):
        store(child).set("nope/missing", {"Status": "Missing"})


def test_set_inherited_falls_back_when_local_occupies_path(tmp_path):
    """`alias/x/y` addressed explicitly while a local `x/y` also exists: mirror
    to `<alias>/x/y` instead — never clobber the local declaration, and never
    refuse a path `show` accepts."""
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    write_cap(child, "auth/login", id="cap-loc001", Status="Missing")
    before = (child / "docs" / "capabilities" / "auth" / "login" / "meta.yaml").read_bytes()

    store(child).set("shared/auth/login", {"Status": "Partial", "Gaps": "wip"})

    assert (child / "docs" / "capabilities" / "auth" / "login"
            / "meta.yaml").read_bytes() == before          # local untouched
    assert ov_meta(child, "shared/auth/login") == {
        "overrides": "shared/cap-aaa111", "Status": "Partial", "Gaps": "wip"}
    assert store(child).get("shared/auth/login").status == "Partial"
    assert store(child).get("auth/login").status == "Missing"   # bare wins local
    assert store(child).check() == []


def test_set_second_alias_same_path(tmp_path):
    """Two aliases exporting the same path: the first override occupies the
    mirrored path, so the second must qualify rather than become un-settable."""
    base = repo(tmp_path, "base")
    write_cap(base, "a/thing", id="cap-one", Status="Supported")
    base2 = repo(tmp_path, "base2")
    write_cap(base2, "a/thing", id="cap-two", Status="Supported")
    child = repo(tmp_path, "child")
    st = FsCapabilitiesStore.open(child)
    st.extends_add("one", "../base")
    st.extends_add("two", "../base2")

    store(child).set("one/a/thing", {"Status": "Missing"})
    store(child).set("two/a/thing", {"Status": "Omitted"})

    assert store(child).get("one/a/thing").status == "Missing"
    assert store(child).get("two/a/thing").status == "Omitted"
    assert ov_meta(child, "a/thing")["overrides"] == "one/cap-one"
    assert ov_meta(child, "two/a/thing")["overrides"] == "two/cap-two"
    assert store(child).check() == []
    # Re-entrant: each updates its own override in place.
    store(child).set("two/a/thing", {"Status": "Partial", "Gaps": "x"})
    assert store(child).get("two/a/thing").status == "Partial"
    assert store(child).get("one/a/thing").status == "Missing"


def test_set_ambiguous_bare_ref_raises(tmp_path):
    base = repo(tmp_path, "base")
    write_cap(base, "a/thing", id="cap-one", Status="Supported")
    base2 = repo(tmp_path, "base2")
    write_cap(base2, "a/thing", id="cap-two", Status="Supported")
    child = repo(tmp_path, "child")
    st = FsCapabilitiesStore.open(child)
    st.extends_add("one", "../base")
    st.extends_add("two", "../base2")
    with pytest.raises(AmbiguousRef):
        store(child).set("a/thing", {"Status": "Missing"})


def test_set_inherited_null_clears_inherited_field(tmp_path):
    """None on an override writes explicit YAML null (clear), not a pop —
    popping would silently mean 're-inherit', a different intent."""
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported", "Priority": "P1"}})
    store(child).set("auth/login", {"Priority": None})
    assert ov_meta(child, "auth/login") == {"overrides": "shared/cap-aaa111",
                                            "Priority": None}
    assert "Priority" not in store(child).get("auth/login").fields
    assert store(child).get("auth/login").status == "Supported"   # rest inherited


def test_set_local_null_pops_field(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Supported", Priority="P1")
    store(root).set("x", {"Priority": None})
    assert "Priority" not in ov_meta(root, "x")


def test_remove_inherited_still_refuses_after_override(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    store(child).set("auth/login", {"Status": "Missing"})
    with pytest.raises(ValueError, match="cannot remove inherited"):
        store(child).remove("auth/login")


# ── unreviewed vs decided (drift mechanism 2) ────────────────────────────────

def test_unreviewed_bare_inherited(tmp_path):
    base, child = child_of(tmp_path, {
        "auth/login": {"id": "cap-aaa111", "Status": "Supported"}})
    unreviewed = {c.qualified for c in store(child).unreviewed_inherited()}
    assert unreviewed == {"shared/auth/login"}


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
    unreviewed = {c.qualified for c in store(child).unreviewed_inherited()}
    assert unreviewed == {"shared/auth/login"}


def test_local_capability_never_unreviewed(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x", id="cap-x", Status="Missing")
    assert store(root).unreviewed_inherited() == []
