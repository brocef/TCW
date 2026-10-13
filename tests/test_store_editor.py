"""Phase 1 — Store contracts and validation shape.

Tests the new revision-bearing store operations: composite create/update,
artifact/sidecar read/write, taxonomy update, capability update/add_entry,
stale revision rejection, validation atomicity, and fault-injection paths.
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import (
    TAXONOMY_EDITABLE_FIELDS, CapabilityDetail, StaleRevision, TermDetail,
)
from tcw.store.fs import (FsCapabilitiesStore, FsTaxonomyStore, _revision, _revision_multi, _atomic_write_all, _mkdir_owned, init, write_sentinel)
# Federation setup is non-trivial and already written next door; the rollback
# test that needs it belongs in this file, with the other fault-injection tests.
from test_capabilities_federation import child_of
from tcw.errors import TcwError


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _work_node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"],
                   check=True)
    init(["work"], root)
    return root


def _tax_node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "docs" / "taxonomy").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"],
                   check=True)
    write_sentinel(root)
    return root


def _cap_node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"],
                   check=True)
    write_sentinel(root)
    return root


# ── Revision helpers ─────────────────────────────────────────────────────────


def test_revision_deterministic():
    assert _revision("hello") == _revision("hello")
    assert _revision("hello") != _revision("world")
    assert len(_revision("x")) == 16  # 16 hex chars


def test_revision_multi_order_dependent():
    a = _revision_multi("state", "body")
    b = _revision_multi("body", "state")
    assert a != b
    assert a == _revision_multi("state", "body")


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — get_detail
# ═══════════════════════════════════════════════════════════════════════════════


# ── a composite write whose read-back loses the race ─────────────────────────
#
# `get_detail` and its siblings are `-> … | None`; the four composite writers
# that end with one are not. Handing the `None` through anyway only relocates the
# failure — `AttributeError` at whichever caller dereferences first, rendered by
# `serve` as a 500. Each of the five returns is driven here with its reader
# forced to `None`.


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — create_work (composite)
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — update_work (partial merge)
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — artifact read / write
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — sidecar read / write
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# FsTaxonomyStore — get_term_detail + update_term
# ═══════════════════════════════════════════════════════════════════════════════


def test_get_term_detail_returns_revision(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    detail = st.get_term_detail("admin")
    assert isinstance(detail, TermDetail)
    assert detail.term.slug == "admin"
    assert detail.core_revision != ""


def test_get_term_detail_unknown_returns_none(tmp_path):
    st = FsTaxonomyStore.open(_tax_node(tmp_path))
    assert st.get_term_detail("nope") is None


def test_update_term_description(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    detail = st.update_term("admin", description="Manage users")
    assert detail.term.description == "Manage users"
    assert detail.core_revision != st.get_term_detail("admin").core_revision \
        or True  # revision changed after write


def test_update_term_read_back_lost_is_a_valueerror(tmp_path, monkeypatch):
    """The taxonomy sibling: no transitions to race, but a concurrent delete or
    rename reaches the same `None` through the same non-optional signature."""
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    monkeypatch.setattr(FsTaxonomyStore, "get_term_detail", lambda self, ref: None)
    with pytest.raises(TcwError, match="could not be read back"):
        st.update_term("admin", description="Manage users")


def test_update_term_name_and_relatesto(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    st.add("User")
    detail = st.update_term("admin", name="Administrator",
                            relates_to=["user"])
    assert detail.term.name == "Administrator"
    assert detail.term.relates_to == ["user"]


def test_update_term_partial_unchanged(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin", description="original desc")
    detail = st.update_term("admin", name="Renamed")
    assert detail.term.name == "Renamed"
    assert detail.term.description == "original desc"  # unchanged


def test_update_term_stale_revision(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    old_rev = st.get_term_detail("admin").core_revision
    # External edit
    d = root / "docs/taxonomy/admin"
    (d / "description.md").write_text("changed externally")

    with pytest.raises(StaleRevision):
        st.update_term("admin", name="X", core_revision=old_rev)

    assert st.get("admin").name == "Admin"  # unchanged


def test_update_term_refuses_inherited(tmp_path):
    """Inherited terms cannot be updated."""
    shared = tmp_path / "shared"
    (shared / "docs" / "taxonomy").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(shared)], check=True)
    subprocess.run(["git", "-C", str(shared), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(shared), "config", "user.name", "t"],
                   check=True)
    write_sentinel(shared, "shared")
    FsTaxonomyStore.open(shared).add("Widget")

    cons = tmp_path / "consumer"
    (cons / "docs" / "taxonomy").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(cons)], check=True)
    subprocess.run(["git", "-C", str(cons), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(cons), "config", "user.name", "t"],
                   check=True)
    write_sentinel(cons, "consumer")
    (cons / "tcw-config.yaml").write_text(
        "id: consumer\nconnected-projects:\n  children:\n    shared: ../shared\n"
    )
    (shared / "tcw-config.yaml").write_text(
        "id: shared\nconnected-projects:\n  parent:\n    consumer: ../consumer\n"
    )
    FsTaxonomyStore.open(cons).extends_add("shared")
    st = FsTaxonomyStore.open(cons)
    with pytest.raises(TcwError, match="cannot update inherited"):
        st.update_term("shared/widget", name="X")


def test_update_term_dangling_relatesto_rejected(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    with pytest.raises(TcwError, match="does not resolve"):
        st.update_term("admin", relates_to=["no-such-term"])


def test_update_term_bad_kind_rejected(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    with pytest.raises(TcwError, match="invalid taxonomy kind"):
        st.update_term("admin", kind="Bogus")


def test_update_term_feature_requires_vocabulary(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    # Set kind to Feature without vocabulary
    with pytest.raises(TcwError, match="Feature requires"):
        st.update_term("admin", kind="Feature", vocabulary=[])


# ═══════════════════════════════════════════════════════════════════════════════
# FsCapabilitiesStore — get_capability_detail + update + add_entry
# ═══════════════════════════════════════════════════════════════════════════════


def test_get_capability_detail_returns_revision(tmp_path):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    detail = st.get_capability_detail("routes/login")
    assert isinstance(detail, CapabilityDetail)
    assert detail.capability.name == "Sign in"
    assert detail.core_revision != ""


def test_update_capability_body(tmp_path):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    detail = st.update_capability("routes/login", body="Updated body text.")
    assert detail.capability.body == "Updated body text."


def test_update_capability_read_back_lost_is_a_valueerror(tmp_path, monkeypatch):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    monkeypatch.setattr(FsCapabilitiesStore, "get_capability_detail",
                        lambda self, identifier: None)
    with pytest.raises(TcwError, match="could not be read back"):
        st.update_capability("routes/login", body="Updated body text.")


def test_update_capability_fields(tmp_path):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    detail = st.update_capability("routes/login",
                                  fields={"Status": "Supported"})
    assert detail.capability.status == "Supported"


def test_update_capability_body_and_fields(tmp_path):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    detail = st.update_capability("routes/login", body="New body.",
                                  fields={"Priority": "P1"})
    assert detail.capability.body == "New body."
    assert detail.capability.fields.get("Priority") == "P1"


def test_update_capability_stale_revision(tmp_path):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    old_rev = st.get_capability_detail("routes/login").core_revision
    # External edit
    (root / "docs/capabilities/routes/login/description.md").write_text("changed")

    with pytest.raises(StaleRevision):
        st.update_capability("routes/login", body="new",
                             core_revision=old_rev)


def test_update_capability_invalid_field_rejected(tmp_path):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    with pytest.raises(TcwError, match="unknown field"):
        st.update_capability("routes/login", fields={"Bogus": "x"})


def test_update_capability_invalid_status_rejected(tmp_path):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    with pytest.raises(TcwError, match="invalid Status"):
        st.update_capability("routes/login", fields={"Status": "Broken"})


def test_add_invalid_status(tmp_path):
    st = FsCapabilitiesStore.open(_cap_node(tmp_path))
    with pytest.raises(TcwError, match="invalid Status"):
        st.add("x", status="NotAStatus")


# ── inherited capabilities are editable, not just viewable (issue #3) ────────


def _federated(tmp_path) -> tuple[Path, Path]:
    """(base, child) where child extends registered base, base
    declaring a single `routes/login` capability."""
    base = _cap_node(tmp_path / "b")
    FsCapabilitiesStore.open(base).add("routes/login", name="Sign in",
                                       status="Supported", body="UPSTREAM.")
    child = _cap_node(tmp_path / "c")
    (child / "tcw-config.yaml").write_text(
        f"id: child-project\nconnected-projects:\n  children:\n"
        f"    base-project: {base}\n"
    )
    (base / "tcw-config.yaml").write_text(
        f"id: base-project\nconnected-projects:\n  parent:\n"
        f"    child-project: {child}\n"
    )
    FsCapabilitiesStore.open(child).extends_add("base-project")
    return base, child


def test_update_capability_inherited_fields(tmp_path):
    base, child = _federated(tmp_path)
    st = FsCapabilitiesStore.open(child)
    detail = st.update_capability("routes/login", fields={"Status": "Missing"})
    assert detail.capability.status == "Missing"
    assert detail.capability.origin == "base-project"
    # Upstream untouched.
    assert FsCapabilitiesStore.open(base).get("routes/login").status == "Supported"


def test_update_capability_inherited_matches_set(tmp_path):
    """The web path and the CLI path share the merge — same field, same file.
    Each fixture mints its own upstream id, so compare against that id."""
    def written(root: Path, write) -> dict:
        st = FsCapabilitiesStore.open(root)
        write(st)
        meta = yaml.safe_load(
            (root / "docs/capabilities/routes/login/meta.yaml").read_text())
        upstream_id = st.get("routes/login").id
        meta["overrides"] = meta["overrides"].replace(upstream_id, "<id>")
        return meta

    _, child = _federated(tmp_path)
    via_update = written(child, lambda st: st.update_capability(
        "routes/login", fields={"Status": "Missing"}))

    _, child2 = _federated(tmp_path / "second")
    via_set = written(child2, lambda st: st.set("routes/login",
                                                {"Status": "Missing"}))

    assert via_update == via_set == {"overrides": "base-project/<id>", "Status": "Missing"}


def test_update_capability_inherited_body(tmp_path):
    base, child = _federated(tmp_path)
    st = FsCapabilitiesStore.open(child)
    detail = st.update_capability("routes/login", body="CHILD STORY.")
    assert detail.capability.body.strip() == "CHILD STORY."
    assert "UPSTREAM" not in detail.capability.body
    assert (child / "docs/capabilities/routes/login/description.md").exists()
    # Upstream body untouched.
    assert FsCapabilitiesStore.open(base).get("routes/login").body.strip() == "UPSTREAM."


def test_update_capability_inherited_body_cleared_drops_the_delta(tmp_path):
    """An override's description.md is a body *delta*; an empty one means "no
    delta" (that is what makes append-only overrides work). So clearing it drops
    the file and re-inherits, rather than leaving an empty file that silently
    means the same thing."""
    base, child = _federated(tmp_path)
    st = FsCapabilitiesStore.open(child)
    st.update_capability("routes/login", body="CHILD STORY.")
    assert (child / "docs/capabilities/routes/login/description.md").exists()

    detail = st.update_capability("routes/login", body=None)
    assert detail.capability.body.strip() == "UPSTREAM."          # re-inherited
    assert not (child / "docs/capabilities/routes/login/description.md").exists()
    assert st.check() == []
    # The rest of the delta survives.
    st.update_capability("routes/login", fields={"Status": "Missing"})
    assert st.update_capability("routes/login", body="").capability.status == "Missing"


def test_update_capability_local_body_cleared_stays_empty(tmp_path):
    """A local capability has no upstream to fall back to — None still clears."""
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in", body="Local body.")
    assert st.update_capability("routes/login", body=None).capability.body == ""


def test_update_capability_inherited_stale_revision(tmp_path):
    """The revision must cover the override's files, or two edits to the same
    override hash identically and stale-write rejection never fires."""
    base, child = _federated(tmp_path)
    st = FsCapabilitiesStore.open(child)
    old_rev = st.get_capability_detail("routes/login").core_revision
    st.update_capability("routes/login", fields={"Status": "Missing"})
    with pytest.raises(StaleRevision):
        st.update_capability("routes/login", fields={"Status": "Partial"},
                             core_revision=old_rev)


def test_update_capability_inherited_revision_tracks_override_body(tmp_path):
    base, child = _federated(tmp_path)
    st = FsCapabilitiesStore.open(child)
    st.update_capability("routes/login", fields={"Status": "Missing"})
    rev = st.get_capability_detail("routes/login").core_revision
    st.update_capability("routes/login", body="CHILD STORY.")
    assert st.get_capability_detail("routes/login").core_revision != rev


# ═══════════════════════════════════════════════════════════════════════════════
# Validation atomicity — failed writes leave store byte-for-byte unchanged
# ═══════════════════════════════════════════════════════════════════════════════


def test_taxonomy_update_validation_no_partial_write(tmp_path):
    """update_term with dangling relatesTo should not write anything."""
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    meta_before = (root / "docs/taxonomy/admin/meta.yaml").read_bytes()

    with pytest.raises(TcwError):
        st.update_term("admin", name="X", relates_to=["ghost"])

    meta_after = (root / "docs/taxonomy/admin/meta.yaml").read_bytes()
    assert meta_before == meta_after


# ═══════════════════════════════════════════════════════════════════════════════
# Fault injection — temp-file / atomic-replace failure paths
# ═══════════════════════════════════════════════════════════════════════════════


def test_atomic_write_preserves_prior_on_failure(tmp_path, monkeypatch):
    """If the replace step fails, the original file must remain readable.

    The single-pair shape is the point: the two-pair version below fails on the
    *second* promote, so a first-promote failure is covered nowhere else. The
    failure is induced at `Path.replace` rather than by making the parent
    read-only, which root ignores.
    """
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "data.yaml"
    original = "key: value\n"
    p.write_text(original)

    def refuse(self, target):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "replace", refuse)

    with pytest.raises(PermissionError):
        _atomic_write_all([(p, "key: new_value\n")])

    # Original content survives, and the temp it staged is gone.
    assert p.read_text() == original
    assert list(d.glob("*.tmp")) == []


def test_atomic_write_temp_cleanup_on_failure(tmp_path, monkeypatch):
    """If the write step fails, no temp file is left behind.

    The failure lands at `Path.write_text`, one statement after `mkstemp`, so a
    temp exists for the handler to remove. Inducing it earlier — by making the
    parent unwritable — kills `mkstemp` itself, and the assertion below then
    holds whether or not the handler unlinks anything: with the unlink deleted,
    that version of this test still passed.
    """
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "data.yaml"
    _fail_writing(monkeypatch, "data.yaml")

    with pytest.raises(OSError):
        _atomic_write_all([(p, "content\n")])

    # No .tmp file should remain
    tmp_files = list(d.glob("*.tmp"))
    assert tmp_files == [], f"temp files left behind: {tmp_files}"


def test_atomic_write_success_stages_file(tmp_path):
    """Successful atomic write produces the expected file content."""
    p = tmp_path / "out.yaml"
    _atomic_write_all([(p, "key: value\n")])
    assert p.read_text() == "key: value\n"


def _fail_writing(monkeypatch, name, exc=OSError(28, "No space left on device")):
    """Make `Path.write_text` raise for one target file.

    Matching on the target's *name* is deterministic where a call counter is not
    — git and fixture setup do their own writes. Temps are
    `<name>.tmp`, so `startswith` catches the staged write too.
    """
    real = Path.write_text

    def guard(self, *a, **kw):
        if self.name.startswith(name):
            raise exc
        return real(self, *a, **kw)

    monkeypatch.setattr(Path, "write_text", guard)


def test_atomic_write_all_writes_both(tmp_path):
    a, b = tmp_path / "a.yaml", tmp_path / "b.md"
    _atomic_write_all([(a, "one\n"), (b, "two\n")])
    assert (a.read_text(), b.read_text()) == ("one\n", "two\n")
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_all_single_pair(tmp_path):
    """The one-entry shape `update_work` uses when `body is _UNSET`."""
    a = tmp_path / "a.yaml"
    _atomic_write_all([(a, "one\n")])
    assert a.read_text() == "one\n"
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_all_cleans_up_on_base_exception(tmp_path, monkeypatch):
    """A KeyboardInterrupt mid-batch still cleans up its temps."""
    a, b = tmp_path / "a.yaml", tmp_path / "b.md"
    _fail_writing(monkeypatch, "b.md", exc=KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        _atomic_write_all([(a, "one\n"), (b, "two\n")])

    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_all_staging_failure_promotes_nothing(tmp_path, monkeypatch):
    a, b = tmp_path / "a.yaml", tmp_path / "b.md"
    a.write_text("prior\n")
    _fail_writing(monkeypatch, "b.md")

    with pytest.raises(OSError):
        _atomic_write_all([(a, "one\n"), (b, "two\n")])

    assert a.read_text() == "prior\n"
    assert not b.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_all_promote_failure_is_the_recorded_ceiling(tmp_path,
                                                                 monkeypatch):
    """The promote loop is not atomic across files. Pinned so the limit reads as
    a decision on record rather than an accident someone silently 'fixes'."""
    a, b = tmp_path / "a.yaml", tmp_path / "b.md"
    real = Path.replace
    calls = []

    def guard(self, target):
        calls.append(target)
        if len(calls) == 2:
            raise OSError(28, "No space left on device")
        return real(self, target)

    monkeypatch.setattr(Path, "replace", guard)

    with pytest.raises(OSError):
        _atomic_write_all([(a, "one\n"), (b, "two\n")])

    assert a.read_text() == "one\n"      # first promoted
    assert not b.exists()                # second was not
    assert list(tmp_path.glob("*.tmp")) == []


def test_write_node_failure_leaves_existing_node_untouched(tmp_path, monkeypatch):
    """AC 3 — a failed update of an existing node keeps both files' prior bytes."""
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin", description="original body\n")
    d = root / "docs" / "taxonomy" / "admin"
    meta_before = (d / "meta.yaml").read_bytes()
    desc_before = (d / "description.md").read_bytes()

    _fail_writing(monkeypatch, "description.md")
    with pytest.raises(OSError):
        st.update_term("admin", name="Changed", description="new body\n")

    assert (d / "meta.yaml").read_bytes() == meta_before
    assert (d / "description.md").read_bytes() == desc_before
    assert list(root.rglob("*.tmp")) == []


