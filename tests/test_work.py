import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import (
    RESOLVED_STATUSES, WORK_ARTIFACTS, WORK_STATUSES, IllegalTransition,
    MultipleMatch, StaleRevision, resolution_status, topo_order,
)
from tcw.store.fs import FsWorkStore, init


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


def subnode(parent: Path, rel: str) -> Path:
    """Create and reciprocally register a same-repo child node."""
    d = parent / rel
    d.mkdir(parents=True)
    direct_parent = d.parent
    while not (direct_parent / "tcw-config.yaml").is_file():
        direct_parent = direct_parent.parent
    project_id = d.name.lower()
    init(["work"], d, project_id)
    parent_cfg_path = direct_parent / "tcw-config.yaml"
    parent_cfg = yaml.safe_load(parent_cfg_path.read_text()) or {}
    connected = parent_cfg.setdefault("connected-projects", {})
    connected.setdefault("children", {})[project_id] = str(d.relative_to(direct_parent))
    parent_cfg_path.write_text(yaml.safe_dump(parent_cfg, sort_keys=False))
    child_cfg = yaml.safe_load((d / "tcw-config.yaml").read_text()) or {}
    parent_id = parent_cfg["id"]
    child_cfg["connected-projects"] = {"parent": {parent_id: str(direct_parent)}}
    (d / "tcw-config.yaml").write_text(yaml.safe_dump(child_cfg, sort_keys=False))
    return d


# ── init / slug ──────────────────────────────────────────────────────────────

def test_init_gitkeep_persistence(tmp_path):
    root = node(tmp_path)
    for s in ("inbox", "backlog", "active", "completed", "discarded"):
        assert (root / "docs" / "work" / s / ".gitkeep").is_file()
    assert not (root / "docs" / "work" / "blocked").exists()


def test_formal_work_statuses_exclude_raw_inbox():
    assert WORK_STATUSES == ("backlog", "active", "review", "completed", "discarded")


def test_resolved_statuses_are_the_two_terminal_ones():
    assert RESOLVED_STATUSES == ("completed", "discarded")
    assert all(s in WORK_STATUSES for s in RESOLVED_STATUSES)


def test_raw_inbox_state_yaml_is_not_discovered_as_work(tmp_path):
    root = node(tmp_path)
    raw = root / "docs/work/inbox/request"
    raw.mkdir()
    (raw / "state.yaml").write_text("title: not formal\n")
    assert FsWorkStore.open(root).query() == []


