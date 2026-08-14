"""`tcw work stage` — legality, stream discipline, and writing nothing."""

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import (
    STAGE_IDS, STAGE_STATUSES, WORK_STATUSES, WorkStore,
)
from tcw.store.fs import FsWorkStore, init


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


def _configure(root: Path, lifecycle: dict) -> None:
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["lifecycle"] = lifecycle
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def _cli(root: Path, *args: str):
    return subprocess.run(["tcw", "work", "stage", *args], cwd=str(root),
                          capture_output=True, text=True)


def _manifest(folder: Path) -> dict:
    """Names, sizes, and content hashes — the adapter-level "wrote nothing"."""
    return {str(p.relative_to(folder)): (p.stat().st_size,
                                         hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(folder.rglob("*")) if p.is_file()}


# ── the legality table ───────────────────────────────────────────────────────


def test_the_table_covers_every_stage_and_only_real_statuses():
    assert set(STAGE_STATUSES) == set(STAGE_IDS)
    for stage, statuses in STAGE_STATUSES.items():
        assert set(statuses) <= set(WORK_STATUSES), stage


def test_each_row_is_what_the_lifecycle_contract_says():
    """Written out rather than derived, because the two non-obvious rows are
    exactly where a table written from the happy path goes wrong."""
    assert STAGE_STATUSES == {
        "inbox": (),
        "request": ("backlog",),
        "spec": ("backlog",),
        "plan": ("backlog",),
        "implement": ("active",),
        # `complete` moves from `review | active`, so an item can be verified
        # without ever having been submitted.
        "verify": ("active", "review"),
        # Not `discarded`: `completed` means shipped and `discarded` means closed
        # without shipping, and a post-mortem on work nobody did is not this.
        "postmortem": ("review", "completed"),
    }


@pytest.fixture
def one_of_each(tmp_path):
    """An item in every status, in one node, so the matrix can be swept."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    slugs = {}
    for status in WORK_STATUSES:
        item = st.create(f"Item {status}", body="req\n")
        if status in ("active", "review", "completed", "discarded"):
            st.start(item.slug)
        if status in ("review",):
            st.submit(item.slug)
        if status == "completed":
            st.complete(item.slug, "done", dod_ack=list(st.dod_checklist()),
                        force=True)
        if status == "discarded":
            st.complete(item.slug, "wontfix", dod_ack=[], force=True)
        slugs[status] = item.slug
    return root, slugs


def test_every_illegal_pair_is_rejected_and_every_legal_one_accepted(one_of_each):
    """The whole Cartesian product, driven from the table.

    Special-casing the two illegal pairs someone thought to test is precisely
    what this closes — and if it ever finds a combination users need, the table
    is wrong rather than the test.
    """
    root, slugs = one_of_each
    for stage in STAGE_IDS:
        for status in WORK_STATUSES:
            r = _cli(root, stage, slugs[status])
            legal = status in STAGE_STATUSES[stage]
            assert (r.returncode == 0) is legal, (
                f"{stage} in {status}: expected "
                f"{'accept' if legal else 'reject'}, got rc={r.returncode} "
                f"{r.stderr}")
            if not legal:
                assert r.stdout == ""


def test_postmortem_is_rejected_on_a_discarded_item(one_of_each):
    """Named separately because it is the row the first draft of the spec got
    wrong, and a matrix test that itself derives from the table would agree with
    a wrong table."""
    root, slugs = one_of_each
    r = _cli(root, "postmortem", slugs["discarded"])
    assert r.returncode == 1
    assert "not legal" in r.stderr


def test_inbox_is_rejected_with_its_reason(one_of_each):
    root, slugs = one_of_each
    r = _cli(root, "inbox", slugs["backlog"])
    assert r.returncode == 1
    assert r.stdout == ""
    assert "runs before an item exists" in r.stderr


def test_an_unknown_stage_names_the_legal_ids(one_of_each):
    root, slugs = one_of_each
    r = _cli(root, "speck", slugs["backlog"])
    assert r.returncode == 1 and r.stdout == ""
    assert "unknown stage 'speck'" in r.stderr and "spec" in r.stderr


def test_a_transition_id_is_not_a_stage(one_of_each):
    root, slugs = one_of_each
    assert _cli(root, "complete", slugs["backlog"]).returncode == 1


# ── streams ──────────────────────────────────────────────────────────────────


def test_stdout_is_only_prompt_text(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": "printf 'check-out'; printf 'check-err' >&2"}],
        "prompt": [{"blob": "THE PROMPT"}]}}})

    r = _cli(root, "spec", item.slug)
    assert r.returncode == 0
    assert r.stdout == "THE PROMPT\n"
    assert "check-out" in r.stderr and "check-err" in r.stderr


def test_a_failing_check_resolves_nothing(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    sentinel = (tmp_path / "GENERATED").resolve()
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": "exit 7"}],
        "prompt": [{"generate": f"touch {sentinel}; printf 'x'"}]}}})

    r = _cli(root, "spec", item.slug)
    assert r.returncode == 1
    assert r.stdout == ""
    assert "exit 7" in r.stderr and "nothing resolved" in r.stderr
    assert not sentinel.exists()


def test_a_late_generator_failure_leaves_stdout_empty(tmp_path):
    """The text is buffered and emitted once, after everything that can fail has
    succeeded — so an earlier binding that resolved fine still prints nothing."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {"prompt": [
        {"blob": "resolved first"},
        {"generate": "exit 5"}]}}})

    r = _cli(root, "spec", item.slug)
    assert r.returncode == 1
    assert r.stdout == ""
    assert "resolved first" not in r.stdout