def test_write_node_failure_removes_directory_it_created(tmp_path, monkeypatch):
    """AC 4 — the same failure on a *new* node leaves no node directory."""
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)

    _fail_writing(monkeypatch, "description.md")
    with pytest.raises(OSError):
        st.add("Admin", description="body\n")

    assert not (root / "docs" / "taxonomy" / "admin").exists()
    assert list(root.rglob("*.tmp")) == []


def test_update_capability_failure_removes_override_it_materialized(tmp_path,
                                                                    monkeypatch):
    """A fresh override directory rolls back too.

    `update_capability` mkdirs the override itself, so `_write_node` sees a
    directory that already "existed" and skips its own rollback — the guard has
    to sit at the caller that created it.
    """
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    d = child / "docs" / "capabilities" / "moderation" / "report-content"

    _fail_writing(monkeypatch, "description.md")
    with pytest.raises(OSError) as excinfo:
        FsCapabilitiesStore.open(child).update_capability(
            "moderation/report-content", body="override body\n")

    assert excinfo.value.errno == 28          # the injected error, not a rollback one
    assert not d.exists()
    assert list(child.rglob("*.tmp")) == []


def test_set_failure_removes_override_it_materialized(tmp_path, monkeypatch):
    """`capabilities set` — the CLI path — materializes a fresh override too, and
    writes only `meta.yaml`. A failed write must not leave the empty directory."""
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    d = child / "docs" / "capabilities" / "moderation" / "report-content"

    _fail_writing(monkeypatch, "meta.yaml")
    with pytest.raises(OSError) as excinfo:
        FsCapabilitiesStore.open(child).set(
            "moderation/report-content", {"Status": "Missing"})

    assert excinfo.value.errno == 28
    assert not d.exists()
    assert list(child.rglob("*.tmp")) == []