def test_slug_generation_collision_and_immutability(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("Fix the bug", created="2026-01-01")
    assert a.slug == "2026-01-01-fix-the-bug"
    b = st.create("Fix the bug", created="2026-01-01")
    assert b.slug == "2026-01-01-fix-the-bug-2"        # collision suffix
    st.set_field(a.slug, "title", "Renamed")           # title drifts...
    assert st.get(a.slug).title == "Renamed"
    assert st.get(a.slug).slug == a.slug               # ...slug is frozen


def test_body_path_points_at_initial_request_md(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01", body="request\n")
    body = st.body_path(item.slug)
    assert body == st.path(item.slug) / "initial-request.md"
    assert body.exists()
    assert st.body_path("no-such-slug") is None
    # an item created with nothing has no body file to point at
    empty = st.create("Empty", created="2026-01-01")
    assert st.body_path(empty.slug) is None


@pytest.mark.parametrize(
    "request_text, intake_text, expect_file, expect_body",
    [
        ("request\n", None, "initial-request.md", "request\n"),   # request only
        (None, "raw\n", "intake.md", "raw\n"),                    # intake only
        ("request\n", "raw\n", "initial-request.md", "request\n"), # both: request wins
        (None, None, None, ""),                                   # neither
        ("   \n", "raw\n", "intake.md", "raw\n"),                 # empty request is absent
    ],
)
def test_body_surface_resolves_by_one_presence_rule(
    tmp_path, request_text, intake_text, expect_file, expect_body
):
    """Presence is exists-and-non-empty, and every reader uses the same rule:
    the resolved body, the board letters, and `body_path` cannot disagree."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    for name, text in (("initial-request.md", request_text), ("intake.md", intake_text)):
        if text is not None:
            (d / name).write_text(text, encoding="utf-8")

    assert st.get(item.slug).body == expect_body
    body = st.body_path(item.slug)
    assert body == (d / expect_file if expect_file else None)

    present = {a.name: a.present for a in st.artifacts(item.slug)}
    assert present["initial-request"] is (expect_file == "initial-request.md")
    assert present["intake"] is bool(intake_text and intake_text.strip())


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({}, {"state.yaml"}),
        ({"body": "request"}, {"state.yaml", "initial-request.md"}),
        ({"intake": "raw"}, {"state.yaml", "intake.md"}),
        ({"body": "request", "intake": "raw"},
         {"state.yaml", "initial-request.md", "intake.md"}),
    ],
)
def test_create_writes_only_what_it_was_given(tmp_path, kwargs, expected):
    """The folder contents are the assertion, not two path checks: creation used
    to template a request for every item, which is what made `R` meaningless."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create_work("Task", created="2026-01-01", **kwargs).item
    d = st.path(item.slug)
    assert {p.name for p in d.iterdir()} == expected
    if "intake" in kwargs:
        assert (d / "intake.md").read_text() == "raw\n"
    if "body" in kwargs:
        assert (d / "initial-request.md").read_text() == "request\n"


def test_modified_timestamp_tracks_only_bounded_work_resources(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01", body="request\n")
    folder = st.path(item.slug)
    assert folder is not None
    request = folder / "initial-request.md"
    state = folder / "state.yaml"
    os.utime(request, (100, 100))
    os.utime(state, (200, 200))

    assert st.get(item.slug).modified == "1970-01-01T00:03:20Z"

    attachment = folder / "attachments" / "ignored.txt"
    attachment.parent.mkdir()
    attachment.write_text("not part of the bounded work resource set\n")
    os.utime(attachment, (400, 400))
    assert st.get(item.slug).modified == "1970-01-01T00:03:20Z"

    plan = folder / "plan" / "build.md"
    plan.parent.mkdir()
    plan.write_text("# Build\n")
    os.utime(plan, (300, 300))
    assert st.get(item.slug).modified == "1970-01-01T00:05:00Z"


# ── raw inbox intake ─────────────────────────────────────────────────────────

def test_inbox_list_and_show_standalone_text(tmp_path):
    root = node(tmp_path)
    source = root / "docs/work/inbox/request.txt"
    source.write_text("please fix it\n", encoding="utf-8")
    st = FsWorkStore.open(root)
    assert [(e.ref, e.title, e.kind) for e in st.inbox_list()] == [
        ("request.txt", "request", "file")]
    detail = st.inbox_show("request.txt")
    assert detail.body == "please fix it\n"
    assert detail.resources[0].name == "request.txt"
    assert detail.resources[0].readable is True


def test_inbox_accept_folder_generates_request_and_attachments(tmp_path):
    root = node(tmp_path)
    entry = root / "docs/work/inbox/big-request"
    (entry / "nested").mkdir(parents=True)
    (entry / "INDEX.md").write_text("Original request\n", encoding="utf-8")
    (entry / "asset.bin").write_bytes(b"\0\1")
    (entry / "nested/notes.txt").write_text("notes\n", encoding="utf-8")
    (entry / ".ignored").write_text("nope", encoding="utf-8")
    (entry / "link").symlink_to(entry / "asset.bin")
    st = FsWorkStore.open(root)
    item = st.inbox_accept("big-request", title="Accepted title")
    assert item.status == "backlog"
    assert item.title == "Accepted title"
    assert not entry.exists()
    created = st.path(item.slug)
    assert (created / "attachments/asset.bin").read_bytes() == b"\0\1"
    assert (created / "attachments/nested/notes.txt").read_text() == "notes\n"
    assert not (created / "attachments/.ignored").exists()
    body = (created / "initial-request.md").read_text()
    assert "- `initial-request.md` — accepted from `INDEX.md`" in body
    assert "- `attachments/asset.bin`" in body
    assert "- `attachments/nested/notes.txt`" in body
    assert body.endswith("Original request\n")


def test_inbox_accept_binary_file_does_not_render_binary(tmp_path):
    root = node(tmp_path)
    source = root / "docs/work/inbox/sample.dat"
    source.write_bytes(b"\0secret")
    st = FsWorkStore.open(root)
    assert st.inbox_show("sample.dat").body is None
    item = st.inbox_accept("sample.dat")
    created = st.path(item.slug)
    assert (created / "attachments/sample.dat").read_bytes() == b"\0secret"
    assert "secret" not in (created / "initial-request.md").read_text()


@pytest.mark.parametrize("indexes", [("INDEX.md",), ("INDEX.txt",)])
def test_inbox_accept_folder_requires_one_index(tmp_path, indexes):
    root = node(tmp_path)
    entry = root / "docs/work/inbox/request"
    entry.mkdir()
    for name in indexes:
        (entry / name).write_text("body", encoding="utf-8")
    st = FsWorkStore.open(root)
    if len(indexes) == 1:
        assert st.inbox_accept("request").status == "backlog"


def test_inbox_accept_folder_rejects_missing_or_ambiguous_index_without_consuming(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    missing = root / "docs/work/inbox/missing"
    missing.mkdir()
    with pytest.raises(ValueError, match="requires"):
        st.inbox_accept("missing")
    assert missing.exists() and st.query() == []
    ambiguous = root / "docs/work/inbox/ambiguous"
    ambiguous.mkdir()
    (ambiguous / "INDEX.md").write_text("one")
    (ambiguous / "INDEX.txt").write_text("two")
    with pytest.raises(ValueError, match="both"):
        st.inbox_accept("ambiguous")
    assert ambiguous.exists() and st.query() == []


def test_cli_inbox_list_show_accept(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    (root / "docs/work/inbox/request.md").write_text("Do the thing\n")
    monkeypatch.chdir(root)
    assert main(["work", "inbox", "list"]) == 0
    assert "request.md | file | request" in capsys.readouterr().out
    assert main(["work", "inbox", "show", "request.md"]) == 0
    shown = capsys.readouterr().out
    assert "Do the thing" in shown and "request.md" in shown
    assert main(["work", "inbox", "accept", "request.md", "--title", "Chosen"]) == 0
    accepted = capsys.readouterr()
    slug = accepted.out.strip()                              # stdout stays a bare slug
    assert f"→ now at docs/work/backlog/{slug}" in accepted.err   # location on stderr
    assert FsWorkStore.open(root).get(slug).title == "Chosen"


def test_artifacts_report_bounded_presence_and_locator(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    (d / "initial-request.md").write_text("request\n", encoding="utf-8")
    (d / "spec.md").write_text("   \n", encoding="utf-8")
    (d / "plan.md").write_text("plan\n", encoding="utf-8")

    artifacts = {a.name: a.present for a in st.artifacts(item.slug)}
    assert tuple(artifacts) == WORK_ARTIFACTS
    assert artifacts == {
        "initial-request": True,
        "spec": False,
        "plan": True,
        "outcome": False,
        "refined-outcome": False,
        "rework": False,
        "post-mortem": False,
        "intake": False,
    }
    assert st.artifact_locator(item.slug, "plan") == str(d / "plan.md")
    assert st.artifact_locator(item.slug, "../plan") is None
    assert st.artifact_locator("no-such-slug", "plan") is None


def test_locate_reports_repo_relative_home_and_degrades_gracefully(tmp_path, monkeypatch):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    assert st.locate(item.slug) == f"docs/work/backlog/{item.slug}"
    st.start(item.slug)
    assert st.locate(item.slug) == f"docs/work/active/{item.slug}"
    assert st.locate("no-such-slug") is None

    outside = tmp_path / "elsewhere" / item.slug        # item outside node_root:
    monkeypatch.setattr(st, "path", lambda slug: outside)   # absolute, never raises
    assert st.locate(item.slug) == str(outside)


def test_legacy_plan_has_no_declared_stages(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Legacy", created="2026-01-01")
    st.write_artifact(item.slug, "plan", "# Plan\n\nDo the work.\n")
    assert st.plan_stages(item.slug) == []


def test_staged_plan_dag_and_revision_safe_crud(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Staged", created="2026-01-01")
    st.write_artifact(item.slug, "plan", """---
stages:
  - id: model
    title: Build model
    depends_on: []
  - id: api
    title: Add API
    depends_on: [model]
  - id: web
    title: Add web
    depends_on: [model]
---

## Overview

Split implementation by surface.

## Stage ordering

Model first, then API and web in parallel.
""")
    stages = st.plan_stages(item.slug)
    assert [stage.id for stage in stages] == ["model", "api", "web"]
    assert stages[1].depends_on == ("model",)
    assert not stages[0].present
    content = """## Objective

Build it.

## Pre-stage checks

Run tests.

## Implementation

Change code.

## Post-stage checks

Run tests again.
"""
    resource = st.write_plan_stage(item.slug, "model", content, revision="")
    assert st.read_plan_stage(item.slug, "model").content == content
    assert st.plan_stage_locator(item.slug, "model").endswith("plan/model.md")
    with pytest.raises(StaleRevision):
        st.write_plan_stage(item.slug, "model", "changed", revision="stale")
    with pytest.raises(StaleRevision):
        st.delete_plan_stage(item.slug, "model", revision="stale")
    st.delete_plan_stage(item.slug, "model", revision=resource.revision)
    assert st.read_plan_stage(item.slug, "model") is None


def test_plan_stage_path_lost_at_find_is_a_valueerror(tmp_path, monkeypatch):
    """`_plan_stage_path` resolves the item after `_declared_plan_stages` already
    did; losing it in between used to be `None / "plan"` → `TypeError`."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Staged", created="2026-01-01")
    st.write_artifact(item.slug, "plan",
                      "---\nstages: [{id: model, title: Build, depends_on: []}]\n---\n")

    real_find = FsWorkStore._find
    calls = {"n": 0}

    def missing_on_the_second_lookup(self, slug):
        calls["n"] += 1
        return None if calls["n"] == 2 else real_find(self, slug)

    monkeypatch.setattr(FsWorkStore, "_find", missing_on_the_second_lookup)
    with pytest.raises(ValueError, match="no such work item"):
        st.read_plan_stage(item.slug, "model")


@pytest.mark.parametrize("manifest, message", [
    ("[{id: bad/id, title: Bad, depends_on: []}]", "unsafe id"),
    ("[{id: a, title: A, depends_on: [missing]}]", "unknown dependency"),
    ("[{id: a, title: A, depends_on: [b]}, {id: b, title: B, depends_on: [a]}]", "cycle"),
    ("[{id: a, title: A, depends_on: []}, {id: a, title: Again, depends_on: []}]", "duplicate"),
])
def test_staged_plan_rejects_invalid_manifests(tmp_path, manifest, message):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Invalid", created="2026-01-01")
    st.write_artifact(item.slug, "plan", f"---\nstages: {manifest}\n---\n")
    with pytest.raises(ValueError, match=message):
        st.plan_stages(item.slug)


def test_multiple_match_resolution_error(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    for s in ("active", "backlog"):
        d = root / "docs/work" / s / "dup"
        d.mkdir()
        (d / "state.yaml").write_text("slug: dup\n")     # state.yaml is the item marker
    with pytest.raises(MultipleMatch):
        st.get("dup")


def test_cli_path_prints_current_item_folder(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")

    assert main(["work", "path", item.slug]) == 0
    assert capsys.readouterr().out.strip() == str(root / "docs/work/backlog" / item.slug)

    st.start(item.slug)
    assert main(["work", "path", item.slug]) == 0
    assert capsys.readouterr().out.strip() == str(root / "docs/work/active" / item.slug)


def test_cli_path_and_inbox_path_print_resolved_store_roots(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    assert main(["work", "path"]) == 0
    output = capsys.readouterr()
    assert output.out == f"{(root / 'docs/work').resolve()}\n"
    assert output.err == ""

    assert main(["work", "inbox", "path"]) == 0
    output = capsys.readouterr()
    assert output.out == f"{(root / 'docs/work/inbox').resolve()}\n"
    assert output.err == ""


@pytest.mark.parametrize("command", [["work", "path"], ["work", "inbox", "path"]])
def test_cli_root_paths_outside_work_node_print_no_path(tmp_path, monkeypatch, capsys,
                                                        command):
    from tcw.cli import main
    monkeypatch.chdir(tmp_path)

    assert main(command) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "no tcw work node here" in output.err


def test_cli_path_missing_slug_errors(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    assert main(["work", "path", "no-such-slug"]) == 1
    out = capsys.readouterr()
    assert out.out == ""
    assert "tcw work path: no such work item: no-such-slug" in out.err


# ── transitions ──────────────────────────────────────────────────────────────

def test_legal_transition_lifecycle(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert st.get(item.slug).status == "backlog"
    assert st.start(item.slug).status == "active"
    assert st.complete(item.slug, "done", ["acked"]).status == "completed"
    assert st.get(item.slug).resolution == "done"


def test_completed_is_a_sink(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.complete(item.slug, "done", [])
    with pytest.raises(IllegalTransition):
        st.start(item.slug)               # completed → active refused


def test_illegal_transitions_refused(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(IllegalTransition):
        st.complete(item.slug, "done", [])    # backlog → completed (only from active)
    st.start(item.slug)
    st.complete(item.slug, "done", [])
    with pytest.raises(IllegalTransition):
        st.start(item.slug)                   # completed → active (sink)


def test_drop_only_from_backlog(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    with pytest.raises(IllegalTransition):
        st.drop(item.slug)                    # active can't be dropped


def test_blocked_by_read_from_state_yaml(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert st.get(item.slug).blocked_by == []          # absent key → empty
    st.set_field(item.slug, "blocked_by", [{"external": "vendor"}])
    assert st.get(item.slug).blocked_by == [{"external": "vendor"}]


# ── query / resolution after move / boundedness ──────────────────────────────

def test_list_status_filter(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    st.start(b.slug)
    assert {i.slug for i in st.query(status="backlog")} == {"2026-01-01-a"}
    assert {i.slug for i in st.query(status="active")} == {"2026-01-02-b"}


def test_resolution_after_move_and_node_bounded(tmp_path):
    parent = node(tmp_path, "parent")
    pst = FsWorkStore.open(parent)
    item = pst.create("Task", created="2026-01-01")
    pst.start(item.slug)                       # folder moved backlog → active
    assert pst.get(item.slug).status == "active"   # resolves after the move
    # a child node's item is invisible to the parent store (bounded — A.5)
    child = node(parent, "child")
    cst = FsWorkStore.open(child)
    citem = cst.create("Child task", created="2026-01-01")
    assert pst.get(citem.slug) is None


def test_malformed_state_yaml_degrades(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    (root / "docs/work/backlog" / item.slug / "state.yaml").write_text("{not: valid: yaml:")
    got = st.get(item.slug)                    # no crash
    assert got is not None and got.status == "backlog"


# ── blocked-by relation ──────────────────────────────────────────────────────

def test_add_and_remove_blocker_roundtrip(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    st.add_blocker(a.slug, b.slug)
    assert st.get(a.slug).blocked_by == [{"slug": b.slug}]
    st.add_blocker(a.slug, b.slug)                      # idempotent
    assert st.get(a.slug).blocked_by == [{"slug": b.slug}]
    st.remove_blocker(a.slug, b.slug)
    assert st.get(a.slug).blocked_by == []
    with pytest.raises(ValueError) as e:                # absent → fails closed
        st.remove_blocker(a.slug, b.slug)
    assert a.slug in str(e.value) and b.slug in str(e.value)


def test_external_blocker_stored(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    st.add_blocker(a.slug, "waiting on vendor")         # unresolvable → external
    assert st.get(a.slug).blocked_by == [{"external": "waiting on vendor"}]
    st.remove_blocker(a.slug, "waiting on vendor")
    assert st.get(a.slug).blocked_by == []


def test_external_prefix_roundtrips_with_display_form(tmp_path):
    """The `external: <text>` string the board prints is accepted back as a ref."""
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    st.add_blocker(a.slug, "external: JIRA-123")
    assert st.get(a.slug).blocked_by == [{"external": "JIRA-123"}]
    st.add_blocker(a.slug, "JIRA-123")                  # same entry → idempotent
    assert st.get(a.slug).blocked_by == [{"external": "JIRA-123"}]
    assert st.unresolved_blockers(st.get(a.slug)) == ["external: JIRA-123"]
    st.remove_blocker(a.slug, "external: JIRA-123")     # exactly what show printed
    assert st.get(a.slug).blocked_by == []


def test_external_blocker_survives_a_comma(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    text = "waiting on vendor A, then legal signoff"
    st.add_blocker(a.slug, text)
    assert st.get(a.slug).blocked_by == [{"external": text}]   # one entry, not two
    st.remove_blocker(a.slug, f"external: {text}")
    assert st.get(a.slug).blocked_by == []


# ── blocker CLI flags (repeatable; fail-closed removal) ──────────────────────

def test_blocker_flags_are_repeatable(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    assert main(["work", "edit", a.slug,
                 "--blocked-by", "vendor A, then legal",
                 "--blocked-by", "vendor B"]) == 0
    assert st.get(a.slug).blocked_by == [
        {"external": "vendor A, then legal"}, {"external": "vendor B"}]
    assert main(["work", "edit", a.slug,
                 "--unblocked-by", "external: vendor A, then legal",
                 "--unblocked-by", "vendor B"]) == 0
    assert st.get(a.slug).blocked_by == []


def test_unblocked_by_unmatched_ref_fails_closed(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    st.add_blocker(a.slug, "vendor A")
    assert main(["work", "edit", a.slug, "--unblocked-by", "not-a-blocker"]) == 1
    assert "no such blocker" in capsys.readouterr().err
    assert st.get(a.slug).blocked_by == [{"external": "vendor A"}]


def test_bad_unblock_aborts_before_any_blocker_write(tmp_path, monkeypatch):
    """Removals run first, so one bad ref leaves the whole edit unapplied."""
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    assert main(["work", "edit", a.slug,
                 "--blocked-by", "vendor A",
                 "--unblocked-by", "not-a-blocker"]) == 1
    assert st.get(a.slug).blocked_by == []


def test_new_blocked_by_is_repeatable(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "new", "A",
                 "--blocked-by", "vendor A, then legal",
                 "--blocked-by", "vendor B"]) == 0
    slug = capsys.readouterr().out.strip().splitlines()[-1]
    assert FsWorkStore.open(root).get(slug).blocked_by == [
        {"external": "vendor A, then legal"}, {"external": "vendor B"}]


def test_self_block_refused(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    with pytest.raises(ValueError):
        st.add_blocker(a.slug, a.slug)


def test_cycle_refused_direct_and_transitive(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    c = st.create("C", created="2026-01-03")
    st.add_blocker(a.slug, b.slug)                      # A blocked by B
    with pytest.raises(ValueError):
        st.add_blocker(b.slug, a.slug)                  # B blocked by A → direct cycle
    st.add_blocker(b.slug, c.slug)                      # B blocked by C
    with pytest.raises(ValueError):
        st.add_blocker(c.slug, a.slug)                  # C blocked by A → A→B→C→A cycle


# ── gating: unresolved blockers ─────────────────────────────────────────────

def test_start_gated_on_unresolved_blocker(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    with pytest.raises(ValueError):
        st.start(target.slug)                          # blocker not completed
    assert st.start(target.slug, force=True).status == "active"


def test_start_ungated_when_blocker_completed_or_dropped(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(blocker.slug)
    st.complete(blocker.slug, "done", [])
    assert st.start(target.slug).status == "active"    # completed blocker → resolved


def test_start_passes_on_dropped_blocker_silently(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.drop(blocker.slug)                              # vanished → resolved, no warning
    assert st.start(target.slug).status == "active"


def test_complete_gated_on_unresolved_blocker(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(target.slug, force=True)
    with pytest.raises(ValueError):
        st.complete(target.slug, "done", [])           # still blocked
    assert st.complete(target.slug, "done", [], force=True).status == "completed"


# ── CLI: DoD gate ────────────────────────────────────────────────────────────

def test_cli_complete_requires_confirm(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    main(["work", "start", slug])
    assert main(["work", "complete", slug, "--resolution", "done"]) == 1   # no --confirm
    assert FsWorkStore.open(root).get(slug).status == "active"
    assert "Definition of Done" in capsys.readouterr().out
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "completed"
    assert (f"completed {slug} (done) → docs/work/completed/{slug}"
            in capsys.readouterr().out)


# ── capabilities gate at complete (DoD teeth) ────────────────────────────────

def _wc_node(tmp_path: Path) -> Path:
    """A node with both work and capabilities trees."""
    root = node(tmp_path)
    init(["capabilities"], root)
    return root


def _item_with_delta(root: Path, sidecar: str) -> str:
    """Create + start a work item carrying a capabilities.yaml sidecar."""
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    from tcw.cli import main
    main(["work", "start", slug])
    (root / "docs" / "work" / "active" / slug / "capabilities.yaml").write_text(sidecar)
    return slug


def test_complete_gate_blocks_unreconciled_new(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    err = capsys.readouterr().err
    assert "auth/login" in err and "Missing" in err
    assert FsWorkStore.open(root).get(slug).status == "active"


def test_complete_gate_passes_when_reconciled(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    FsCapabilitiesStore.open(root).set("auth/login", {"Status": "Supported"})
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_complete_gate_force_overrides(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    assert main(["work", "complete", slug, "--resolution", "done",
                 "--confirm", "--force"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_complete_gate_omitted_passes(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    FsCapabilitiesStore.open(root).set("auth/login", {"Status": "Omitted"})
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0


def test_complete_gate_changed_missing_passes(tmp_path, monkeypatch, capsys):
    """A changed: entry only fails if it doesn't resolve — a still-Missing one
    that resolves passes (routine body/wording edits leave status alone)."""
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "changed:\n- auth/login\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0


def test_complete_gate_unresolved_refuses(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    slug = _item_with_delta(root, "new:\n- ghost/nope\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    assert "does not resolve" in capsys.readouterr().err


def test_complete_gate_unparseable_sidecar_refuses(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    slug = _item_with_delta(root, "new: [unterminated\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    assert "unreadable" in capsys.readouterr().err


def test_complete_gate_no_sidecar_unaffected(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    main(["work", "start", slug])
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0


def test_complete_gate_work_only_node_unaffected(tmp_path, monkeypatch, capsys):
    """A node with no capabilities tree has nothing to reconcile."""
    from tcw.cli import main
    root = node(tmp_path)                      # work only, no capabilities
    monkeypatch.chdir(root)
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0


def test_complete_gate_reads_after_worktree_mergeback(tmp_path, monkeypatch, capsys):
    """The reconciling flip happens on the worktree branch; the primary tree still
    reads Missing until merge-back. The gate must pass because it runs AFTER
    merge_worktree — a pre-merge gate would false-fail here."""
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _git_subnode(tmp_path, "repo")
    init(["capabilities"], root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed cap"], check=True)
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    (root / "docs" / "work" / "backlog" / slug / "capabilities.yaml").write_text(
        "new:\n- auth/login\n")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "declare"], check=True)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    # Flip on the worktree branch only, and commit there.
    wt = root / ".worktrees" / slug
    FsCapabilitiesStore.open(wt).set("auth/login", {"Status": "Supported"})
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-am", "flip on branch"],
                   check=True)
    # Primary tree still Missing until merge-back.
    assert FsCapabilitiesStore.open(root).get("auth/login").status == "Missing"

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "completed"
    assert FsCapabilitiesStore.open(root).get("auth/login").status == "Supported"


def test_complete_gate_catches_declaration_added_on_branch(tmp_path, monkeypatch, capsys):
    """A `new:` declaration added ON the worktree branch and left Missing must be
    caught — the gate must read the declared list from the merged tree, not the
    pre-merge snapshot."""
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _git_subnode(tmp_path, "repo")
    init(["capabilities"], root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed"], check=True)
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "item"], check=True)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    # Declare the delta ON the branch (not present in the primary snapshot), leave Missing.
    wt = root / ".worktrees" / slug
    (wt / "docs" / "work" / "active" / slug / "capabilities.yaml").write_text(
        "new:\n- auth/login\n")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "declare on branch"],
                   check=True)

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    assert "auth/login" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(slug).status == "active"


# ── topo_order / board ───────────────────────────────────────────────────────

def test_topo_order_blocker_before_blocked(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")           # will be blocked by B
    b = st.create("B", created="2026-01-02")
    st.add_blocker(a.slug, b.slug)
    ordered = [i.slug for i in st.board()]
    assert ordered.index(b.slug) < ordered.index(a.slug)


def test_topo_order_stable_on_ties(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    c = st.create("C", created="2026-01-03")           # no edges → input order kept
    st.add_blocker(b.slug, "external wait")            # external is not a graph node
    ordered = [i.slug for i in st.board()]
    assert ordered == [a.slug, b.slug, c.slug]         # external doesn't reorder


def test_topo_order_ignores_blocker_outside_set(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    backlog_blocker = st.create("Blocker", created="2026-01-01")
    x = st.create("X", created="2026-01-02")
    y = st.create("Y", created="2026-01-03")
    st.add_blocker(x.slug, backlog_blocker.slug)        # blocker stays in backlog
    st.start(x.slug, force=True)
    st.start(y.slug)
    ordered = [i.slug for i in st.board(status="active")]
    assert ordered == [x.slug, y.slug]                  # blocker not in set → no reorder


# ── CLI: edit / new --blocked-by / --force / ordered list ───────────────────

def test_cli_edit_blocked_by_and_blocks(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    assert main(["work", "edit", a.slug, "--blocked-by", b.slug]) == 0
    assert FsWorkStore.open(root).get(a.slug).blocked_by == [{"slug": b.slug}]
    # reverse direction: a now blocks b's sibling c
    c = st.create("C", created="2026-01-03")
    assert main(["work", "edit", a.slug, "--blocks", c.slug]) == 0
    assert FsWorkStore.open(root).get(c.slug).blocked_by == [{"slug": a.slug}]
    assert main(["work", "edit", a.slug, "--unblocked-by", b.slug]) == 0
    assert FsWorkStore.open(root).get(a.slug).blocked_by == []


def test_cli_edit_title_keeps_slug_and_body(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    item = FsWorkStore.open(root).create("Old title", created="2026-01-01",
                                         body="# Old title\n\nprose\n")
    body_path = root / "docs" / "work" / "backlog" / item.slug / "initial-request.md"
    before = body_path.read_bytes()

    assert main(["work", "edit", item.slug, "--title", "New title"]) == 0
    detail = FsWorkStore.open(root).get_detail(item.slug)
    assert detail.item.title == "New title"
    # The slug is the stable ID: a retitle must not recompute it, or every
    # existing reference to this item breaks.
    assert detail.item.slug == item.slug
    # The body's heading is prose the user owns; the store must leave it alone.
    assert body_path.read_bytes() == before

    # An edit that does not pass --title must not disturb the title: _provided
    # maps the absent flag to _UNSET, which update_work skips.
    assert main(["work", "edit", item.slug, "--priority", "5"]) == 0
    assert FsWorkStore.open(root).get(item.slug).title == "New title"


@pytest.mark.parametrize("bad", ["", "   "])
def test_cli_edit_rejects_empty_title(tmp_path, monkeypatch, bad):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    item = FsWorkStore.open(root).create("Keep me", created="2026-01-01")
    # `create_work` refuses an empty title; `edit` must not offer a back door to
    # a titleless item. argparse exits 2 on a type= rejection.
    with pytest.raises(SystemExit) as e:
        main(["work", "edit", item.slug, "--title", bad])
    assert e.value.code == 2
    assert FsWorkStore.open(root).get(item.slug).title == "Keep me"


def test_cli_edit_blocks_nonexistent_errors(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    a = FsWorkStore.open(root).create("A", created="2026-01-01")
    assert main(["work", "edit", a.slug, "--blocks", "nope"]) == 1


def test_cli_new_blocked_by(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    b = FsWorkStore.open(root).create("B", created="2026-01-01")
    assert main(["work", "new", "A",
                 "--blocked-by", b.slug, "--blocked-by", "extra"]) == 0
    items = FsWorkStore.open(root).query(status="backlog")
    a = next(i for i in items if i.title == "A")
    assert a.blocked_by == [{"slug": b.slug}, {"external": "extra"}]


def test_cli_new_blocked_by_attach_failure_returns_nonzero(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    for s in ("active", "backlog"):
        d = root / "docs/work" / s / "dup"
        d.mkdir()
        (d / "state.yaml").write_text("slug: dup\n")        # two real items named "dup"
    rc = main(["work", "new", "A", "--blocked-by", "dup"])   # ambiguous ref → attach fails
    out = capsys.readouterr().out.strip()
    assert rc == 1                                           # non-zero on attach failure
    assert (root / "docs/work/backlog" / out).is_dir()      # item still created + slug printed


def test_cli_new_and_start_emit_next_step_hints(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    assert main(["work", "new", "A"]) == 0
    new_out = capsys.readouterr()
    slug = new_out.out.strip()
    assert "\n" not in slug                                  # stdout is just the slug…
    assert "tcw work start" in new_out.err and slug in new_out.err   # …hint is on stderr
    assert f"→ created at docs/work/backlog/{slug}" in new_out.err   # …and its new home

    assert main(["work", "start", slug]) == 0
    start_out = capsys.readouterr()
    assert start_out.out.strip() == f"started {slug} → docs/work/active/{slug}"
    assert "tcw work complete" in start_out.err and slug in start_out.err


def test_cli_new_epic_omits_start_hint(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "new", "E", "--epic"]) == 0         # epic's next step is delegate
    assert "tcw work start" not in capsys.readouterr().err


def test_cli_edit_ambiguous_slug_errors(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    (root / "docs/work/active/dup").mkdir()
    (root / "docs/work/backlog/dup").mkdir()
    assert main(["work", "edit", "dup", "--blocked-by", "x"]) == 1


def test_cli_complete_blocker_gate_before_dod(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(target.slug, force=True)
    rc = main(["work", "complete", target.slug, "--resolution", "done", "--confirm"])
    assert rc == 1
    out = capsys.readouterr()
    assert "blocked by" in out.err and "Definition of Done" not in out.out  # fail-fast
    assert main(["work", "complete", target.slug, "--resolution", "done",
                 "--confirm", "--force"]) == 0


def test_malformed_blocked_by_entry_degrades(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    st.set_field(item.slug, "blocked_by", [{"note": "garbage"}])
    assert st.unresolved_blockers(st.get(item.slug)) == []   # skipped, no KeyError
    monkeypatch.chdir(root)
    assert main(["work", "show", item.slug]) == 0            # show doesn't crash
    assert main(["work", "list"]) == 0                       # list doesn't crash


# ── priority ─────────────────────────────────────────────────────────────────

def test_priority_order_specified_above_unspecified_desc(tmp_path):
    from tcw.store.base import priority_order
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")               # no priority
    b = st.create("B", created="2026-01-02", priority=1)
    c = st.create("C", created="2026-01-03")               # no priority
    d = st.create("D", created="2026-01-04", priority=5)
    ordered = [i.slug for i in priority_order(st.query(status="backlog"))]
    # specified desc (D=5, B=1) first; unspecified keep creation order (A, C)
    assert ordered == [d.slug, b.slug, a.slug, c.slug]


def test_priority_default_unspecified_keeps_creation_order(tmp_path):
    from tcw.store.base import priority_order
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    assert a.priority is None
    assert [i.slug for i in priority_order([a, b])] == [a.slug, b.slug]


def test_board_priority_cannot_jump_a_blocker(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")   # low/no priority
    blocked = st.create("Blocked", created="2026-01-02", priority=9)
    st.add_blocker(blocked.slug, blocker.slug)
    ordered = [i.slug for i in st.board(status="backlog")]
    # priority wants Blocked first, but its blocker is a hard constraint
    assert ordered.index(blocker.slug) < ordered.index(blocked.slug)


def test_priority_persists_create_and_set_field(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01", priority=3)
    assert FsWorkStore.open(root).get(a.slug).priority == 3
    st.set_field(a.slug, "priority", 7)
    assert FsWorkStore.open(root).get(a.slug).priority == 7


def test_cli_new_and_edit_priority_reorders_list(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    assert main(["work", "new", "B", "--priority", "5"]) == 0
    b = next(i for i in FsWorkStore.open(root).query(status="backlog") if i.title == "B")
    assert FsWorkStore.open(root).get(b.slug).priority == 5
    # B (priority 5) sorts above A (unspecified)
    assert [i.slug for i in FsWorkStore.open(root).board(status="backlog")][0] == b.slug
    # raise A above B via edit
    assert main(["work", "edit", a.slug, "--priority", "9"]) == 0
    assert FsWorkStore.open(root).get(a.slug).priority == 9
    assert [i.slug for i in FsWorkStore.open(root).board(status="backlog")][0] == a.slug


# ── list: completed hidden by default ────────────────────────────────────────

def _make_completed(st):
    item = st.create("Done thing", created="2026-01-01")
    st.start(item.slug)
    st.complete(item.slug, "done", [])
    return item


def test_cli_list_hides_completed_by_default(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    live = st.create("Live one", created="2026-01-02")
    done = _make_completed(st)
    assert main(["work", "list"]) == 0
    out = capsys.readouterr().out
    assert live.slug in out
    assert done.slug not in out                 # completed hidden by default


def test_cli_list_status_completed_still_shows(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    done = _make_completed(st)
    assert main(["work", "list", "--status", "completed"]) == 0
    assert done.slug in capsys.readouterr().out  # explicit filter honored


def test_cli_list_all_includes_completed(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    live = st.create("Live one", created="2026-01-02")
    done = _make_completed(st)
    assert main(["work", "list", "--all"]) == 0
    out = capsys.readouterr().out
    assert live.slug in out and done.slug in out  # --all = full board


# ── list: priority column ────────────────────────────────────────────────────

def test_cli_list_shows_priority_column(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    hot = st.create("Hot", created="2026-01-01", priority=7)
    cold = st.create("Cold", created="2026-01-02")        # unspecified
    assert main(["work", "list"]) == 0
    rows = {ln.split(" | ")[0]: ln.split(" | ")
            for ln in capsys.readouterr().out.splitlines()}
    # row: slug | status | lifecycle-stages | priority | title
    assert rows[hot.slug][3] == "7"
    assert rows[cold.slug][3] == "-"
    assert rows[hot.slug][4] == "Hot"                     # title still follows


def test_cli_list_shows_lifecycle_stage_letters(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    item = st.create("Planned", created="2026-01-01")
    d = st.path(item.slug)
    (d / "initial-request.md").write_text("request\n", encoding="utf-8")
    (d / "spec.md").write_text("spec\n", encoding="utf-8")
    (d / "plan.md").write_text("plan\n", encoding="utf-8")

    assert main(["work", "list"]) == 0
    row = capsys.readouterr().out.strip().split(" | ")
    assert row[2] == "RSP"


def test_cli_list_ignores_empty_lifecycle_artifacts(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    item = st.create("Sketch", created="2026-01-01")
    d = st.path(item.slug)
    (d / "initial-request.md").write_text("   \n", encoding="utf-8")
    (d / "spec.md").write_text("spec\n", encoding="utf-8")

    assert main(["work", "list"]) == 0
    row = capsys.readouterr().out.strip().split(" | ")
    assert row[2] == "S"


def test_cli_list_shows_outcome_and_refined_outcome_stages(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    item = st.create("Finished", created="2026-01-01", body="request\n")
    d = st.path(item.slug)
    (d / "outcome.md").write_text("outcome\n", encoding="utf-8")
    (d / "refined-outcome.md").write_text("refined\n", encoding="utf-8")

    assert main(["work", "list"]) == 0
    row = capsys.readouterr().out.strip().split(" | ")
    assert row[2] == "ROF"


def test_cli_work_init_mirrors_top_level(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = tmp_path / "fresh"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.chdir(root)
    assert main(["work", "init", "--id", "fresh"]) == 0
    comp_out = capsys.readouterr().out
    for s in ("inbox", "backlog", "active", "completed"):
        assert (root / "docs" / "work" / s / ".gitkeep").is_file()
    assert main(["init", "work"]) == 0
    assert comp_out == capsys.readouterr().out


# ── nested work items (parent/child) ─────────────────────────────────────────

def test_create_child_nests_and_derives_parent(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    # folder nests inside the parent's folder
    assert (root / "docs/work/backlog" / p.slug / c.slug / "state.yaml").is_file()
    got = st.get(c.slug)
    assert got.parent == p.slug
    assert got.status == "backlog"                  # inherits parent's status folder
    assert st.get(p.slug).parent == ""              # top-level


def test_create_child_unknown_parent_errors(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    with pytest.raises(ValueError):
        st.create("Orphan", created="2026-01-01", parent="no-such-slug")


def test_discovery_is_depth_agnostic(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    assert st.path(c.slug) == root / "docs/work/backlog" / p.slug / c.slug
    assert {i.slug for i in st.query()} == {p.slug, c.slug}      # query walks
    assert {i.slug for i in st.query(status="backlog")} == {p.slug, c.slug}


def test_parent_transition_carries_children(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    st.start(p.slug)                                # git mv of the parent folder
    assert st.get(p.slug).status == "active"
    child = st.get(c.slug)
    assert child.status == "active"                 # rode along, still nested
    assert child.parent == p.slug
    assert (root / "docs/work/active" / p.slug / c.slug / "state.yaml").is_file()


def test_child_transition_denests_to_top_level(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    st.start(c.slug)                                # child moves to a new status alone
    child = st.get(c.slug)
    assert child.status == "active"
    assert child.parent == ""                       # de-nested (relation ends with nesting)
    assert (root / "docs/work/active" / c.slug / "state.yaml").is_file()
    assert st.get(p.slug).status == "backlog"       # parent unaffected


def test_drop_parent_removes_children(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    st.drop(p.slug)
    assert st.get(p.slug) is None
    assert st.get(c.slug) is None                   # nested child went with it


def test_cli_new_parent_and_list_nesting(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    assert main(["work", "new", "Child task", "--parent", p.slug]) == 0
    child_slug = capsys.readouterr().out.strip()
    assert FsWorkStore.open(root).get(child_slug).parent == p.slug
    assert main(["work", "list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    parent_line = next(ln for ln in lines if ln.startswith(p.slug))
    child_line = next(ln for ln in lines if child_slug in ln)
    assert child_line.startswith("  ")              # child indented under parent
    assert lines.index(parent_line) < lines.index(child_line)


def test_cli_new_unknown_parent_errors(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "new", "X", "--parent", "nope"]) == 1


# ── effort / complexity ──────────────────────────────────────────────────────

def test_effort_complexity_persist_and_read_back(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    assert main(["work", "new", "A", "--effort", "high", "--complexity", "low"]) == 0
    a = st.query(status="backlog")[0]
    assert (a.effort, a.complexity) == ("high", "low")
    # persisted as real state.yaml keys
    import yaml
    state = yaml.safe_load((st.path(a.slug) / "state.yaml").read_text())
    assert state["effort"] == "high" and state["complexity"] == "low"


def test_edit_effort_leaves_complexity_untouched(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    st.set_field(a.slug, "complexity", "high")
    assert main(["work", "edit", a.slug, "--effort", "medium"]) == 0
    got = FsWorkStore.open(root).get(a.slug)
    assert (got.effort, got.complexity) == ("medium", "high")   # complexity preserved


def test_show_displays_when_set_omits_when_unset(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    assert main(["work", "show", a.slug]) == 0
    assert "effort:" not in capsys.readouterr().out          # omitted when unset
    st.set_field(a.slug, "effort", "very-high")
    assert main(["work", "show", a.slug]) == 0
    assert "effort: very-high" in capsys.readouterr().out


def test_invalid_effort_rejected_and_no_write(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    with pytest.raises(SystemExit):                           # argparse choices=
        main(["work", "new", "A", "--effort", "bogus"])
    assert FsWorkStore.open(root).query(status="backlog") == []   # nothing created


def test_missing_and_null_keys_read_as_empty(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")                 # no effort/complexity keys
    assert (st.get(a.slug).effort, st.get(a.slug).complexity) == ("", "")
    st.set_field(a.slug, "effort", None)                     # bare YAML `effort:` (null)
    assert FsWorkStore.open(root).get(a.slug).effort == ""   # `or ""` coercion


# ── list --include-descendants ───────────────────────────────────────────────

def test_list_include_descendants_groups_by_node(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    FsWorkStore.open(subnode(root, "project-a")).create("A feature", created="2026-01-01")
    FsWorkStore.open(subnode(root, "project-b")).create("B feature", created="2026-01-01")
    (root / "plain-subdir").mkdir()                          # no sentinel → not a node

    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    out = capsys.readouterr().out

    # root-first, then path-sorted; a non-node subdir is never a group
    assert out.index("# .\n") < out.index("# project-a") < out.index("# project-b")
    assert "plain-subdir" not in out
    # each node's item shows under its own header (node-bounded boards)
    assert out.index("2026-01-01-a-feature") < out.index("# project-b")
    assert "2026-01-01-b-feature" in out.split("# project-b", 1)[1]
    assert "2026-01-01-root-thing" in out.split("# project-a", 1)[0]


def test_list_include_descendants_indents_same_node_initiative_child(
        tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create_work("Epic", created="2026-01-01", type="epic").item
    child = st.create_work("Child", created="2026-01-02",
                           initiative=epic.slug).item

    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    out = capsys.readouterr().out
    assert f"\n{epic.slug} |" in out
    assert f"\n  {child.slug} |" in out
    assert out.count(child.slug) == 1


def test_list_include_descendants_indents_qualified_cross_node_initiative_child(
        tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    child_root = subnode(root, "project-a")
    epic = FsWorkStore.open(root).create_work(
        "Epic", created="2026-01-01", type="epic").item
    child = FsWorkStore.open(child_root).create_work(
        "Child", created="2026-01-02", initiative=epic.slug).item

    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    out = capsys.readouterr().out
    assert f"\n{epic.slug} |" in out
    assert f"\n  project-a/{child.slug} |" in out
    assert out.count(child.slug) == 1


@pytest.mark.parametrize("flag", ["-i", "--incl-desc", "--include-descendants"])
def test_list_include_descendants_flag_aliases(flag, tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(subnode(root, "project-a")).create(
        "A feature", created="2026-01-01")

    monkeypatch.chdir(root)
    assert main(["work", "list", flag]) == 0
    assert "# project-a" in capsys.readouterr().out


def test_list_include_descendants_skips_own_worktree(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    decoy = root / ".worktrees/some-item"
    decoy.mkdir(parents=True)
    init(["work"], decoy, "copied-worktree")                # valid but unregistered decoy

    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    assert ".worktrees" not in capsys.readouterr().out


def test_list_include_descendants_nested(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    mid = subnode(root, "project-a")
    FsWorkStore.open(subnode(mid, "nested")).create("deep", created="2026-01-01")

    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    out = capsys.readouterr().out
    assert "# nested" in out
    assert "2026-01-01-deep" in out


def test_list_without_flag_has_no_node_headers(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    subnode(root, "project-a")

    monkeypatch.chdir(root)
    assert main(["work", "list"]) == 0
    out = capsys.readouterr().out
    assert "# ." not in out and "project-a" not in out      # descendants untouched without the flag


# ── effort/complexity level normalization ────────────────────────────────────

def test_normalize_work_level_aliases_case_and_passthrough():
    from tcw.store.base import normalize_work_level
    assert normalize_work_level("h") == "high"
    assert normalize_work_level("VH") == "very-high"
    assert normalize_work_level("L") == "low"
    assert normalize_work_level("m") == "medium"
    assert normalize_work_level("HIGH") == "high"          # canonical, case-insensitive
    assert normalize_work_level("very-high") == "very-high"


def test_normalize_work_level_rejects_unknown():
    from tcw.store.base import normalize_work_level
    with pytest.raises(ValueError, match="L/M/H/VH"):
        normalize_work_level("s")                          # T-shirt slip, not a level
    for junk in ("", "   ", "xl"):                          # empty/whitespace/unknown all rejected
        with pytest.raises(ValueError, match="invalid level"):
            normalize_work_level(junk)


def test_cli_new_effort_alias_stored_canonical(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    assert main(["work", "new", "Task", "--effort", "h", "--complexity", "vh"]) == 0
    slug = capsys.readouterr().out.strip()
    item = FsWorkStore.open(root).get(slug)
    assert item.effort == "high" and item.complexity == "very-high"


def test_cli_new_effort_invalid_exits(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit):                         # argparse rejects the bad value
        main(["work", "new", "Task", "--effort", "xl"])
    assert "L/M/H/VH" in capsys.readouterr().err


def test_cli_edit_effort_alias_stored_canonical(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    item = FsWorkStore.open(root).create("Task", created="2026-01-01")

    assert main(["work", "edit", item.slug, "--effort", "M", "--complexity", "l"]) == 0
    edited = FsWorkStore.open(root).get(item.slug)
    assert edited.effort == "medium" and edited.complexity == "low"


# ── qualified (subproject-relative) slugs ────────────────────────────────────

def _git_subnode(parent: Path, rel: str) -> Path:
    """A descendant that is its OWN committed git repo — worktree flows need a
    repo with a HEAD (a plain subnode shares the enclosing repo)."""
    d = parent / rel
    d.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
    project_id = d.name.lower()
    init(["work"], d, project_id)
    parent_cfg_path = parent / "tcw-config.yaml"
    if parent_cfg_path.is_file():
        parent_cfg = yaml.safe_load(parent_cfg_path.read_text()) or {}
        parent_cfg.setdefault("connected-projects", {}).setdefault("children", {})[
            project_id
        ] = rel
        parent_cfg_path.write_text(yaml.safe_dump(parent_cfg, sort_keys=False))
        child_cfg = yaml.safe_load((d / "tcw-config.yaml").read_text()) or {}
        child_cfg["connected-projects"] = {
            "parent": {parent_cfg["id"]: str(parent.resolve())}
        }
        (d / "tcw-config.yaml").write_text(yaml.safe_dump(child_cfg, sort_keys=False))
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "commit", "-q", "-m", "init"], check=True)
    return d


def test_list_include_descendants_qualifies_slugs(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    FsWorkStore.open(subnode(root, "project-a")).create("a feature", created="2026-01-01")
    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    out = capsys.readouterr().out
    assert "project-a/2026-01-01-a-feature |" in out          # descendant slug qualified
    anchor_line = next(l for l in out.splitlines() if "root-thing" in l)
    assert anchor_line.lstrip().startswith("2026-01-01-root-thing |")  # anchor stays bare


def test_show_and_path_resolve_qualified_slug(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "project-a")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "show", f"project-a/{slug}"]) == 0
    assert slug in capsys.readouterr().out
    assert main(["work", "path", f"project-a/{slug}"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == str(sub / "docs" / "work" / "backlog" / slug)


def test_qualified_resolution_from_mid_tree_node(tmp_path, monkeypatch, capsys):
    """Anchor is wherever you invoke — a mid-tree node resolves a slug relative to
    itself, not the repo root."""
    from tcw.cli import main
    root = node(tmp_path)
    mid = subnode(root, "project-a")
    grand = subnode(mid, "nested")
    slug = FsWorkStore.open(grand).create("deep", created="2026-01-01").slug
    monkeypatch.chdir(mid)
    assert main(["work", "show", f"nested/{slug}"]) == 0
    assert slug in capsys.readouterr().out


def test_start_complete_via_qualified_slug(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "project-a")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "start", f"project-a/{slug}"]) == 0
    out = capsys.readouterr()
    assert f"started project-a/{slug}" in out.out
    assert f"complete project-a/{slug}" in out.err            # hint echoes QUALIFIED slug
    assert FsWorkStore.open(sub).get(slug).status == "active"
    assert main(["work", "complete", f"project-a/{slug}",
                 "--resolution", "done", "--confirm"]) == 0
    assert FsWorkStore.open(sub).get(slug).status == "completed"


def test_worktree_roundtrip_via_qualified_slug(tmp_path, monkeypatch, capsys):
    """start --worktree then complete on a descendant addressed by qualified slug:
    the worktree lands under the DESCENDANT's .worktrees/<bare> and is removed on
    complete (guards remove_worktree using bare, not the qualified slug)."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = _git_subnode(root, "project-a")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "start", f"project-a/{slug}", "--worktree"]) == 0
    capsys.readouterr()
    assert (sub / ".worktrees" / slug / "docs" / "work" / "active" / slug).is_dir()
    assert main(["work", "complete", f"project-a/{slug}",
                 "--resolution", "done", "--confirm"]) == 0
    assert not (sub / ".worktrees" / slug).exists()          # torn down via bare path
    assert FsWorkStore.open(sub).get(slug).status == "completed"


def test_drop_via_qualified_slug(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "project-a")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "drop", f"project-a/{slug}", "--confirm"]) == 0
    assert FsWorkStore.open(sub).get(slug) is None


def test_drop_refuses_without_confirm(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    slug = FsWorkStore.open(root).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "drop", slug]) == 1
    out = capsys.readouterr()
    # Both lines on stderr: nothing succeeded, and two streams can interleave.
    assert "--confirm" in out.err and slug in out.err       # names what would go
    assert "Would delete" in out.err and out.out == ""
    assert FsWorkStore.open(root).get(slug) is not None     # and deleted nothing
    assert main(["work", "drop", slug, "--confirm"]) == 0
    assert FsWorkStore.open(root).get(slug) is None


def test_drop_of_a_missing_item_does_not_advise_confirm(tmp_path, monkeypatch, capsys):
    """The gate must resolve existence first.

    Advising `--confirm` on an item that does not exist sends the user to a
    second, different error when they take the advice.
    """
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "drop", "2026-01-01-no-such-thing"]) == 1
    err = capsys.readouterr().err
    assert "no such work item" in err
    assert "--confirm" not in err


def test_edit_blocks_reverse_stores_bare_ref(tmp_path, monkeypatch, capsys):
    """--blocks on a qualified slug must persist a BARE ref into the other item's
    node-local blocked_by (never the qualified form)."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "project-a")
    s = FsWorkStore.open(sub)
    a = s.create("item a", created="2026-01-01").slug
    b = s.create("item b", created="2026-01-02").slug
    monkeypatch.chdir(root)
    assert main(["work", "edit", f"project-a/{a}", "--blocks", b]) == 0
    blockers = [x.get("slug") for x in FsWorkStore.open(sub).get(b).blocked_by]
    assert a in blockers and f"project-a/{a}" not in blockers


def test_bare_slug_not_found_across_nodes(tmp_path, monkeypatch, capsys):
    """Backward compat: a descendant-only slug is NOT resolvable bare from the anchor."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "project-a")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "show", slug]) == 1                  # bare -> anchor only
    assert f"no such work item: {slug}" in capsys.readouterr().err
    assert main(["work", "show", f"project-a/{slug}"]) == 0   # qualified resolves


def test_unresolvable_qualifier_names_the_unregistered_project(tmp_path, monkeypatch, capsys):
    """The cause, not the symptom — 'no such work item' read like a typo."""
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "show", "Nope/2026-01-01-foo"]) == 1
    assert "tcw work show: no such project in this graph: Nope" in capsys.readouterr().err


def test_parent_qualified_slug_addressable_from_child(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    child = subnode(root, "sub")
    epic = FsWorkStore.open(root).create("Parent epic", created="2026-01-01")
    monkeypatch.chdir(child)
    assert main(["work", "show", f"repo/{epic.slug}"]) == 0
    assert "Parent epic" in capsys.readouterr().out


def test_qualified_ambiguous_bare_surfaces_multiple_match(tmp_path, monkeypatch, capsys):
    """A qualified ref whose bare part collides inside the descendant still errors."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "project-a")
    for status in ("active", "backlog"):                      # two items named 'dup'
        d = sub / "docs/work" / status / "dup"
        d.mkdir(parents=True)
        (d / "state.yaml").write_text("slug: dup\n")
    monkeypatch.chdir(root)
    assert main(["work", "show", "project-a/dup"]) == 1
    assert "resolves to 2 items" in capsys.readouterr().err


# ── discarded status ─────────────────────────────────────────────────────────

def _persisted_dod(root: Path, status: str, slug: str) -> list:
    """`dod` lives in state.yaml, not on WorkItem."""
    state = yaml.safe_load((root / "docs/work" / status / slug / "state.yaml").read_text())
    return state.get("dod", [])

@pytest.mark.parametrize("resolution,expected", [
    ("done", "completed"),
    ("wontfix", "discarded"),
    ("duplicate", "discarded"),
    ("superseded", "discarded"),
])
def test_resolution_selects_the_terminal_folder(tmp_path, resolution, expected):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create(f"Close as {resolution}", created="2026-01-01")
    st.start(item.slug)
    assert st.complete(item.slug, resolution, []).status == expected
    assert (root / "docs/work" / expected / item.slug / "state.yaml").is_file()


@pytest.mark.parametrize("bad", ["", "nope", None, "Done"])
def test_resolution_status_raises_rather_than_guessing(bad):
    """A silent `else: discarded` would make a corrupt item read as consistent."""
    with pytest.raises(ValueError):
        resolution_status(bad)


@pytest.mark.parametrize("resolution", ["wontfix", "duplicate", "superseded"])
def test_discard_direct_from_backlog(tmp_path, resolution):
    """The friction this status exists to remove: no throwaway start."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Never going to happen", created="2026-01-01")
    assert st.complete(item.slug, resolution, []).status == "discarded"


def test_backlog_to_completed_still_refused_for_a_plain_item(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Not started", created="2026-01-01")
    with pytest.raises(IllegalTransition):
        st.complete(item.slug, "done", [])


def test_completable_epic_still_closes_from_backlog(tmp_path):
    """The done-only exception survives; (backlog, discarded) doesn't subsume it."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create_work("Epic", created="2026-01-01", type="epic").item
    child = st.create_work("Child", created="2026-01-01",
                           initiative=epic.slug).item
    st.start(epic.slug)
    st.start(child.slug)
    st.complete(child.slug, "done", [])
    st = FsWorkStore.open(root)
    assert st.get(epic.slug).status == "active"
    assert st.complete(epic.slug, "done", []).status == "completed"


def test_discarded_blocker_no_longer_blocks(tmp_path):
    """A decision not to do it is as final as doing it."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-01")
    st.add_blocker(target.slug, blocker.slug)
    assert st.unresolved_blockers(st.get(target.slug)) == [blocker.slug]
    st.complete(blocker.slug, "wontfix", [])
    st = FsWorkStore.open(root)
    assert st.unresolved_blockers(st.get(target.slug)) == []
    assert st.start(target.slug).status == "active"


def test_epic_completable_with_a_discarded_child(tmp_path):
    """A child nobody will do must not hold its epic open forever."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create_work("Epic", created="2026-01-01", type="epic").item
    shipped = st.create_work("Shipped", created="2026-01-01",
                             initiative=epic.slug).item
    dropped = st.create_work("Abandoned", created="2026-01-01",
                             initiative=epic.slug).item
    st.start(epic.slug)
    st.start(shipped.slug)
    st.complete(shipped.slug, "done", [])
    st = FsWorkStore.open(root)
    assert not st.epic_completable(st.get(epic.slug))      # one child still open
    st.complete(dropped.slug, "wontfix", [])
    st = FsWorkStore.open(root)
    assert st.epic_completable(st.get(epic.slug))
    assert st.complete(epic.slug, "done", []).status == "completed"


def test_list_hides_discarded_by_default(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    kept = st.create("Still open", created="2026-01-01")
    gone = st.create("Abandoned", created="2026-01-01")
    st.complete(gone.slug, "wontfix", [])
    monkeypatch.chdir(root)

    assert main(["work", "list"]) == 0
    out = capsys.readouterr().out
    assert kept.slug in out and gone.slug not in out

    assert main(["work", "list", "--all"]) == 0
    assert gone.slug in capsys.readouterr().out

    assert main(["work", "list", "--status", "discarded"]) == 0
    out = capsys.readouterr().out
    assert gone.slug in out and kept.slug not in out


def test_discard_skips_the_dod_checklist_but_still_needs_confirm(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Abandon me", created="2026-01-01")
    monkeypatch.chdir(root)

    assert main(["work", "complete", item.slug, "--resolution", "wontfix"]) == 1
    captured = capsys.readouterr()
    assert "Definition of Done" not in captured.out
    assert "is permanent" in captured.err

    assert main(["work", "complete", item.slug, "--resolution", "wontfix", "--confirm"]) == 0
    captured = capsys.readouterr()
    assert "Definition of Done" not in captured.out
    assert "discarded" in captured.out
    assert _persisted_dod(root, "discarded", item.slug) == []


def test_done_still_prints_the_dod_checklist_but_no_longer_stores_it(
        tmp_path, monkeypatch, capsys):
    """The checklist is `[prompted]` — printing it is the whole job.

    It is no longer persisted: `_complete` passed the entire checklist as the
    acknowledgement unconditionally, so every completed item stored the same
    fixed 5-string constant and the field could never differ. Same treatment as
    `phase`: the key stops being written, existing items keep theirs unread, and
    no rewrite pass is added."""
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Ship me", created="2026-01-01")
    st.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug, "--resolution", "done", "--confirm"]) == 0
    assert "Definition of Done" in capsys.readouterr().out
    assert _persisted_dod(root, "completed", item.slug) == []


def test_an_item_completed_before_the_change_keeps_its_stored_dod(tmp_path):
    """The migration is a no-op in the same sense `phase` was: unread, not
    erased. Nothing rewrites 60 completed items to drop a key nothing consults."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Legacy", created="2026-01-01")
    st.start(item.slug)
    st.complete(item.slug, "done", [])
    state_path = root / "docs/work/completed" / item.slug / "state.yaml"
    state = yaml.safe_load(state_path.read_text())
    state["dod"] = ["tests pass", "docs synced"]           # as an older tcw wrote it
    state_path.write_text(yaml.safe_dump(state, sort_keys=False))

    reloaded = FsWorkStore.open(root).get(item.slug)
    assert reloaded is not None and reloaded.status == "completed"
    assert not hasattr(reloaded, "dod")
    assert _persisted_dod(root, "completed", item.slug) == ["tests pass", "docs synced"]


