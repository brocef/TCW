"""Writes outside a git repository refuse before touching the filesystem.

TCW's contract is that **reads** work anywhere and **writes** need a repository.
The refusal used to be inconsistent: `tcw init` said so in one line, while every
store write died in `git_stage` with an unhandled `CalledProcessError` — after
creating the item, moving it, or rewriting the config it was about to stage.

The guard is a filesystem-adapter precondition (`require_repository`), not a
model concept: a remote store has no repository to require. It sits in two
places — the `_stage`/`_rm`/`_mv` funnel, so no git failure can escape as a
traceback, and the public write methods whose first mutation *precedes* their
staging call, so nothing lands before the refusal.
"""
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import (
    NOT_A_REPOSITORY, SENTINEL, FsCapabilitiesStore, FsTaxonomyStore, FsTreeStore,
    FsWorkStore, init,
    require_repository,
)

REFUSED = "not inside a git repository"


def git_init(root: Path) -> Path:
    """An empty git repository at `root`, committer identity configured."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    return root


def commit_all(root: Path, message: str = "seed") -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", message], check=True)


def repo(tmp_path: Path, name: str = "repo") -> Path:
    """A committed TCW node inside a git repository."""
    root = git_init(tmp_path / name)
    init(["taxonomy", "capabilities", "work"], root, name.lower())
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    return root


def manifest(root: Path) -> dict[str, str]:
    """Every path under `root`, **directories included**.

    A file-only map would call a run clean that left `docs/work/.claiming/`
    behind — `FsWorkStore.start` creates that directory before it renames
    anything. An empty directory is a partial write too, and so is a symlink:
    recorded by its target, before `is_dir()`/`read_bytes()` get a chance to
    follow it into a file that may not be there.
    """
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root))
        if p.is_symlink():
            out[rel] = f"<symlink:{p.readlink()}>"
        else:
            out[rel] = "<dir>" if p.is_dir() else hashlib.sha256(
                p.read_bytes()).hexdigest()
    return out


def refuses(store, call) -> None:
    """`call` is refused, and nothing under the store's node moved."""
    before = manifest(store.node_root)
    with pytest.raises(ValueError, match=REFUSED):
        call()
    assert manifest(store.node_root) == before