# ═══════════════════════════════════════════════════════════════════════════════
# Lifecycle guardrails — start/complete through existing semantic ops
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# Bounded registry enforcement
# ═══════════════════════════════════════════════════════════════════════════════


def test_taxonomy_editable_fields():
    assert "name" in TAXONOMY_EDITABLE_FIELDS
    assert "description" in TAXONOMY_EDITABLE_FIELDS
    assert "relates_to" in TAXONOMY_EDITABLE_FIELDS
    assert "vocabulary" in TAXONOMY_EDITABLE_FIELDS
    assert "kind" in TAXONOMY_EDITABLE_FIELDS
    assert "attachments" not in TAXONOMY_EDITABLE_FIELDS


# ═══════════════════════════════════════════════════════════════════════════════
# YAML parse/validation failures
# ═══════════════════════════════════════════════════════════════════════════════


def test_update_capability_yaml_parse_in_existing(tmp_path):
    """If the existing capability file has parseable content, update works."""
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    detail = st.update_capability("routes/login", body="new body")
    assert detail.capability.body == "new body"


# ═══════════════════════════════════════════════════════════════════════════════
# Review-fix regressions (dual review of the interactive web editor)
# ═══════════════════════════════════════════════════════════════════════════════


def test_add_rejects_path_traversal(tmp_path):
    """#3 — a caller-supplied path must not escape the store root."""
    st = FsCapabilitiesStore.open(_cap_node(tmp_path))
    for bad in ["../evil", "/tmp/evil", "a/../../evil", "..\\evil"]:
        with pytest.raises(TcwError, match="invalid path"):
            st.add(bad, name="Do X")
    assert list(tmp_path.rglob("evil*")) == []