# ── writing nothing ──────────────────────────────────────────────────────────


def test_no_mutating_store_method_is_called(tmp_path, monkeypatch):
    """The portable half: a Jira-backed adapter has no item folder, so the
    property is "no mutator ran", not "no file changed"."""
    from tcw.cli import main
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {"prompt": [{"blob": "text"}]}}})

    mutators = [name for name in dir(WorkStore)
                if name.startswith(("create", "update", "write", "delete",
                                    "set_", "start", "submit", "rework",
                                    "complete", "drop", "inbox_accept"))
                and callable(getattr(WorkStore, name, None))]
    assert mutators, "found no mutating methods to guard — the guard is vacuous"
    called = []
    for name in mutators:
        original = getattr(FsWorkStore, name, None)
        if original is None:
            continue
        monkeypatch.setattr(FsWorkStore, name,
                            (lambda n: lambda *a, **k: called.append(n))(name))

    monkeypatch.chdir(root)
    assert main(["work", "stage", "spec", item.slug]) == 0
    assert called == []


def test_the_item_folder_is_byte_identical_after_every_legal_stage(tmp_path):
    """The adapter half: catches anything that writes without going through the
    store at all."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    st.write_artifact(item.slug, "spec", "# Spec\n")
    _configure(root, {"stages": {sid: {"prompt": [{"blob": f"{sid} text"}]}
                                 for sid in STAGE_IDS if sid != "inbox"}})

    folder = st.path(item.slug)
    for stage in STAGE_IDS:
        if "backlog" not in STAGE_STATUSES[stage]:
            continue
        before = _manifest(folder)
        assert _cli(root, stage, item.slug).returncode == 0
        assert _manifest(folder) == before, f"`stage {stage}` wrote something"


# ── --no-exec ────────────────────────────────────────────────────────────────


def test_no_exec_runs_nothing_and_names_what_it_skipped(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    check_sentinel = (tmp_path / "CHECK").resolve()
    gen_sentinel = (tmp_path / "GEN").resolve()
    (root / "guide.md").write_text("from a file\n")
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": f"touch {check_sentinel}"}],
        "prompt": [{"blob": "static text"},
                   {"file": "guide.md"},
                   {"generate": f"touch {gen_sentinel}; printf 'gen'"}]}}})

    r = _cli(root, "spec", item.slug, "--no-exec")
    assert r.returncode == 0
    assert not check_sentinel.exists() and not gen_sentinel.exists()
    # Still a dry *run*: what resolves without executing is printed.
    assert r.stdout == "static text\n"
    assert "from a file" not in r.stdout          # a file read is observable too
    assert "gen" not in r.stdout
    assert "pre check would run" in r.stderr
    assert f"touch {gen_sentinel}" in r.stderr
    assert "prompt file" in r.stderr


def test_without_no_exec_the_same_stage_runs_everything(tmp_path):
    """The other side of the previous test: if this failed the same way, that
    one would prove nothing."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Thing", body="req\n")
    check_sentinel = (tmp_path / "CHECK").resolve()
    (root / "guide.md").write_text("from a file\n")
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": f"touch {check_sentinel}"}],
        "prompt": [{"blob": "static text"}, {"file": "guide.md"},
                   {"generate": "printf 'gen'"}]}}})

    r = _cli(root, "spec", item.slug)
    assert r.returncode == 0
    assert check_sentinel.exists()
    assert r.stdout == "static text\n\nfrom a file\n\ngen\n"


def test_no_exec_reports_a_condition_that_did_not_match(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    item = st.create("Thing", body="req\n")
    _configure(root, {"stages": {"spec": {"prompt": [
        {"blob": "for bugs", "when": {"tags": ["bug"]}},
        {"blob": "for all"}]}}})

    r = _cli(root, "spec", item.slug, "--no-exec")
    assert "skipped (condition)" in r.stderr
    assert r.stdout == "for all\n"
