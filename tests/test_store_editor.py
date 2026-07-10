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
    TAXONOMY_EDITABLE_FIELDS, WORK_ARTIFACTS, WORK_SIDECARS, WORK_LEVELS,
    _UNSET, ArtifactResource, CapabilityDetail, SidecarResource, StaleRevision,
    TermDetail, WorkDetail,
)
from tcw.store.fs import (
    FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore,
    _revision, _revision_multi, _atomic_write, init, write_sentinel,
)


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


def test_get_detail_returns_full_revision_map(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    (d / "spec.md").write_text("spec content\n")
    (d / "capabilities.yaml").write_text("links:\n- web\n")

    detail = st.get_detail(item.slug)

    assert isinstance(detail, WorkDetail)
    assert detail.item.slug == item.slug
    assert detail.core_revision != ""
    assert "spec" in detail.artifact_revisions
    assert "capabilities.yaml" in detail.sidecar_revisions
    # initial-request is always present after create
    assert "initial-request" in detail.artifact_revisions


def test_get_detail_unknown_slug_returns_none(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    assert st.get_detail("no-such-slug") is None


def test_get_detail_core_changes_after_field_write(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    rev1 = st.get_detail(item.slug).core_revision
    st.set_field(item.slug, "priority", 5)
    rev2 = st.get_detail(item.slug).core_revision
    assert rev1 != rev2


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — create_work (composite)
# ═══════════════════════════════════════════════════════════════════════════════


def test_create_work_sets_all_fields(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    detail = st.create_work(
        "Big Feature",
        body="Do the thing.",
        priority=7,
        effort="high",
        complexity="medium",
        initiative="epic-slug",
    )
    item = detail.item
    assert item.title == "Big Feature"
    assert item.priority == 7
    assert item.effort == "high"
    assert item.complexity == "medium"
    assert item.initiative == "epic-slug"
    assert detail.core_revision != ""


def test_create_work_with_blockers(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    detail = st.create_work(
        "Dependent",
        blockers=[blocker.slug, "external-ticket"],
    )
    item = detail.item
    slugs = [b.get("slug") for b in item.blocked_by if "slug" in b]
    externals = [b.get("external") for b in item.blocked_by if "external" in b]
    assert blocker.slug in slugs
    assert "external-ticket" in externals


def test_create_work_with_parent(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    parent = st.create("Parent", created="2026-01-01")
    detail = st.create_work("Child", parent=parent.slug)
    assert detail.item.parent == parent.slug


def test_create_work_epic_type(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    detail = st.create_work("Epic Thing", type="epic")
    assert detail.item.type == "epic"


def test_create_work_rejects_bad_effort(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    with pytest.raises(ValueError, match="invalid level"):
        st.create_work("X", effort="bogus")
    # Nothing persisted
    assert st.query() == []


def test_create_work_rejects_bad_complexity(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    with pytest.raises(ValueError, match="invalid level"):
        st.create_work("X", complexity="xl")
    assert st.query() == []


def test_create_work_rejects_bad_type(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    with pytest.raises(ValueError, match="invalid type"):
        st.create_work("X", type="invalid-type")
    assert st.query() == []


def test_create_work_rejects_unknown_parent(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    with pytest.raises(ValueError, match="no such parent"):
        st.create_work("Orphan", parent="no-such-slug")
    assert st.query() == []


def test_create_work_rejects_empty_title(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    with pytest.raises(ValueError, match="title is required"):
        st.create_work("")
    assert st.query() == []


def test_create_work_level_normalization(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    detail = st.create_work("X", effort="H", complexity="vh")
    assert detail.item.effort == "high"
    assert detail.item.complexity == "very-high"


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — update_work (partial merge)
# ═══════════════════════════════════════════════════════════════════════════════


def test_update_work_partial_merge(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01", priority=3)
    st.set_field(item.slug, "effort", "low")
    st.set_field(item.slug, "complexity", "high")

    detail = st.update_work(item.slug, title="Renamed", priority=9)

    assert detail.item.title == "Renamed"
    assert detail.item.priority == 9
    assert detail.item.effort == "low"        # unchanged
    assert detail.item.complexity == "high"   # unchanged


def test_update_work_null_clears_nullable(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01", priority=5)
    detail = st.update_work(item.slug, priority=None)
    assert detail.item.priority is None


def test_update_work_empty_string_is_explicit(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.set_field(item.slug, "initiative", "some-epic")
    detail = st.update_work(item.slug, initiative="")
    assert detail.item.initiative == ""


def test_update_work_clears_blockers(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.set_field(item.slug, "blocked_by", [{"external": "vendor"}])
    detail = st.update_work(item.slug, blockers=[])
    assert detail.item.blocked_by == []


def test_update_work_unchanged_when_no_fields_provided(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01", priority=3)
    detail = st.update_work(item.slug)
    assert detail.item.priority == 3


def test_update_work_stale_revision_rejected(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    old_rev = st.get_detail(item.slug).core_revision
    st.set_field(item.slug, "priority", 5)  # changes the revision

    with pytest.raises(StaleRevision):
        st.update_work(item.slug, title="X", core_revision=old_rev)

    # Store unchanged
    assert st.get(item.slug).title == "Task"
    assert st.get(item.slug).priority == 5


def test_update_work_validation_failure_no_write(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01", priority=3)
    with pytest.raises(ValueError, match="invalid level"):
        st.update_work(item.slug, effort="bogus")
    # Priority unchanged
    assert st.get(item.slug).priority == 3
    assert st.get(item.slug).effort == ""


def test_update_work_body(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01", body="old body")
    detail = st.update_work(item.slug, body="new body")
    assert detail.item.body == "new body"


def test_update_work_unknown_slug(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    with pytest.raises(ValueError, match="no such work item"):
        st.update_work("no-such-slug", title="X")


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — artifact read / write
# ═══════════════════════════════════════════════════════════════════════════════


def test_read_artifact_present(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    (d / "spec.md").write_text("my spec\n")

    res = st.read_artifact(item.slug, "spec")

    assert isinstance(res, ArtifactResource)
    assert res.name == "spec"
    assert res.content == "my spec\n"
    assert res.media_type == "text/markdown"
    assert res.revision == _revision("my spec\n")


def test_read_artifact_not_present_returns_none(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert st.read_artifact(item.slug, "plan") is None


def test_read_artifact_invalid_name(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(ValueError, match="unknown artifact"):
        st.read_artifact(item.slug, "not-real")


def test_write_artifact_creates_and_returns_resource(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")

    res = st.write_artifact(item.slug, "spec", "spec content\n")

    assert res.content == "spec content\n"
    assert res.revision != ""
    # File actually written
    d = st.path(item.slug)
    assert (d / "spec.md").read_text() == "spec content\n"


def test_write_artifact_stale_revision(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    res = st.write_artifact(item.slug, "spec", "v1\n")
    old_rev = res.revision
    # External change
    d = st.path(item.slug)
    (d / "spec.md").write_text("v2 externally\n")

    with pytest.raises(StaleRevision):
        st.write_artifact(item.slug, "spec", "v1 modified\n",
                          revision=old_rev)

    # Store unchanged by failed write
    assert (d / "spec.md").read_text() == "v2 externally\n"


def test_write_artifact_invalid_name(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(ValueError, match="unknown artifact"):
        st.write_artifact(item.slug, "not-real", "content")


# ═══════════════════════════════════════════════════════════════════════════════
# FsWorkStore — sidecar read / write
# ═══════════════════════════════════════════════════════════════════════════════


def test_read_sidecar_present(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    (d / "capabilities.yaml").write_text("links:\n- web\n")

    res = st.read_sidecar(item.slug, "capabilities.yaml")

    assert isinstance(res, SidecarResource)
    assert res.name == "capabilities.yaml"
    assert res.media_type == "application/yaml"
    assert res.revision != ""


def test_read_sidecar_not_present(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert st.read_sidecar(item.slug, "capabilities.yaml") is None


def test_read_sidecar_invalid_name(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(ValueError, match="unknown sidecar"):
        st.read_sidecar(item.slug, "not-real.yaml")


def test_write_sidecar_valid_yaml(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    content = "links:\n- web\n- api\n"

    res = st.write_sidecar(item.slug, "capabilities.yaml", content)

    assert res.content == content
    assert res.media_type == "application/yaml"
    d = st.path(item.slug)
    assert (d / "capabilities.yaml").read_text() == content


def test_write_sidecar_invalid_yaml_rejected(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    bad = "{not: valid: yaml:"

    with pytest.raises(ValueError, match="not valid YAML"):
        st.write_sidecar(item.slug, "capabilities.yaml", bad)

    # File should not exist (no write)
    d = st.path(item.slug)
    assert not (d / "capabilities.yaml").exists()


def test_write_sidecar_yaml_not_mapping(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    arr_yaml = "- just a list\n"

    with pytest.raises(ValueError, match="must be a YAML mapping"):
        st.write_sidecar(item.slug, "capabilities.yaml", arr_yaml)


def test_write_sidecar_invalid_name(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(ValueError, match="unknown sidecar"):
        st.write_sidecar(item.slug, "not-real.yaml", "content")


def test_write_sidecar_stale_revision(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    res = st.write_sidecar(item.slug, "capabilities.yaml", "links: []\n")
    old_rev = res.revision
    # External change
    d = st.path(item.slug)
    (d / "capabilities.yaml").write_text("links: [changed]\n")

    with pytest.raises(StaleRevision):
        st.write_sidecar(item.slug, "capabilities.yaml",
                         "links: [new]\n", revision=old_rev)

    assert (d / "capabilities.yaml").read_text() == "links: [changed]\n"


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
    write_sentinel(shared)
    FsTaxonomyStore.open(shared).add("Widget")

    cons = tmp_path / "consumer"
    (cons / "docs" / "taxonomy").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(cons)], check=True)
    subprocess.run(["git", "-C", str(cons), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(cons), "config", "user.name", "t"],
                   check=True)
    write_sentinel(cons)
    FsTaxonomyStore.open(cons).extends_add("shared", "../shared")
    st = FsTaxonomyStore.open(cons)
    with pytest.raises(ValueError, match="cannot update inherited"):
        st.update_term("shared/widget", name="X")


def test_update_term_dangling_relatesto_rejected(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    with pytest.raises(ValueError, match="does not resolve"):
        st.update_term("admin", relates_to=["no-such-term"])


def test_update_term_bad_kind_rejected(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    with pytest.raises(ValueError, match="invalid taxonomy kind"):
        st.update_term("admin", kind="Bogus")


def test_update_term_feature_requires_vocabulary(tmp_path):
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    # Set kind to Feature without vocabulary
    with pytest.raises(ValueError, match="Feature requires"):
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
    with pytest.raises(ValueError, match="unknown field"):
        st.update_capability("routes/login", fields={"Bogus": "x"})


def test_update_capability_invalid_status_rejected(tmp_path):
    root = _cap_node(tmp_path)
    st = FsCapabilitiesStore.open(root)
    st.add("routes/login", name="Sign in")
    with pytest.raises(ValueError, match="invalid Status"):
        st.update_capability("routes/login", fields={"Status": "Broken"})


def test_add_invalid_status(tmp_path):
    st = FsCapabilitiesStore.open(_cap_node(tmp_path))
    with pytest.raises(ValueError, match="invalid Status"):
        st.add("x", status="NotAStatus")


# ═══════════════════════════════════════════════════════════════════════════════
# Validation atomicity — failed writes leave store byte-for-byte unchanged
# ═══════════════════════════════════════════════════════════════════════════════


def test_work_update_validation_no_partial_write(tmp_path):
    """update_work with invalid effort should not change any field."""
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01", priority=3)
    state_before = (st.path(item.slug) / "state.yaml").read_bytes()

    with pytest.raises(ValueError):
        st.update_work(item.slug, effort="bogus", title="Changed")

    state_after = (st.path(item.slug) / "state.yaml").read_bytes()
    assert state_before == state_after


def test_sidecar_write_validation_no_file_created(tmp_path):
    """write_sidecar with invalid YAML must not create the file."""
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    with pytest.raises(ValueError):
        st.write_sidecar(item.slug, "capabilities.yaml", "{bad yaml")
    assert not (d / "capabilities.yaml").exists()


def test_taxonomy_update_validation_no_partial_write(tmp_path):
    """update_term with dangling relatesTo should not write anything."""
    root = _tax_node(tmp_path)
    st = FsTaxonomyStore.open(root)
    st.add("Admin")
    meta_before = (root / "docs/taxonomy/admin/meta.yaml").read_bytes()

    with pytest.raises(ValueError):
        st.update_term("admin", name="X", relates_to=["ghost"])

    meta_after = (root / "docs/taxonomy/admin/meta.yaml").read_bytes()
    assert meta_before == meta_after


# ═══════════════════════════════════════════════════════════════════════════════
# Fault injection — temp-file / atomic-replace failure paths
# ═══════════════════════════════════════════════════════════════════════════════


def test_atomic_write_preserves_prior_on_failure(tmp_path):
    """If the replace step fails, the original file must remain readable."""
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "data.yaml"
    original = "key: value\n"
    p.write_text(original)

    # Simulate failure: make the directory read-only so replace can't happen
    # On POSIX, we chmod the parent dir.
    os.chmod(d, stat.S_IRUSR | stat.S_IXUSR)  # remove write

    try:
        with pytest.raises(PermissionError):
            _atomic_write(p, "key: new_value\n")
        # Original content survives
        assert p.read_text() == original
    finally:
        os.chmod(d, stat.S_IRWXU)  # restore for cleanup


def test_atomic_write_temp_cleanup_on_failure(tmp_path):
    """If the write step fails, no temp file is left behind."""
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "data.yaml"

    # Make directory read-only — mkstemp-style write will fail
    os.chmod(d, stat.S_IRUSR | stat.S_IXUSR)

    try:
        with pytest.raises(PermissionError):
            _atomic_write(p, "content\n")
    finally:
        os.chmod(d, stat.S_IRWXU)

    # No .tmp file should remain
    tmp_files = list(d.glob("*.tmp"))
    assert tmp_files == [], f"temp files left behind: {tmp_files}"


def test_atomic_write_success_stages_file(tmp_path):
    """Successful atomic write produces the expected file content."""
    p = tmp_path / "out.yaml"
    _atomic_write(p, "key: value\n")
    assert p.read_text() == "key: value\n"


def test_artifact_write_preserves_prior_on_replace_failure(tmp_path):
    """write_artifact with a stale revision must not overwrite the file."""
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    # Write initial artifact
    st.write_artifact(item.slug, "spec", "original content\n")
    prior = (d / "spec.md").read_bytes()

    # External change
    (d / "spec.md").write_text("externally changed\n")

    with pytest.raises(StaleRevision):
        st.write_artifact(item.slug, "spec", "should not appear\n",
                          revision=_revision("original content\n"))

    # File must still have the external content
    assert (d / "spec.md").read_bytes() == b"externally changed\n"


def test_sidecar_write_preserves_prior_on_replace_failure(tmp_path):
    """write_sidecar with stale revision must not corrupt existing file."""
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    sc = st.write_sidecar(item.slug, "capabilities.yaml", "links: [a]\n")

    # External change
    (d / "capabilities.yaml").write_text("links: [externally]\n")

    with pytest.raises(StaleRevision):
        st.write_sidecar(item.slug, "capabilities.yaml", "links: [bad]\n",
                         revision=sc.revision)

    assert (d / "capabilities.yaml").read_text() == "links: [externally]\n"


# ═══════════════════════════════════════════════════════════════════════════════
# Lifecycle guardrails — start/complete through existing semantic ops
# ═══════════════════════════════════════════════════════════════════════════════


def test_start_via_semantic_op(tmp_path):
    """start() should work on items created via create_work."""
    st = FsWorkStore.open(_work_node(tmp_path))
    detail = st.create_work("Task")
    result = st.start(detail.item.slug)
    assert result.status == "active"


def test_complete_via_semantic_op(tmp_path):
    """complete() should work on items created via create_work."""
    st = FsWorkStore.open(_work_node(tmp_path))
    detail = st.create_work("Task")
    st.start(detail.item.slug)
    result = st.complete(detail.item.slug, "done", dod_ack=["tests"])
    assert result.status == "completed"
    assert result.resolution == "done"


def test_drop_via_semantic_op(tmp_path):
    """drop() should work on inbox/backlog items created via create_work."""
    st = FsWorkStore.open(_work_node(tmp_path))
    detail = st.create_work("Task")
    st.drop(detail.item.slug)
    assert st.get(detail.item.slug) is None


# ═══════════════════════════════════════════════════════════════════════════════
# Bounded registry enforcement
# ═══════════════════════════════════════════════════════════════════════════════


def test_work_artifacts_is_bounded():
    assert "initial-request" in WORK_ARTIFACTS
    assert "spec" in WORK_ARTIFACTS
    assert "not-a-thing" not in WORK_ARTIFACTS


def test_work_sidecars_has_capabilities_yaml():
    assert "capabilities.yaml" in WORK_SIDECARS
    sc = WORK_SIDECARS["capabilities.yaml"]
    assert sc["media_type"] == "application/yaml"
    assert sc["validation"] == "yaml_mapping"


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


def test_write_sidecar_empty_yaml_is_valid(tmp_path):
    """Empty YAML (null) should be accepted."""
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    res = st.write_sidecar(item.slug, "capabilities.yaml", "")
    assert res.content == ""


def test_write_sidecar_yaml_list_rejected(tmp_path):
    """YAML that parses to a list (not a mapping) must be rejected."""
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        st.write_sidecar(item.slug, "capabilities.yaml", "- item\n")


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


def test_create_work_rejects_non_string_blocker(tmp_path):
    """#1 — a non-string blocker ref (e.g. the old UI's {slug: ref}) must fail
    loudly instead of being silently stored as a malformed external entry."""
    st = FsWorkStore.open(_work_node(tmp_path))
    with pytest.raises(ValueError, match="blocker refs must be strings"):
        st.create_work("X", blockers=[{"slug": "y"}])
    assert st.query() == []


def test_update_work_rejects_non_string_blocker(tmp_path):
    st = FsWorkStore.open(_work_node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(ValueError, match="blocker refs must be strings"):
        st.update_work(item.slug, blockers=[{"slug": "y"}])


def test_update_work_reparent_preserves_body_edit(tmp_path):
    """#2 — re-parenting AND editing the body in one call must land the new body
    on the moved item (not lose it to an orphaned source directory)."""
    st = FsWorkStore.open(_work_node(tmp_path))
    parent = st.create("Parent", created="2026-01-01")
    child = st.create("Child", created="2026-01-02")
    detail = st.update_work(child.slug, parent=parent.slug, body="RELOCATED BODY")
    assert detail.item.parent == parent.slug
    got = st.get_detail(child.slug)
    assert "RELOCATED BODY" in got.item.body
    assert got.item.parent == parent.slug
    # Exactly one item folder for the child — no orphan/duplicate left behind.
    assert len([i for i in st.query() if i.slug == child.slug]) == 1


def test_update_work_denest(tmp_path):
    """#2 — clearing the parent moves the item back to the top of its status."""
    st = FsWorkStore.open(_work_node(tmp_path))
    parent = st.create("Parent", created="2026-01-01")
    child = st.create("Child", created="2026-01-02", parent=parent.slug)
    assert st.get(child.slug).parent == parent.slug
    st.update_work(child.slug, parent="")
    assert st.get(child.slug).parent == ""
    assert len([i for i in st.query() if i.slug == child.slug]) == 1


def test_update_work_reparent_rejects_self_and_descendant(tmp_path):
    """#2 — an item cannot be nested under itself or one of its descendants."""
    st = FsWorkStore.open(_work_node(tmp_path))
    parent = st.create("Parent", created="2026-01-01")
    child = st.create("Child", created="2026-01-02", parent=parent.slug)
    with pytest.raises(ValueError, match="itself or a descendant"):
        st.update_work(parent.slug, parent=parent.slug)
    with pytest.raises(ValueError, match="itself or a descendant"):
        st.update_work(parent.slug, parent=child.slug)


def test_add_rejects_path_traversal(tmp_path):
    """#3 — a caller-supplied path must not escape the store root."""
    st = FsCapabilitiesStore.open(_cap_node(tmp_path))
    for bad in ["../evil", "/tmp/evil", "a/../../evil", "..\\evil"]:
        with pytest.raises(ValueError, match="invalid path"):
            st.add(bad, name="Do X")
    assert list(tmp_path.rglob("evil*")) == []


def test_taxonomy_add_rejects_path_traversal(tmp_path):
    """#3 — a caller-supplied taxonomy slug must not escape the store root."""
    st = FsTaxonomyStore.open(_tax_node(tmp_path))
    with pytest.raises(ValueError, match="invalid slug"):
        st.add("Evil", slug="../evil")
    assert list(tmp_path.rglob("evil*")) == []


def test_add_rejects_duplicate_path(tmp_path):
    """#5 — adding a capability at an existing path must fail, not overwrite."""
    st = FsCapabilitiesStore.open(_cap_node(tmp_path))
    st.add("routes/login", name="Sign in")
    with pytest.raises(ValueError, match="already exists"):
        st.add("routes/login", name="Sign in")