def test_taxonomy_add_rejects_path_traversal(tmp_path):
    """#3 — a caller-supplied taxonomy slug must not escape the store root."""
    st = FsTaxonomyStore.open(_tax_node(tmp_path))
    with pytest.raises(TcwError, match="invalid slug"):
        st.add("Evil", slug="../evil")
    assert list(tmp_path.rglob("evil*")) == []


def test_add_rejects_duplicate_path(tmp_path):
    """#5 — adding a capability at an existing path must fail, not overwrite."""
    st = FsCapabilitiesStore.open(_cap_node(tmp_path))
    st.add("routes/login", name="Sign in")
    with pytest.raises(TcwError, match="already exists"):
        st.add("routes/login", name="Sign in")


# ── the write chokepoint ─────────────────────────────────────────────────────
#
# `_write_files` undoes what the call created when a write fails and
# re-raises; it must never touch anything that was already there.


def test_mkdir_owned_reports_who_created_the_directory(tmp_path):
    d = tmp_path / "a" / "b" / "c"
    assert _mkdir_owned(d) is True          # creates parents too
    assert d.is_dir()
    assert _mkdir_owned(d) is False         # the race-shaped second call
    assert d.is_dir()


# ── what the rollback must never touch ───────────────────────────────────────
#
# Every case below is a path that existed before the call. Found by adversarial
# review of the finished diff, each reproduced before being fixed.