@pytest.fixture
def unrepo(tmp_path):
    """A seeded node whose repository was removed after the seeding committed.

    The reachable shape: `tcw init` refuses outside a repository, so a node
    without one arrives by the repository being deleted, by an export, or by a
    `docs/` tree vendored into a plain directory.
    """
    root = repo(tmp_path)
    work = FsWorkStore.open(root)
    work.create("Backlog item", created="2026-01-01")
    active = work.create("Active item", created="2026-01-02")
    work.start(active.slug, owner="t")
    FsTaxonomyStore.open(root).add("Widget", slug="widget")
    FsCapabilitiesStore.open(root).add("seeded/cap", "Seeded cap")
    (root / "docs" / "work" / "inbox" / "raw.md").write_text(
        "# Raw\n\nbody\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    shutil.rmtree(root / ".git")
    return root


# ── The precondition itself ──────────────────────────────────────────────────


def test_require_repository_accepts_a_repository(tmp_path):
    assert require_repository(repo(tmp_path)) is None


def test_require_repository_refuses_a_plain_directory(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(ValueError) as e:
        require_repository(plain)
    assert str(e.value) == NOT_A_REPOSITORY


def test_each_store_checks_the_repository_it_actually_writes_to(split_repos):
    """A work store's repository can differ from its node's (`work.path`).

    Built on a genuinely external store: the earlier version of this test used a
    default store, where `store_git_root == node_root`, so it passed whether or
    not `FsWorkStore._write_git_root` overrode the base implementation — and that
    blind spot is why the two split-ownership defects below reached `verify`.
    """
    code, store, _ = split_repos
    work = FsWorkStore.open(code)
    assert work.store_git_root != work.node_root          # the premise, asserted
    assert work.store_git_root == store
    assert work._write_git_root() == work.store_git_root
    taxonomy = FsTaxonomyStore.open(code)
    assert taxonomy._write_git_root() == taxonomy.node_root == code


def test_the_guard_holds_no_state_because_it_could_not_be_initialized(tmp_path):
    """Why `_require_repository` re-probes instead of caching.

    `FsWorkStore.__init__` does not chain to `FsTreeStore.__init__` — it assigns
    `root`/`node_root`/`store_git_root`/`config` itself — so any attribute added
    to the base initializer is simply absent on every work store, and the first
    work write would raise `AttributeError`. If someone makes the guard stateful
    later, this is the test that has to be read first.
    """
    assert FsWorkStore.__init__ is not FsTreeStore.__init__
    root = repo(tmp_path)
    assert FsWorkStore.open(root)._require_repository() is None


# ── The work store ───────────────────────────────────────────────────────────


def test_every_work_write_is_refused_and_writes_nothing(unrepo):
    st = FsWorkStore.open(unrepo)
    backlog = st.query("backlog")[0].slug
    active = st.query("active")[0].slug

    refuses(st, lambda: st.create_work("New", created="2026-01-03"))
    refuses(st, lambda: st.update_work(backlog, title="Renamed"))
    refuses(st, lambda: st.start(backlog, owner="t"))
    refuses(st, lambda: st.submit(active))            # _effect_transition
    refuses(st, lambda: st.set_field(backlog, "priority", 1))
    refuses(st, lambda: st.register_tags(["demo"]))
    refuses(st, lambda: st.unregister_tags(["demo"]))
    refuses(st, lambda: st.inbox_accept("raw.md"))
    refuses(st, lambda: st.write_artifact(backlog, "spec", "# Spec\n"))
    refuses(st, lambda: st.write_draft(backlog, "spec", "# Draft\n"))
    refuses(st, lambda: st.write_sidecar(backlog, "capabilities.yaml", "changed: []\n"))
    refuses(st, lambda: st.write_plan_stage(backlog, "one", "# Stage\n"))
    refuses(st, lambda: st.drop(backlog))             # _delete → _rm (Tier 1 only)


def test_a_no_change_update_still_succeeds_outside_a_repository(unrepo):
    """Placement, not just presence.

    `update_work` returns before writing when nothing changed. A guard at the
    top of the method would turn that read-shaped call into a refusal, so the
    guard sits after the no-change decision and before `_atomic_write_all`.
    """
    st = FsWorkStore.open(unrepo)
    slug = st.query("backlog")[0].slug
    before = manifest(unrepo)
    assert st.update_work(slug).item.slug == slug     # no fields → no write
    assert manifest(unrepo) == before


def test_start_is_refused_before_it_makes_the_claiming_folder(tmp_path):
    """`start` reaches `git_stage` directly, bypassing `_stage`, on both its
    branches, and both rename before they stage — so the guard has to be its
    literal first statement, ahead of the `.claiming/` directory it creates.

    A fresh node rather than the shared fixture: `.claiming/` survives a
    *successful* `start` (nothing removes it), so a node that has ever started
    an item cannot tell "not created" from "already there".
    """
    root = repo(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create("Task", created="2026-01-01").slug
    shutil.rmtree(root / ".git")
    claiming = root / "docs" / "work" / ".claiming"
    assert not claiming.exists()
    refuses(st, lambda: st.start(slug, owner="t"))
    refuses(st, lambda: st.start(slug, owner="t", take_over=True))
    assert not claiming.exists()


def test_a_repository_removed_after_a_successful_write_still_refuses(tmp_path):
    """Repository membership is not frozen for a store's lifetime.

    The same instance that just wrote successfully must re-check. This is the
    test a memoized guard would fail, and the reason the guard holds no state.
    """
    root = repo(tmp_path)
    st = FsWorkStore.open(root)
    st.create("First", created="2026-01-01")
    shutil.rmtree(root / ".git")
    backlog = root / "docs" / "work" / "backlog"
    before = manifest(backlog)
    with pytest.raises(ValueError, match=REFUSED):
        st.create("Second", created="2026-01-01")
    assert manifest(backlog) == before


def test_reads_do_not_acquire_a_repository_precondition(unrepo):
    """Goal 4: the guard must not leak into a read path through a shared helper."""
    st = FsWorkStore.open(unrepo)
    slug = st.query("backlog")[0].slug
    assert len(st.query()) == 2
    assert st.get(slug).slug == slug
    assert st.get_detail(slug) is not None
    assert st.locate(slug)
    assert st.check() == []
    assert st.board() is not None
    assert st.inbox_list()
    assert st.inbox_show("raw.md") is not None
    assert st.registered_tags() == []
    assert st._validation_resources(slug)          # targeted `tcw validate`


# ── The taxonomy and capabilities stores ─────────────────────────────────────


def test_every_taxonomy_write_is_refused_and_writes_nothing(unrepo):
    st = FsTaxonomyStore.open(unrepo)
    refuses(st, lambda: st.add("Gadget", slug="gadget"))
    assert not (unrepo / "docs" / "taxonomy" / "gadget").exists()
    refuses(st, lambda: st.update_term("widget", name="Renamed"))
    refuses(st, lambda: st.remove("widget"))
    refuses(st, lambda: st.extends_add("other"))
    refuses(st, lambda: st.extends_remove("other"))


def test_every_capability_write_is_refused_and_writes_nothing(unrepo):
    st = FsCapabilitiesStore.open(unrepo)
    refuses(st, lambda: st.add("doing/a-thing", "Do a thing"))
    assert not (unrepo / "docs" / "capabilities" / "doing").exists()
    refuses(st, lambda: st.set("seeded/cap", {"Status": "Supported"}))
    refuses(st, lambda: st.update_capability("seeded/cap", body="new"))
    refuses(st, lambda: st.remove("seeded/cap"))
    # `reset` is not here: it refuses a *local* capability on its own terms
    # ("not an override") before any git path, and reaching its `_rm` needs a
    # federated override. That `_rm` is the same Tier-1 guard `remove` exercises
    # one line above.
    refuses(st, lambda: st.extends_add("other"))
    refuses(st, lambda: st.extends_remove("other"))


def test_tree_store_reads_do_not_acquire_a_repository_precondition(unrepo):
    """Goal 4, the other two stores: `_write_node`'s guard must not reach a read."""
    tax = FsTaxonomyStore.open(unrepo)
    assert [t.slug for t in tax.list_all(local_only=True)] == ["widget"]
    assert tax.get("widget") is not None
    assert tax.get_term_detail("widget") is not None
    assert tax.search("widget")
    assert tax.check() == []
    assert tax.relators("widget") == []
    assert tax.__class__.__mro__          # sanity: store constructed at all
    assert tax._validation_resources("widget")

    cap = FsCapabilitiesStore.open(unrepo)
    assert [c.path for c in cap.list_all(local_only=True)] == ["seeded/cap"]
    assert cap.get("seeded/cap") is not None
    assert cap.get_capability_detail("seeded/cap") is not None
    assert cap.search("cap")
    assert cap.check(taxonomy=tax) == []
    assert cap.unreviewed_inherited() == []
    assert cap._validation_resources("seeded/cap")


# ── The CLI boundary ─────────────────────────────────────────────────────────


def test_init_refuses_with_the_shared_wording(tmp_path, monkeypatch, capsys):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)
    assert main(["init", "--id", "x"]) == 1
    assert capsys.readouterr().err == (
        "tcw init: not inside a git repository. Run `git init` first.\n")


def test_a_git_subprocess_failure_is_a_message_not_a_traceback(
    tmp_path, monkeypatch, capsys
):
    """The generic handler, checked behaviorally rather than by reading source.

    The same injected git failure through three different components produces
    the identical line. That is what "carries no per-command policy" means; an
    assertion about the handler's source text would pass or fail for reasons
    that have nothing to do with coupling.
    """
    root = repo(tmp_path)
    FsWorkStore.open(root).create("Task", created="2026-01-01")
    monkeypatch.chdir(root)

    def boom(*args, **kwargs):
        raise subprocess.CalledProcessError(128, ["git", "add", "x"])

    # `git_stage`, not `_git`: patching `_git` would break `git_root` too, and
    # the repository guard would answer first. The failure being modelled here
    # is a repository that exists and refuses — a held `index.lock`, a rejecting
    # hook, a path git will not stage — which is exactly what reaches staging.
    monkeypatch.setattr("tcw.store.fs.git_stage", boom)

    seen = set()
    for argv in (["work", "new", "T"],
                 ["taxonomy", "add", "Gadget", "--slug", "gadget"],
                 ["capabilities", "add", "a/b", "Thing"]):
        assert main(argv) != 0, argv
        err = capsys.readouterr().err
        assert "Traceback" not in err, argv
        seen.add(err)
    assert seen == {"tcw: git command failed (exit 128): git add x\n"}


# ── Every public CLI write, end to end ───────────────────────────────────────


REFUSAL = re.compile(
    r"^tcw[a-z ]*: not inside a git repository\. Run `git init` first\.$")


@pytest.fixture
def graph(tmp_path):
    """A connected parent/child pair, seeded and committed, then de-gitted.

    Both repositories lose `.git`, because `delegate` writes into the child's
    store and `escalate` into the parent's — a half-git graph would prove the
    wrong thing.
    """
    parent, child = repo(tmp_path, "parent"), repo(tmp_path, "child")
    (parent / "tcw-config.yaml").write_text(
        "id: parent\nconnected-projects:\n  children:\n    child: ../child\n",
        encoding="utf-8")
    (child / "tcw-config.yaml").write_text(
        "id: child\nconnected-projects:\n  parent:\n    parent: ../parent\n",
        encoding="utf-8")
    work = FsWorkStore.open(parent)
    work.create("Backlog item", created="2026-01-01")
    review = work.create("Review item", created="2026-01-02")
    work.start(review.slug, owner="t")
    work.submit(review.slug)
    active = work.create("Active item", created="2026-01-04")
    work.start(active.slug, owner="t")
    epic = work.create_work("Epic item", created="2026-01-03", type="epic").item
    FsTaxonomyStore.open(parent).add("Widget", slug="widget")
    FsCapabilitiesStore.open(parent).add("seeded/cap", "Seeded cap")
    (parent / "docs" / "work" / "inbox" / "raw.md").write_text(
        "# Raw\n\nbody\n", encoding="utf-8")
    for root in (parent, child):
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
        shutil.rmtree(root / ".git")
    return parent, child, epic.slug


def test_every_cli_write_refuses_with_one_wording_and_writes_nothing(
    graph, monkeypatch, capsys
):
    parent, child, epic = graph
    st = FsWorkStore.open(parent)
    backlog = [i.slug for i in st.query("backlog") if i.slug != epic][0]
    review = st.query("review")[0].slug
    active = st.query("active")[0].slug
    monkeypatch.chdir(parent)

    commands = [
        ["init", "--id", "parent"],
        ["work", "init"],
        ["taxonomy", "init"],
        ["capabilities", "init"],
        ["work", "new", "T"],
        ["work", "start", backlog],
        ["work", "start", backlog, "--worktree"],
        ["work", "start", backlog, "--take-over", "--owner", "me"],
        ["work", "edit", backlog, "--title", "Renamed"],
        ["work", "rework", review],
        ["work", "submit", active],
        ["work", "complete", review, "--resolution", "done", "--confirm"],
        ["work", "complete", review, "--resolution", "wontfix", "--confirm"],
        ["work", "drop", backlog, "--confirm"],
        ["work", "tags", "add", "demo"],
        ["work", "tags", "rm", "demo"],
        ["work", "scaffold", "spec", backlog],
        ["work", "inbox", "accept", "raw.md"],
        ["work", "reconcile", epic],
        ["work", "delegate", "child", "T"],
        ["taxonomy", "add", "Gadget", "--slug", "gadget"],
        ["taxonomy", "rm", "widget"],
        ["taxonomy", "extends", "add", "child"],
        ["taxonomy", "extends", "rm", "child"],
        ["capabilities", "add", "other/thing", "Other"],
        ["capabilities", "set", "seeded/cap", "--status", "Supported"],
        ["capabilities", "extends", "child"],          # not `extends add`
        ["capabilities", "extends", "child", "--rm"],
    ]
    graph_before = manifest(parent.parent)
    for argv in commands:
        assert main(argv) == 1, argv
        err = capsys.readouterr().err
        assert "Traceback" not in err, (argv, err)
        assert [ln for ln in err.splitlines() if ln] == [
            ln for ln in err.splitlines() if ln and REFUSAL.match(ln)], (argv, err)
        assert manifest(parent.parent) == graph_before, argv

    monkeypatch.chdir(child)                     # escalate writes the parent's inbox
    assert main(["work", "escalate", "T"]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert any(REFUSAL.match(ln) for ln in err.splitlines())
    assert manifest(parent.parent) == graph_before


def test_start_leaves_the_item_in_backlog(graph, monkeypatch, capsys):
    """The sharpest regression: `start` used to move the item and *then* fail."""
    parent, _, epic = graph
    st = FsWorkStore.open(parent)
    backlog = [i.slug for i in st.query("backlog") if i.slug != epic][0]
    monkeypatch.chdir(parent)
    assert main(["work", "start", backlog]) == 1
    capsys.readouterr()
    assert (parent / "docs" / "work" / "backlog" / backlog).is_dir()
    assert not (parent / "docs" / "work" / "active" / backlog).exists()


# ── Reads, byte-for-byte against the pre-change tree ─────────────────────────


GOLDEN = Path(__file__).parent / "fixtures" / "non_git_reads"
READS = [
    ["work", "list"], ["work", "nodes"], ["validate"],
    ["taxonomy", "list"], ["taxonomy", "show", "widget"],
    ["capabilities", "list"], ["capabilities", "show", "seeded/cap"],
]


def _normalize(text: str, root: Path) -> str:
    """Only what cannot be reproduced: the tmp root, the minted capability id,
    and the claim's wall-clock timestamp."""
    text = text.replace(str(root), "<ROOT>")
    text = re.sub(r"cap-[0-9a-f]{6}", "cap-<ID>", text)
    return re.sub(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z", "<TS>", text)


@pytest.mark.parametrize("argv", READS, ids=lambda a: "-".join(a))
def test_read_output_is_unchanged_outside_a_repository(argv, unrepo, monkeypatch,
                                                       capsys):
    """Goal 4, pinned against output captured from the tree *before* the guard.

    The golden files in `fixtures/non_git_reads/` were produced by running these
    same commands at the pre-change commit in this same fixture (see the item's
    outcome.md). No historical checkout is needed to check them.
    """
    monkeypatch.chdir(unrepo)
    assert main(argv) == 0
    got = _normalize(capsys.readouterr().out, unrepo)
    name = "-".join(argv).replace("/", "_") + ".txt"
    assert got == (GOLDEN / name).read_text(encoding="utf-8")


# ── Split ownership: a work store in another repository ──────────────────────
#
# Every defect in this section is the same mistake: a flow that writes to *two*
# repositories, guarded against one. With a default store the two are the same
# directory, so the 28-command matrix above — which removes every repository in
# the graph at once — cannot see any of it.


@pytest.fixture
def split_repos(tmp_path):
    """A node in one repository whose work store is in another (`work.path`).

    Both repositories present and committed; the item is in `backlog/`. Tests
    remove whichever `.git` the case needs.
    """
    store = git_init(tmp_path / "store")
    subprocess.run(["git", "-C", str(store), "commit", "-q", "--allow-empty",
                    "-m", "seed"], check=True)
    code = git_init(tmp_path / "code")
    init(["taxonomy", "capabilities", "work"], code, "demo",
         work_path=store / "work")
    commit_all(code)
    commit_all(store)
    item = FsWorkStore.open(code).create("A thing", created="2026-01-01")
    commit_all(store, "item")
    return code, store, item.slug


def test_start_worktree_is_refused_when_only_the_node_has_no_repository(
    split_repos, monkeypatch, capsys
):
    """`--worktree` writes the *node's* `.gitignore`, not the store's.

    The store guard passes — `work.path` is still in its own repository — so
    without a check of its own `start` moved the item to `active/`, wrote
    `.worktrees/` into `.gitignore`, and only then died in `git add`.
    """
    code, store, slug = split_repos
    shutil.rmtree(code / ".git")
    monkeypatch.chdir(code)
    before = manifest(code.parent)
    assert main(["work", "start", slug, "--worktree", "--owner", "t@t"]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err, err
    assert [ln for ln in err.splitlines() if ln] == [
        ln for ln in err.splitlines() if ln and REFUSAL.match(ln)], err
    assert manifest(code.parent) == before
    assert (store / "work" / "backlog" / slug).is_dir()
    assert not (store / "work" / "active" / slug).exists()


def test_a_plain_start_still_works_when_only_the_node_has_no_repository(
    split_repos, monkeypatch, capsys
):
    """The guard above is scoped to `--worktree`, which is what needs the node.

    A plain `start` writes only the store, so it must keep succeeding — the
    external-store split is a supported configuration, not a broken one.
    """
    code, store, slug = split_repos
    shutil.rmtree(code / ".git")
    monkeypatch.chdir(code)
    assert main(["work", "start", slug, "--owner", "t@t"]) == 0
    capsys.readouterr()
    assert (store / "work" / "active" / slug).is_dir()


def test_complete_refuses_when_the_merge_back_has_no_repository(
    split_repos, monkeypatch, capsys
):
    """A skipped merge-back must not be reported as a completion.

    `merge_worktree` read *any* failed `rev-parse` as "branch already gone", and
    outside a repository that lookup fails with 128 — so completion sailed past
    the merge, exited 0, and left the work branch unmerged. A partial write
    announces itself; a false completion does not.
    """
    code, store, slug = split_repos
    monkeypatch.chdir(code)
    assert main(["work", "start", slug, "--worktree", "--owner", "t@t"]) == 0
    capsys.readouterr()
    worktree = code / ".worktrees" / slug
    assert worktree.is_dir()
    shutil.rmtree(code / ".git")

    assert main(["work", "complete", slug, "--resolution", "done",
                 "--confirm", "--force"]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err, err
    assert f"work/{slug}" in err, err                  # names the branch at risk
    assert (store / "work" / "active" / slug).is_dir()  # not completed
    assert not (store / "work" / "completed" / slug).exists()
    assert worktree.is_dir()                            # teardown skipped too


# ── `init --work-path`: two locations, checked last ───────────────────────────


def test_init_refuses_an_external_work_path_before_it_writes_anything(tmp_path):
    """`init` scaffolded both locations and *then* refused.

    It wrote the sentinel, rewrote `tcw-config.yaml` with `work.path`, created
    all six status folders and every `.gitkeep`, and only then checked whether
    the target was in a repository — so the refusal was real and the residue was
    total.
    """
    code = git_init(tmp_path / "code")
    plain = tmp_path / "plain"
    plain.mkdir()
    before = manifest(tmp_path)
    with pytest.raises(ValueError, match="not inside a Git repository"):
        init(["work"], code, "demo", work_path=plain / "work")
    assert manifest(tmp_path) == before


def test_init_refuses_a_work_path_git_would_never_track(tmp_path):
    """Inside a repository is not the same as tracked by it.

    A store under an ignored path passes every git-repository check and then
    disappears: `git_stage` drops ignored paths from the `git add` it builds, so
    every item written there is real on disk and invisible to git — the failure
    mode the whole external-store contract exists to prevent.
    """
    code = git_init(tmp_path / "code")
    (code / ".gitignore").write_text("external/\n", encoding="utf-8")
    commit_all(code)
    before = manifest(code)
    with pytest.raises(ValueError, match="gitignored"):
        init(["work"], code, "demo", work_path=code / "external" / "work")
    assert manifest(code) == before


def test_init_refuses_a_work_path_behind_a_broken_symlink(tmp_path):
    """`Path.exists()` follows symlinks, so a dangling one looks absent.

    The nearest-existing-ancestor walk then skipped it, found the enclosing
    repository, accepted the target — and `mkdir` died on `FileExistsError`
    *after* the sentinel was written. A broken symlink is a path that exists as
    far as anything creating a directory is concerned.
    """
    code = git_init(tmp_path / "code")
    (code / "link").symlink_to(tmp_path / "nowhere")
    before = manifest(code)
    with pytest.raises(ValueError, match="not inside a Git repository"):
        init(["work"], code, "demo", work_path=code / "link" / "work")
    assert manifest(code) == before


def test_init_refuses_a_non_pristine_default_store_before_writing_the_sentinel(
    tmp_path
):
    """The refusal was already right; its placement was not.

    `write_sentinel` ran first, so declining to replace an existing `docs/work`
    still left a new `tcw-config.yaml` in a project that had none.
    """
    code = git_init(tmp_path / "code")
    store = git_init(tmp_path / "store")
    item = code / "docs" / "work" / "backlog" / "existing"
    item.mkdir(parents=True)
    (item / "state.yaml").write_text("status: backlog\n", encoding="utf-8")
    before = manifest(code)
    with pytest.raises(ValueError, match="non-pristine"):
        init(["work"], code, "demo", work_path=store / "work")
    assert manifest(code) == before
    assert not (code / SENTINEL).exists()


def test_init_refuses_a_store_the_ignore_rules_hide_even_once_it_is_tracked(
    tmp_path
):
    """`git check-ignore` answers about *this* path, not about the rules.

    It reports a tracked path as not ignored however the rules read, which is
    right for the staging callers — it mirrors what `git add` will do — and
    wrong here, where the question is whether files written there *later* get
    recorded. A store scaffolded, committed, and only then covered by a new
    ignore rule reproduces round two's silent-untracked-work outcome exactly.
    """
    code = git_init(tmp_path / "code")
    init(["work"], code, "demo", work_path=code / "external" / "work")
    commit_all(code)
    (code / ".gitignore").write_text("external/\n", encoding="utf-8")
    commit_all(code, "ignore it")
    before = manifest(code)
    with pytest.raises(ValueError, match="gitignored"):
        init(["work"], code, "demo", work_path=code / "external" / "work")
    assert manifest(code) == before


def test_init_re_runs_on_a_healthy_external_store(tmp_path):
    """The other side of the check above, and the regression it could cause.

    TCW's own scaffolding writes ignore rules for `completed/*` and
    `discarded/*` under the store prefix. Those cover status folders, never the
    store root — but an ignore check strict enough to catch the case above is
    exactly the one that could start refusing TCW's own healthy store, so it is
    re-run here both before and after the scaffold is committed.
    """
    code = git_init(tmp_path / "code")
    store = git_init(tmp_path / "store")
    init(["work"], code, "demo", work_path=store / "work")
    init(["work"], code, "demo", work_path=store / "work")      # uncommitted
    commit_all(code)
    commit_all(store)
    init(["work"], code, "demo", work_path=store / "work")      # tracked
    assert (store / "work" / "backlog" / ".gitkeep").is_file()


def test_init_refuses_when_a_status_folder_is_occupied_by_a_file(tmp_path):
    """The leaves are known before any of them is created, so check them there.

    `mkdir(parents=True, exist_ok=True)` raises on a leaf that exists as a file
    and on a parent that does, and it raised *after* the sentinel and the
    earlier leaves had landed — the same mutate-then-raise shape as every other
    defect in this item, arriving through the filesystem rather than through git.
    """
    code = git_init(tmp_path / "code")
    store = git_init(tmp_path / "store")
    (store / "work").mkdir()
    (store / "work" / "backlog").write_text("not a directory\n", encoding="utf-8")
    before = manifest(code), manifest(store)
    with pytest.raises(ValueError, match="not a directory"):
        init(["work"], code, "demo", work_path=store / "work")
    assert (manifest(code), manifest(store)) == before


def test_init_refuses_a_default_store_that_is_a_symlink(tmp_path):
    """A symlinked `docs/work` reads as pristine through the link.

    It then reached `shutil.rmtree`, which refuses a symlink — after
    `write_sentinel` had run. Replacing a default store means deleting it, and a
    symlink is someone else's directory.
    """
    code = git_init(tmp_path / "code")
    store = git_init(tmp_path / "store")
    elsewhere = git_init(tmp_path / "elsewhere")
    init(["work"], elsewhere, "other")
    (code / "docs").mkdir()
    (code / "docs" / "work").symlink_to(elsewhere / "docs" / "work")
    before = manifest(code)
    with pytest.raises(ValueError, match="non-pristine"):
        init(["work"], code, "demo", work_path=store / "work")
    assert manifest(code) == before
    assert not (code / SENTINEL).exists()


def test_init_reports_a_malformed_config_rather_than_raising_through_it(tmp_path):
    """`init` reads the config before `write_sentinel` validates it.

    That order is what lets every refusal land before the first write, and it
    moved the mapping check out from under this read — a YAML list came back as
    an `AttributeError` from `.get`, and a list-valued `work.path` as a
    `TypeError` from `Path()`. Both are user-facing config mistakes and belong
    in the `ValueError` channel the CLI already renders.
    """
    for text, message in (( "- a\n- b\n", "must be a mapping"),
                          ("id: x\nwork:\n  path: [bad]\n", "must be a string")):
        code = git_init(tmp_path / hashlib.sha256(text.encode()).hexdigest()[:8])
        (code / SENTINEL).write_text(text, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            init(["work"], code, "demo")


def test_init_accepts_a_work_path_whose_directories_do_not_exist_yet(tmp_path):
    """Why the check was written late, and what the early one must not break.

    `git_root` shells out to `git -C <path>`, which fails on a path that does not
    exist — so an early check that probed the target itself would refuse a
    perfectly good `--work-path <repo>/new/nested/dir`. It has to resolve to the
    nearest *existing* ancestor.
    """
    code = git_init(tmp_path / "code")
    store = git_init(tmp_path / "store")
    target = store / "new" / "nested" / "work"
    init(["work"], code, "demo", work_path=target)
    assert (target / "backlog" / ".gitkeep").is_file()


# ── The generic handler, on a `cmd` that is a string ─────────────────────────


def test_a_string_valued_git_command_is_rendered_as_one_command(
    tmp_path, monkeypatch, capsys
):
    """`CalledProcessError.cmd` is a sequence *or* a string (stdlib contract).

    Given a string, `shlex.join(str(a) for a in cmd)` iterates characters and
    prints `g i t ' ' s t a t u s`. No shipped raiser passes a string today, but
    the handler's entire justification is that it carries no assumptions about
    who raised.
    """
    root = repo(tmp_path)
    FsWorkStore.open(root).create("Task", created="2026-01-01")
    monkeypatch.chdir(root)

    def boom(*args, **kwargs):
        raise subprocess.CalledProcessError(128, "git status")

    monkeypatch.setattr("tcw.store.fs.git_stage", boom)
    assert main(["work", "new", "T"]) != 0
    err = capsys.readouterr().err
    assert err == "tcw: git command failed (exit 128): git status\n", err

