"""A path held across `submit` writes to a folder the item left. `complete` needs
the verify artifact, the stray folder is reported, a slug held twice is a
problem not a crash, and printed folders are reachable from here (spec:
2026-09-29-make-a-stale-item-path-fail-loudly-…)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsWorkStore

from test_recursion import commit_all, mk_node


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True).stdout


def settle(root: Path, msg: str = "setup") -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", msg)


@pytest.fixture
def in_review(tmp_path, monkeypatch, capsys):
    """An item in review with outcome.md and no refined-outcome.md."""
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    assert main(["work", "new", "Stale path"]) == 0
    slug = capsys.readouterr().out.strip()
    settle(root)
    assert main(["work", "start", slug]) == 0
    (root / "docs/work/active" / slug / "outcome.md").write_text("# Outcome\n\ndone\n")
    settle(root)
    assert main(["work", "submit", slug]) == 0
    capsys.readouterr()
    return root, slug


def complete(slug: str, *extra: str) -> int:
    return main(["work", "complete", slug, "--resolution", "done", "--confirm", *extra])


# ── 1, 2: the verify artifact ───────────────────────────────────────────────

def test_done_from_review_needs_refined_outcome(in_review, capsys):
    root, slug = in_review
    assert complete(slug) == 1
    err = capsys.readouterr().err
    assert "refined-outcome.md" in err and f"tcw work path {slug}" in err, err
    assert FsWorkStore.open(root).get(slug).status == "review"


def test_force_overrides_it(in_review, capsys):
    root, slug = in_review
    assert complete(slug, "--force") == 0, capsys.readouterr().err
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_a_discard_from_review_needs_nothing(in_review, capsys):
    root, slug = in_review
    assert main(["work", "complete", slug, "--resolution", "wontfix", "--confirm"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "discarded"


def test_done_with_refined_outcome_completes(in_review, capsys):
    root, slug = in_review
    (root / "docs/work/review" / slug / "refined-outcome.md").write_text("# Accepted\n")
    settle(root)
    assert complete(slug) == 0, capsys.readouterr().err


def test_done_from_active_is_unchanged(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    assert main(["work", "new", "Straight through"]) == 0
    slug = capsys.readouterr().out.strip()
    settle(root)
    assert main(["work", "start", slug]) == 0
    (root / "docs/work/active" / slug / "outcome.md").write_text("# Outcome\n")
    settle(root)
    assert complete(slug) == 0, capsys.readouterr().err


def test_the_store_refuses_too(in_review):
    """The web app completes through the store, not the CLI."""
    root, slug = in_review
    st = FsWorkStore.open(root)
    with pytest.raises(ValueError, match="refined-outcome.md"):
        st.complete(slug, "done", [])
    st.complete(slug, "done", [], force=True)


# ── 3: a worktree item is refused before the merge-back ─────────────────────

def test_a_worktree_item_is_refused_before_its_branch_merges(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    assert main(["work", "new", "In a worktree"]) == 0
    slug = capsys.readouterr().out.strip()
    settle(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    wt = root / ".worktrees" / slug
    (wt / "code.txt").write_text("work\n")
    (wt / "docs/work/active" / slug / "outcome.md").write_text("# Outcome\n")
    git(wt, "add", "-A")
    git(wt, "commit", "-qm", "work")
    assert main(["work", "submit", slug]) == 0
    capsys.readouterr()
    head = git(root, "rev-parse", "HEAD")

    assert complete(slug) == 1
    assert "refined-outcome.md" in capsys.readouterr().err
    assert git(root, "rev-parse", "HEAD") == head
    assert not (root / "code.txt").exists()
    assert git(root, "branch", "--list", f"work/{slug}").strip()


# ── 4, 5: the stray folder ──────────────────────────────────────────────────

def test_a_write_through_the_old_path_is_named(in_review, capsys):
    root, slug = in_review
    stray = root / "docs/work/active" / slug
    stray.mkdir(parents=True)
    (stray / "refined-outcome.md").write_text("# Accepted, in the wrong place\n")

    assert complete(slug) == 1
    err = capsys.readouterr().err
    assert f"docs/work/active/{slug}" in err and "refined-outcome.md" in err, err

    assert main(["validate"]) == 1
    out = capsys.readouterr()
    text = out.out + out.err
    assert f"work/active/{slug}" in text and "refined-outcome.md" in text, text


@pytest.mark.parametrize("contents", [[], [".DS_Store"]])
def test_an_empty_leftover_is_not_reported(in_review, capsys, contents):
    root, slug = in_review
    stray = root / "docs/work/active" / slug
    stray.mkdir(parents=True)
    for name in contents:
        (stray / name).write_text("")
    assert FsWorkStore.open(root).stray_folders() == []
    assert FsWorkStore.open(root).stray_folders(slug) == []


def test_a_stray_folder_is_a_warning_when_nothing_else_is_wrong(in_review, capsys):
    root, slug = in_review
    (root / "docs/work/review" / slug / "refined-outcome.md").write_text("# Accepted\n")
    settle(root)
    stray = root / "docs/work/active" / slug
    stray.mkdir(parents=True)
    (stray / "notes.md").write_text("late\n")
    assert complete(slug) == 0
    assert f"docs/work/active/{slug}" in capsys.readouterr().err


# ── 6: one slug, two folders ────────────────────────────────────────────────

def test_a_slug_held_twice_is_reported_not_crashed_on(in_review, capsys):
    root, slug = in_review
    import shutil
    shutil.copytree(root / "docs/work/review" / slug, root / "docs/work/active" / slug)
    assert main(["validate"]) == 1
    out = capsys.readouterr()
    text = out.out + out.err
    assert "Traceback" not in text
    assert f"work/active/{slug}" in text and f"work/review/{slug}" in text, text


def test_the_web_apps_per_item_validation_returns_the_problem(in_review):
    """The web app validates the one item it just wrote; a duplicate used to
    raise `MultipleMatch` out of it, which the handler turned into a warning
    that validation "could not complete"."""
    from tcw.validate import ValidationTarget, validate
    import shutil
    root, slug = in_review
    shutil.copytree(root / "docs/work/review" / slug, root / "docs/work/active" / slug)
    problems = validate(root, target=ValidationTarget(axis="work", ref=slug))
    assert any("held by 2 folders" in p for p in problems), problems


# ── 7: the stage text ───────────────────────────────────────────────────────

@pytest.mark.parametrize("stage", ["verify", "implement"])
def test_the_stage_text_says_where_to_write(in_review, capsys, stage):
    root, slug = in_review
    assert main(["work", "stage", "prompt", stage, slug]) in (0, 1)
    assert f"tcw work path" in capsys.readouterr().out


# ── 8: printed folders ──────────────────────────────────────────────────────

def test_a_child_items_folder_is_printed_from_here(tmp_path, monkeypatch, capsys):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)
    commit_all(parent)
    slug = FsWorkStore.open(child).create("Child work", created="2026-01-01").slug
    commit_all(child, "add")
    monkeypatch.chdir(parent)
    assert main(["work", "start", f"child/{slug}"]) == 0
    printed = capsys.readouterr().out.split("→", 1)[1].split()[0]
    assert (parent / printed).is_dir(), printed


# ── review follow-ups ────────────────────────────────────────────────────────

def test_submit_run_in_the_worktree_is_refused_before_the_merge(tmp_path, monkeypatch, capsys):
    """The primary copy still reads `active`; the branch's reads `review`."""
    import test_worktree_completion as h
    root = h.repo(tmp_path)
    slug = h.new_item(root, monkeypatch, capsys)
    wt = h.start_worktree(root, slug, monkeypatch, capsys)
    h.branch_commit(wt)
    assert h.run_in(wt, monkeypatch, capsys, "work", "submit", slug)[0] == 0
    tip = h.head(h._top(wt))
    code, _, err = h.run_in(root, monkeypatch, capsys, "work", "complete", slug,
                            "--resolution", "done", "--confirm")
    assert code == 1 and "refined-outcome.md" in err, err
    assert h._git(root, "merge-base", "--is-ancestor", tip, "HEAD").returncode != 0