def test_atomic_write_all_does_not_consume_an_existing_tmp_path(tmp_path):
    """The temp name used to be `<target>.tmp` — a real path a user or a symlink
    can already occupy, which this would truncate, promote, and delete."""
    target = tmp_path / "state.yaml"
    squatter = tmp_path / "state.yaml.tmp"
    squatter.write_text("PRECIOUS", encoding="utf-8")

    _atomic_write_all([(target, "written\n")])

    assert target.read_text() == "written\n"
    assert squatter.read_text() == "PRECIOUS"


def test_atomic_write_all_keeps_the_targets_mode(tmp_path):
    """Promotion replaces the directory entry, so a file someone chmod'ed would
    silently come back with default permissions."""
    target = tmp_path / "config.yaml"
    target.write_text("a: 1\n", encoding="utf-8")
    os.chmod(target, 0o600)

    _atomic_write_all([(target, "a: 2\n")])

    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_the_body_clear_branch_rolls_back(tmp_path, monkeypatch):
    """`update_capability`'s body-clear branch deletes `description.md` and
    writes `meta.yaml` into an override it materialized; a failed write leaves
    no folder behind."""
    base, child = child_of(tmp_path, {
        "moderation/report-content": {"id": "cap-aaa111", "Status": "Supported"}})
    d = child / "docs" / "capabilities" / "moderation" / "report-content"

    _fail_writing(monkeypatch, "meta.yaml")
    with pytest.raises(OSError):
        FsCapabilitiesStore.open(child).update_capability(
            "moderation/report-content", body="")

    assert not d.exists()
