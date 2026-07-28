"""The `review` status and the `submit` / `rework` transitions.

`review` means "implemented, acceptance pending". It is the first status that is
neither open-for-work nor terminal, and `rework` is the model's only reverse
edge — so the matrix is worth exercising explicitly rather than trusting that a
constant was edited correctly.
"""
import subprocess
from pathlib import Path

import pytest

from tcw.store.base import (
    LEGAL_TRANSITIONS, RESOLVED_STATUSES, WORK_STATUSES, IllegalTransition,
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


# ── the shape of the state machine ───────────────────────────────────────────

def test_review_sits_between_active_and_the_terminal_statuses():
    assert WORK_STATUSES == ("backlog", "active", "review", "completed", "discarded")


def test_review_is_not_a_resolved_status():
    """An item awaiting acceptance is not finished: verification can still send
    it back, so it must keep blocking its dependents."""
    assert "review" not in RESOLVED_STATUSES


def test_the_four_new_edges_exist_and_no_others_do():
    assert LEGAL_TRANSITIONS == {
        ("backlog", "active"),
        ("backlog", "discarded"),
        ("active", "review"),
        ("active", "completed"),
        ("active", "discarded"),
        ("review", "active"),
        ("review", "completed"),
        ("review", "discarded"),
    }


def test_nothing_transitions_out_of_a_terminal_status():
    """No reopen edge anywhere: `completed` and `discarded` are sinks."""
    assert not [e for e in LEGAL_TRANSITIONS if e[0] in RESOLVED_STATUSES]


# ── traversal ────────────────────────────────────────────────────────────────

def test_an_item_can_round_trip_through_review_before_completing(tmp_path):
    """The full loop the `rework` edge exists for: submitted, rejected, fixed,
    resubmitted, accepted."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)

    assert st.submit(item.slug).status == "review"
    assert st.rework(item.slug).status == "active"
    assert st.submit(item.slug).status == "review"
    assert st.complete(item.slug, "done", []).status == "completed"


def test_submit_is_illegal_from_backlog(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(IllegalTransition):
        st.submit(item.slug)


def test_rework_is_illegal_from_active(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    with pytest.raises(IllegalTransition):
        st.rework(item.slug)


def test_a_reviewed_item_can_be_abandoned(tmp_path):
    """Without the `(review, discarded)` edge an item in review could not be
    abandoned at all — `complete` maps every non-`done` resolution there."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.submit(item.slug)
    assert st.complete(item.slug, "wontfix", []).status == "discarded"


def test_the_compressed_path_still_completes_straight_from_active(tmp_path):
    """Small changes must not be forced through review."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Small fix", created="2026-01-01")
    st.start(item.slug)
    assert st.complete(item.slug, "done", []).status == "completed"


# ── the one gate ─────────────────────────────────────────────────────────────

def test_rework_refuses_while_refined_outcome_asserts_verification(tmp_path):
    """`refined-outcome.md` says the work was verified and accepted. Sending the
    item back makes that false, so TCW refuses rather than deleting the user's
    document for them."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.submit(item.slug)
    st.write_artifact(item.slug, "refined-outcome", "# Verified\n\nLooks good.\n")

    with pytest.raises(ValueError, match="refined-outcome.md"):
        st.rework(item.slug)
    assert st.get(item.slug).status == "review"        # and it did not move

    (st.path(item.slug) / "refined-outcome.md").unlink()
    assert st.rework(item.slug).status == "active"


def test_an_empty_refined_outcome_does_not_gate_rework(tmp_path):
    """Presence is content-bearing throughout `artifacts()` — a whitespace-only
    file asserts nothing, so it must not block the reverse edge."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.submit(item.slug)
    (st.path(item.slug) / "refined-outcome.md").write_text("   \n", encoding="utf-8")
    assert st.rework(item.slug).status == "active"


def test_refined_outcome_does_not_gate_completion_from_review(tmp_path):
    """The artifact gates `rework` and nothing else: it is the normal path into
    `--resolution done`, and abandoning verified work is a real decision."""
    st = FsWorkStore.open(node(tmp_path))
    for resolution, expected in (("done", "completed"), ("wontfix", "discarded")):
        item = st.create(f"Task {resolution}", created="2026-01-01")
        st.start(item.slug)
        st.submit(item.slug)
        st.write_artifact(item.slug, "refined-outcome", "# Verified\n")
        assert st.complete(item.slug, resolution, []).status == expected


# ── review is an *open* status ───────────────────────────────────────────────

def test_an_item_in_review_still_blocks_its_dependents(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Upstream", created="2026-01-01")
    target = st.create("Downstream", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(blocker.slug)
    st.submit(blocker.slug)

    assert st.unresolved_blockers(st.get(target.slug)) == [blocker.slug]
    with pytest.raises(ValueError, match="blocked by"):
        st.start(target.slug)

    st.complete(blocker.slug, "done", [])
    assert st.start(target.slug).status == "active"


def test_an_epic_cannot_close_while_a_child_is_in_review(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    epic = st.create_work("Epic", created="2026-01-01", type="epic").item
    child = st.create_work("Child", created="2026-01-02", initiative=epic.slug).item
    st.start(epic.slug)
    st.start(child.slug)
    st.submit(child.slug)

    assert not st.epic_completable(st.get(epic.slug))
    with pytest.raises(ValueError, match="initiative children are still open"):
        st.complete(epic.slug, "done", [])


def test_a_review_item_is_on_the_default_board(tmp_path):
    """`list` hides resolved items. `review` is not resolved, so it stays
    visible — a submitted item disappearing from the board would be a bug."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.submit(item.slug)
    assert item.slug in [i.slug for i in st.board()]
    assert [i.slug for i in st.query("review")] == [item.slug]


# ── discovery and addressing ─────────────────────────────────────────────────

def test_a_review_item_resolves_by_slug_and_by_status_path(tmp_path):
    """Discovery globs every status folder and the status-path locator tests
    membership in WORK_STATUSES — both derived, and therefore worth proving
    rather than reading."""
    from tcw.store.fs import resolve_qualified_work_ref

    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.submit(item.slug)

    assert st.get(item.slug).status == "review"
    assert st.path(item.slug).parent.name == "review"

    resolved = resolve_qualified_work_ref(root, f"review/{item.slug}")
    assert resolved is not None and resolved[1] == item.slug
    # the status segment must match the item's real status
    assert resolve_qualified_work_ref(root, f"active/{item.slug}") is None


def test_review_is_a_reserved_project_id():
    """RESERVED_PROJECT_IDS derives from WORK_STATUSES, so adding a status
    silently reserves an id. A node already using it needs a legible failure,
    not a generic one."""
    from tcw.store.project import RESERVED_PROJECT_IDS, validate_project_id
    assert "review" in RESERVED_PROJECT_IDS
    with pytest.raises(ValueError, match="reserved"):
        validate_project_id("review")


# ── nodes that predate the status ────────────────────────────────────────────

def test_a_transition_creates_a_missing_status_folder(tmp_path):
    """Existing nodes were scaffolded with four folders and `git mv` refuses when
    the destination's parent is missing. The repair is status-agnostic, so both
    a never-created and a hand-deleted folder are covered here."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)

    work = root / "docs" / "work"
    for folder in ("review", "completed"):            # simulate a pre-upgrade node
        for p in sorted((work / folder).rglob("*"), reverse=True):
            p.unlink()
        (work / folder).rmdir()
    assert not (work / "review").exists()

    assert st.submit(item.slug).status == "review"
    assert (work / "review" / item.slug).is_dir()
    assert st.complete(item.slug, "done", []).status == "completed"
    assert (work / "completed" / item.slug).is_dir()


def test_a_node_missing_a_status_folder_still_lists(tmp_path):
    """Reading was already safe — `rglob` on a missing directory yields nothing
    rather than raising — but that is load-bearing enough to pin."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    work = root / "docs" / "work"
    for p in sorted((work / "review").rglob("*"), reverse=True):
        p.unlink()
    (work / "review").rmdir()

    assert [i.slug for i in st.board()] == [item.slug]
    assert st.query("review") == []


def test_init_scaffolds_the_review_folder(tmp_path):
    root = node(tmp_path)
    assert (root / "docs" / "work" / "review" / ".gitkeep").is_file()


# ── the new artifact names ───────────────────────────────────────────────────

def test_rework_and_post_mortem_are_addressable_artifacts(tmp_path):
    """Child 1 owns only that the names exist and the set stays bounded; what
    the files must contain is a later child's job."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    for name in ("rework", "post-mortem"):
        st.write_artifact(item.slug, name, f"# {name}\n")
        assert st.artifact_locator(item.slug, name) == str(
            st.path(item.slug) / f"{name}.md")
    present = {a.name for a in st.artifacts(item.slug) if a.present}
    assert {"rework", "post-mortem"} <= present


def test_the_artifact_set_stays_bounded(tmp_path):
    """An unregistered name is refused rather than silently creating a file —
    the folder is a bounded set of named attachments, not an open namespace."""
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(ValueError):
        st.write_artifact(item.slug, "rejected-refined-outcome-2", "# Nope\n")


# ── the CLI surface ──────────────────────────────────────────────────────────

def test_cli_submit_and_rework_round_trip(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    monkeypatch.chdir(root)

    assert main(["work", "start", item.slug]) == 0
    capsys.readouterr()

    assert main(["work", "submit", item.slug]) == 0
    assert "→ review" in capsys.readouterr().out
    assert FsWorkStore.open(root).get(item.slug).status == "review"

    assert main(["work", "rework", item.slug]) == 0
    assert "→ active" in capsys.readouterr().out
    assert FsWorkStore.open(root).get(item.slug).status == "active"


def test_cli_submit_from_backlog_fails_without_a_traceback(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    item = FsWorkStore.open(root).create("Task", created="2026-01-01")
    monkeypatch.chdir(root)

    assert main(["work", "submit", item.slug]) == 1
    assert "not a legal transition" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(item.slug).status == "backlog"


def test_cli_rework_reports_the_blocking_artifact_by_name(tmp_path, monkeypatch, capsys):
    """The refusal has to say which file and what to do about it — the whole
    point is that the operator can act on it without reading the source."""
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.submit(item.slug)
    st.write_artifact(item.slug, "refined-outcome", "# Verified\n")
    monkeypatch.chdir(root)

    assert main(["work", "rework", item.slug]) == 1
    err = capsys.readouterr().err
    assert "refined-outcome.md" in err and "rework.md" in err
    assert FsWorkStore.open(root).get(item.slug).status == "review"


def test_cli_complete_warns_when_the_verify_stage_was_skipped(tmp_path, monkeypatch, capsys):
    """`[prompted]`: the tool must say something. Not a gate — exit status is 0
    and no extra confirmation is read."""
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    monkeypatch.chdir(root)

    assert main(["work", "complete", item.slug, "--resolution", "done", "--confirm"]) == 0
    assert "the verify stage was skipped" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(item.slug).status == "completed"


def test_cli_complete_from_review_does_not_warn(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.submit(item.slug)
    monkeypatch.chdir(root)

    assert main(["work", "complete", item.slug, "--resolution", "done", "--confirm"]) == 0
    assert "verify stage was skipped" not in capsys.readouterr().err


def test_cli_list_shows_a_review_item_with_its_stage_letters(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    st.write_artifact(item.slug, "rework", "# Rework\n")
    st.start(item.slug)
    st.submit(item.slug)
    monkeypatch.chdir(root)

    assert main(["work", "list"]) == 0
    line = next(l for l in capsys.readouterr().out.splitlines() if item.slug in l)
    assert "| review |" in line
    assert "W" in line.split("|")[2]          # the rework artifact's stage letter


# ── the pr field, added and removed within one epic ─────────────────────────

def test_no_pr_field_survives(tmp_path):
    """`pr` was added by this child to hold a pull-request URL, on the prediction
    that `complete --already-integrated` would read it. It did not — that flag
    needs only the `worktree` and `branch` fields that already existed — and
    neither the lifecycle policy work nor the stage documents found a use either.

    Four children passed without a consumer, so it was deleted rather than left
    as a persisted field nothing reads. That is the third time this epic applied
    the pattern, after `phase` and `dod`; the difference is that this one was
    introduced *by* the epic, which is the more useful lesson.
    """
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert not hasattr(item, "pr")