def test_refined_outcome_in_the_primary_copy_is_enough(tmp_path, monkeypatch, capsys):
    import test_worktree_completion as h
    root = h.repo(tmp_path)
    slug = h.new_item(root, monkeypatch, capsys)
    wt = h.start_worktree(root, slug, monkeypatch, capsys)
    h.branch_commit(wt)
    assert h.run_in(root, monkeypatch, capsys, "work", "submit", slug)[0] == 0
    FsWorkStore.open(root).write_artifact(slug, "refined-outcome", "# Accepted\n")
    h.commit_all(h._top(root), "accepted in primary")
    code, _, err = h.run_in(root, monkeypatch, capsys, "work", "complete", slug,
                            "--resolution", "done", "--confirm")
    assert code == 0, err


def test_an_epic_in_review_closes_without_one(tmp_path):
    import test_epic_completable as e
    from tcw.work.recursion import reconcile
    root = e.mk_node(tmp_path)
    st = FsWorkStore.open(root)
    epic = e.make_epic(st, n_done=1, n_open=0)
    st.start(epic, force=True)
    st.submit(epic)
    reconcile(root, epic, complete_when_ready=True)
    assert FsWorkStore.open(root).get(epic).status == "completed"


def test_a_nested_childs_old_spot_is_found(tmp_path):
    import shutil
    import test_epic_completable as e
    root = e.mk_node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01").slug
    c = st.create("Child", created="2026-01-01", parent=p).slug
    shutil.move(str(st.path(c)), str(st.path(p) / c))          # the older nested layout
    settle(root)
    old = FsWorkStore.open(root).path(c)
    FsWorkStore.open(root).start(c, force=True)
    old.mkdir(parents=True, exist_ok=True)
    (old / "outcome.md").write_text("x\n")
    assert [f for f, _ in FsWorkStore.open(root).stray_folders(c)] == [old]


def test_artifacts_is_abstract_and_the_scans_are_not():
    from tcw.store.base import WorkStore
    assert "artifacts" in WorkStore.__abstractmethods__
    assert not {"stray_folders", "duplicate_slugs"} & WorkStore.__abstractmethods__


def test_the_refusal_comes_before_the_checklist(in_review, capsys):
    root, slug = in_review
    assert main(["work", "complete", slug, "--resolution", "done"]) == 1
    err = capsys.readouterr()
    assert "refined-outcome.md" in err.err and "[ ]" not in err.out + err.err