def test_check_flags_status_resolution_disagreement(tmp_path):
    """`complete()` can't produce this — a hand-run `mv` or a bad merge can."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Moved by hand", created="2026-01-01")
    st.start(item.slug)
    st.complete(item.slug, "wontfix", [])
    src = root / "docs/work/discarded" / item.slug
    src.rename(root / "docs/work/completed" / item.slug)
    problems = FsWorkStore.open(root).check()
    assert any("belongs in 'discarded'" in p for p in problems)


def test_check_flags_terminal_status_without_a_resolution(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Orphaned", created="2026-01-01")
    (root / "docs/work/backlog" / item.slug).rename(
        root / "docs/work/discarded" / item.slug)
    problems = FsWorkStore.open(root).check()
    assert any("missing or invalid resolution" in p for p in problems)


def test_check_flags_open_item_carrying_a_resolution(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Half transitioned", created="2026-01-01")
    st.set_field(item.slug, "resolution", "done")
    problems = FsWorkStore.open(root).check()
    assert any("only a closed item has one" in p for p in problems)


def test_check_is_clean_for_a_healthy_node(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    open_item = st.create("Open", created="2026-01-01")
    shipped = st.create("Shipped", created="2026-01-01")
    st.start(shipped.slug)
    st.complete(shipped.slug, "done", [])
    dropped = st.create("Dropped", created="2026-01-01")
    st.complete(dropped.slug, "superseded", [])
    assert FsWorkStore.open(root).check() == []
    assert open_item.slug                                  # created, still untouched


def test_discard_leaves_the_unmerged_branch_intact(tmp_path, monkeypatch, capsys):
    """Deciding work isn't wanted is not authority to destroy an unmerged branch."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = _git_subnode(root, "project-a")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "start", f"project-a/{slug}", "--worktree"]) == 0
    capsys.readouterr()
    wt = sub / ".worktrees" / slug
    assert wt.is_dir()
    (wt / "only-on-the-branch.txt").write_text("unmerged work\n")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "wip"], check=True)

    assert main(["work", "complete", f"project-a/{slug}",
                 "--resolution", "wontfix", "--confirm"]) == 0
    err = capsys.readouterr().err
    assert not wt.exists()                                   # worktree torn down
    assert f"work/{slug}" in err and "left intact" in err
    branches = subprocess.run(["git", "-C", str(sub), "branch", "--list", f"work/{slug}"],
                              capture_output=True, text=True).stdout
    assert f"work/{slug}" in branches                         # branch survives
    assert not (sub / "only-on-the-branch.txt").exists()      # and was NOT merged
    assert FsWorkStore.open(sub).get(slug).status == "discarded"


def test_blockers_gate_a_completion_but_not_a_discard(tmp_path):
    """"Blocked indefinitely" is a reason to give up, not a reason you can't.
    The gate says "don't claim you shipped this while its dependency is
    unfinished" — which says nothing about abandoning it."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    blocker = st.create("Vendor work", created="2026-01-01")
    target = st.create("Depends on the vendor", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(target.slug, force=True)

    with pytest.raises(ValueError, match="blocked by"):
        st.complete(target.slug, "done", [])
    assert st.complete(target.slug, "wontfix", []).status == "discarded"


def test_epic_children_gate_applies_to_a_discard_too(tmp_path):
    """Unlike blockers: an initiative child can't start until its epic is
    active, so closing an epic either way strands open children."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create_work("Epic", created="2026-01-01", type="epic").item
    st.create_work("Child", created="2026-01-02", initiative=epic.slug)
    st.start(epic.slug)
    with pytest.raises(ValueError, match="initiative children are still open"):
        st.complete(epic.slug, "wontfix", [])


def test_a_state_yaml_still_carrying_phase_stays_readable(tmp_path):
    """`phase` was a dead field: declared since the first work commit, displayed
    by `show` and the rollup, and never written non-empty by any code path.

    Removing it must be a no-op for every item created before the removal. It is
    not *erased* from those items — `set_field` is a read-modify-write over the
    raw mapping, so unknown keys survive — it simply stops being read. That is
    the whole migration: no rewrite pass, no churn, and an inert key nothing
    consults."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Predates the removal", created="2026-01-01")

    state_path = root / "docs" / "work" / "backlog" / item.slug / "state.yaml"
    state = yaml.safe_load(state_path.read_text())
    assert "phase" not in state                       # new items never write it
    state["phase"] = "some-stale-value"               # simulate a pre-existing item
    state_path.write_text(yaml.safe_dump(state, sort_keys=False))

    reloaded = st.get(item.slug)                      # read ignores the stale key
    assert reloaded is not None
    assert reloaded.title == "Predates the removal"
    assert not hasattr(reloaded, "phase")

    st.set_field(item.slug, "priority", 3)            # writes still work over it
    assert st.get(item.slug).priority == 3
    assert yaml.safe_load(state_path.read_text())["phase"] == "some-stale-value"

    # And it reaches no output surface: `show` renders the item without it.
    from tcw.work.cli import _print_item
    _print_item(st.get(item.slug))
