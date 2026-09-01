"""Publishing a provisioned work store's writes to the repository it came from.

**No test here reaches the network.** Where a remote is needed it is a real bare
repository in `tmp_path` — Git does not care that the URL is a local path, and
the code under test never learns the difference.

The organising idea is the spec's section A: *which* stores publish. Three of the
four answers are "not this one", and those three are the safety story — a store
that consulted its Git `origin` rather than the declaration would make TCW push
the user's own project on every status change. So the tests that assert **no**
network are the load-bearing ones, and they are parametrized over every
non-publishing rule rather than written once for the convenient case.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store import fs
from tcw.store.fs import FsWorkStore, init


def _repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    for key, value in (("user.email", "test@example.com"), ("user.name", "Test"),
                       ("commit.gpgsign", "false")):
        subprocess.run(["git", "-C", str(path), "config", key, value], check=True)
    return path


def _remote_with_store(tmp_path: Path, inner: str = "stores/corelib") -> Path:
    """A repository holding a real work store, used as the declared remote."""
    remote = _repo(tmp_path / "orchestrator")
    for name in ("inbox", "backlog", "active", "review", "completed", "discarded"):
        (remote / inner / name).mkdir(parents=True)
        (remote / inner / name / ".gitkeep").write_text("")
    subprocess.run(["git", "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(remote), "commit", "-qm", "seed"], check=True)
    return remote


def _bare(tmp_path: Path, source: Path) -> Path:
    bare = tmp_path / "orchestrator.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(source), str(bare)], check=True)
    return bare


def _write_config(node_root: Path, **work) -> None:
    path = node_root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text()) or {}
    config.setdefault("work", {}).update(work)
    path.write_text(yaml.safe_dump(config, sort_keys=False))


@pytest.fixture(autouse=True)
def _cache_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


# ── the four answers to "does this store publish?" ──────────────────────────
#
# Every axis the resolution ladder branches on is an explicit argument here.
# A fixture default is always whichever value makes setup easiest, and that is
# how the store-provisioning epic put three defects in cells no test reached.

def _node(tmp_path: Path, *, local_store: bool, declaration: bool,
          provisioned: bool, publish: bool | str | None = None) -> Path:
    """A node built to land on one specific rung of the spec's section A."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    subprocess.run(["git", "-C", str(code), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(code), "commit", "-qm", "init"], check=True)

    settings: dict = {}
    if local_store:
        here = _repo(tmp_path / "local-store")
        for name in ("inbox", "backlog", "active", "review", "completed", "discarded"):
            (here / name).mkdir(parents=True)
            (here / name / ".gitkeep").write_text("")
        subprocess.run(["git", "-C", str(here), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(here), "commit", "-qm", "seed"], check=True)
        settings["path"] = str(here)
    else:
        (code / "docs" / "work").rename(code / "docs" / "work-elsewhere")
        settings["path"] = str(tmp_path / "absent")

    if declaration:
        remote = _bare(tmp_path, _remote_with_store(tmp_path))
        settings["repository"] = {"url": str(remote), "path": "stores/corelib",
                                  "checkout": str(tmp_path / "checkout")}
    if publish is not None:
        settings["publish-transitions"] = publish
    _write_config(code, **settings)

    # Provisioning is the caller's to do, after chdir — it is a CLI action and
    # belongs in the test that needs it, not hidden in a fixture.
    return code


def test_a_provisioned_store_publishes(tmp_path, monkeypatch):
    """Section A rule 1 — the case the initiative exists for."""
    code = _node(tmp_path, local_store=False, declaration=True, provisioned=True)
    monkeypatch.chdir(code)
    assert main(["provision"]) == 0

    assert FsWorkStore.open(code).publishes is True


@pytest.mark.parametrize("kind, kwargs", [
    ("rule-1-declared-but-unused",
     dict(local_store=True, declaration=True, provisioned=False)),
    ("rule-4-no-declaration",
     dict(local_store=True, declaration=False, provisioned=False)),
    ("disabled-by-config",
     dict(local_store=False, declaration=True, provisioned=True, publish=False)),
])
def test_a_store_that_must_not_publish_does_not(tmp_path, monkeypatch, kind, kwargs):
    """Section A rules 2, 3 and 4 — the safety story, in one parametrized test.

    Rule 3 is the one that matters most and is easiest to get wrong: such a
    store's Git repository usually *does* have an `origin`, because it is the
    user's own project. A `publishes` that consulted `origin` rather than the
    declaration would make every status change push the user's repository.
    """
    code = _node(tmp_path, **kwargs)
    monkeypatch.chdir(code)
    if kwargs.get("declaration") and kwargs.get("provisioned"):
        assert main(["provision"]) == 0

    assert FsWorkStore.open(code).publishes is False, kind


# ── the property task 6 must not break ──────────────────────────────────────
#
# These pass trivially today: nothing publishes yet, so nothing can perform a
# network operation. That is deliberate and they are not redundant. They are the
# definition of "adding publication broke nothing", written before the code that
# could break them — written afterwards they would be shaped to fit whatever
# that code happened to do.

def _assert_no_network(calls: list[list[str]]) -> None:
    """One named assertion for criterion 6, so a sibling test that skips it is
    visible in the diff rather than left to review."""
    assert calls == [], f"expected no network operation, got: {calls}"


def _record_network(monkeypatch) -> list[list[str]]:
    """Intercept the adapter's own Git runner — the single point every clone,
    fetch and push routes through. Asserted **empty**, not merely 'no push': a
    test that allows some network is one that cannot notice a new call site."""
    calls: list[list[str]] = []

    def spy(self, argv, **kwargs):
        calls.append(list(argv))
        raise AssertionError(f"unexpected network operation: {argv}")

    monkeypatch.setattr(fs.FsStoreProvisioner, "_run", spy)
    return calls


def _slug_of(title: str) -> str:
    """`tcw work new` slugs a title with today's date. Derived rather than read
    back, so these tests do not depend on a listing API to say what they mean."""
    from datetime import date
    return f"{date.today().isoformat()}-{title.lower().replace(' ', '-')}"


NON_PUBLISHING = [
    ("rule-1-declared-but-unused",
     dict(local_store=True, declaration=True, provisioned=False)),
    ("rule-4-no-declaration",
     dict(local_store=True, declaration=False, provisioned=False)),
    ("disabled-by-config",
     dict(local_store=True, declaration=True, provisioned=False, publish=False)),
]


# Every command that moves an item, not the one that was convenient to write.
# `start` does not route through `_effect_transition` — it has its own claim
# path — so a refresh hooked into `_effect_transition` alone leaves `start`
# unrefreshed. That was found by accident here; parametrizing is what stops the
# next transition path from being found the same way.
TRANSITIONS = ["start", "submit", "complete"]


def _drive_to(slug: str, transition: str) -> int:
    if transition == "start":
        return main(["work", "start", slug])
    assert main(["work", "start", slug]) == 0
    if transition == "submit":
        return main(["work", "submit", slug])
    return main(["work", "complete", slug, "--resolution", "done", "--confirm"])


@pytest.mark.parametrize("transition", TRANSITIONS)
@pytest.mark.parametrize("kind, kwargs", NON_PUBLISHING)
def test_no_transition_on_a_non_publishing_store_touches_the_network_anywhere(
        tmp_path, monkeypatch, kind, kwargs, transition):
    """Criterion 6, over every non-publishing rule AND every transition."""
    code = _node(tmp_path, **kwargs)
    monkeypatch.chdir(code)
    assert main(["work", "new", "A thing to move"]) == 0
    slug = _slug_of("A thing to move")

    calls = _record_network(monkeypatch)
    assert _drive_to(slug, transition) == 0

    _assert_no_network(calls)


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_every_transition_on_a_publishing_store_refreshes_first(
        tmp_path, monkeypatch, transition):
    """The other half of the same property: a transition path that forgets to
    refresh is a path that silently stops publishing."""
    code, _bare_remote, slug = _publishing_node(tmp_path, monkeypatch)
    seen: list[str] = []
    real = fs.FsWorkStore.refresh
    monkeypatch.setattr(fs.FsWorkStore, "refresh",
                        lambda self: (seen.append("refreshed"), real(self))[1])

    assert _drive_to(slug, transition) == 0

    assert seen, f"`tcw work {transition}` did not refresh"


@pytest.mark.parametrize("kind, kwargs", NON_PUBLISHING)
def test_no_transition_on_a_non_publishing_store_touches_the_network(
        tmp_path, monkeypatch, kind, kwargs):
    """Criterion 6, over every rule in section A that must not publish.

    Parametrized over all three rather than written for one, because the spec's
    Coverage table marks a column of cells `n/a — via 7`, and those cells are
    load bearing only if this test really does cover the rules they defer to.
    One rule covered and three assumed is how the previous two items in this
    initiative shipped the same defect four times.
    """
    code = _node(tmp_path, **kwargs)
    monkeypatch.chdir(code)
    assert main(["work", "new", "A thing to move"]) == 0
    slug = _slug_of("A thing to move")

    calls = _record_network(monkeypatch)
    assert main(["work", "start", slug]) == 0

    _assert_no_network(calls)


@pytest.mark.parametrize("kind, kwargs", NON_PUBLISHING)
def test_a_non_publishing_store_is_unchanged(tmp_path, monkeypatch, kind, kwargs):
    """Criterion 7. Not just 'no network' but 'nothing new at all': the
    transition still succeeds, still moves the item, and still commits."""
    code = _node(tmp_path, **kwargs)
    monkeypatch.chdir(code)
    assert main(["work", "new", "A thing to move"]) == 0
    slug = _slug_of("A thing to move")

    assert main(["work", "start", slug]) == 0

    store = FsWorkStore.open(code)
    assert store.publishes is False, kind
    assert store.get(slug).status == "active"
    head = subprocess.run(["git", "-C", str(store.store_git_root), "log", "-1",
                           "--format=%s"], capture_output=True, text=True)
    assert slug in head.stdout, head.stdout




# ── step 1: refresh, before anything moves ──────────────────────────────────

def _publishing_node(tmp_path, monkeypatch) -> tuple[Path, Path, str]:
    """A provisioned store with one backlog item. Returns (node, bare remote,
    slug)."""
    source = _remote_with_store(tmp_path)
    bare = _bare(tmp_path, source)
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    subprocess.run(["git", "-C", str(code), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(code), "commit", "-qm", "init"], check=True)
    (code / "docs" / "work").rename(code / "docs" / "work-elsewhere")
    _write_config(code, path=str(tmp_path / "absent"),
                  repository={"url": str(bare), "path": "stores/corelib",
                              "checkout": str(tmp_path / "checkout")})
    monkeypatch.chdir(code)
    assert main(["provision"]) == 0
    assert main(["work", "new", "A thing to move"]) == 0
    return code, bare, _slug_of("A thing to move")


def _head(node_root: Path) -> str:
    store = FsWorkStore.open(node_root)
    return subprocess.run(["git", "-C", str(store.store_git_root), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def _assert_nothing_moved(node_root: Path, slug: str, status: str,
                          head_before: str) -> None:
    """One named assertion for criterion 3: the spec says *same status, same
    folder, no commit*, so all three are checked in one place and no sibling
    test can quietly check a subset.

    "No commit" is the store repository's HEAD, not a clean working tree —
    `tcw work new` stages an item without committing it, so a pristine-tree
    assertion would be checking someone else's behaviour and would fail for a
    reason that has nothing to do with this criterion.
    """
    store = FsWorkStore.open(node_root)
    item = store.get(slug)
    assert item is not None and item.status == status, item
    assert (store.root / status / slug).is_dir(), f"{slug} is not in {status}/"
    assert _head(node_root) == head_before, "the refused transition committed"


def test_the_refresh_precedes_any_filesystem_change(tmp_path, monkeypatch):
    """Criterion 2, asserted as an ordering rather than as 'a refresh happened'.

    The store is asked to move an item; the refresh is made to observe whether
    the item has already moved. If it has, the refresh is not first.
    """
    code, _bare_remote, slug = _publishing_node(tmp_path, monkeypatch)
    store_root = FsWorkStore.open(code).root
    seen: list[bool] = []
    real = fs.FsWorkStore.refresh

    def watching(self):
        seen.append((self.root / "active" / slug).exists())
        return real(self)

    monkeypatch.setattr(fs.FsWorkStore, "refresh", watching)
    assert main(["work", "start", slug]) == 0

    assert seen == [False], "refresh ran after the item had already moved"
    assert (store_root / "active" / slug).is_dir()


def test_a_refused_refresh_leaves_the_item_untouched(tmp_path, monkeypatch):
    """Criterion 3. Nothing has moved when step 1 fails, so there is no partial
    state to explain — the transition simply refuses."""
    code, _bare_remote, slug = _publishing_node(tmp_path, monkeypatch)

    def broken(self):
        raise ValueError("the declared remote is unreachable")

    head = _head(code)
    monkeypatch.setattr(fs.FsWorkStore, "refresh", broken)
    assert main(["work", "start", slug]) == 1

    _assert_nothing_moved(code, slug, "backlog", head)


def test_divergence_is_refused_not_merged(tmp_path, monkeypatch, capsys):
    """Criterion 5. The remote moves incompatibly; the refresh is fast-forward
    only, so it refuses at step 1 rather than creating a merge commit inside
    somebody's work store."""
    code, bare, slug = _publishing_node(tmp_path, monkeypatch)
    checkout = tmp_path / "checkout"

    # Someone else advances the remote…
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(bare), str(other)], check=True)
    for key, value in (("user.email", "o@o"), ("user.name", "O")):
        subprocess.run(["git", "-C", str(other), "config", key, value], check=True)
    (other / "stores" / "corelib" / "inbox" / "theirs.md").write_text("theirs\n")
    subprocess.run(["git", "-C", str(other), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(other), "commit", "-qm", "theirs"], check=True)
    subprocess.run(["git", "-C", str(other), "push", "-q", "origin", "main"], check=True)

    # …while this checkout commits something else on top of the old tip.
    (checkout / "stores" / "corelib" / "inbox" / "ours.md").write_text("ours\n")
    subprocess.run(["git", "-C", str(checkout), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(checkout), "commit", "-qm", "ours"], check=True)

    head = _head(code)
    assert main(["work", "start", slug]) == 1

    _assert_nothing_moved(code, slug, "backlog", head)
    log = subprocess.run(["git", "-C", str(checkout), "log", "--merges",
                          "--oneline"], capture_output=True, text=True)
    assert log.stdout.strip() == "", f"a merge commit was created: {log.stdout}"


# ── step 4: publish, after the commit ───────────────────────────────────────

def _remote_log(bare: Path) -> str:
    return subprocess.run(["git", "-C", str(bare), "log", "--oneline"],
                          capture_output=True, text=True).stdout


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_a_transition_reaches_the_remote(tmp_path, monkeypatch, transition):
    """Criterion 1, over every transition. The check is not "a push happened"
    but the thing the user actually cares about: provisioning the same
    declaration somewhere else afterwards shows the item where it now is."""
    code, bare, slug = _publishing_node(tmp_path, monkeypatch)

    assert _drive_to(slug, transition) == 0

    elsewhere = tmp_path / "second"
    subprocess.run(["git", "clone", "-q", str(bare), str(elsewhere)], check=True)
    expected = {"start": "active", "submit": "review", "complete": "completed"}[transition]
    assert (elsewhere / "stores" / "corelib" / expected / slug).is_dir(), \
        _remote_log(bare)


def test_a_failed_publish_says_what_landed(tmp_path, monkeypatch, capsys):
    """Criterion 4. The item moved and committed locally; only the push failed.
    The message has to say exactly that, because "your work is on this machine
    and nowhere else" is a state this CLI has never had to describe."""
    code, bare, slug = _publishing_node(tmp_path, monkeypatch)
    head_before = _head(code)

    def broken(self):
        raise ValueError("could not reach the declared remote")

    monkeypatch.setattr(fs.FsWorkStore, "publish", broken)
    assert main(["work", "start", slug]) == 1

    store = FsWorkStore.open(code)
    assert store.get(slug).status == "active", "the transition was rolled back"
    assert _head(code) != head_before, "the transition was not committed"
    err = capsys.readouterr().err
    assert slug in err and "active" in err, err
    assert "not" in err.lower(), err


def test_a_push_verifies_the_remote_before_contacting_it(tmp_path, monkeypatch):
    """Criterion 8. A `checkout` is an arbitrary user-chosen directory, so it can
    hold an unrelated repository — the same reason `_require_declared_checkout`
    exists for fetching. Pushing into the wrong one would be worse."""
    code, bare, slug = _publishing_node(tmp_path, monkeypatch)
    checkout = tmp_path / "checkout"
    stranger = _repo(tmp_path / "stranger")
    subprocess.run(["git", "-C", str(checkout), "remote", "set-url", "origin",
                    str(stranger)], check=True)

    assert main(["work", "start", slug]) == 1

    assert _remote_log(stranger).strip() == "", "pushed to an unexpected remote"


def test_publication_can_be_switched_off(tmp_path, monkeypatch):
    """Criterion 9, including the half that gets forgotten: a non-boolean reads
    as the default rather than as false."""
    code, bare, slug = _publishing_node(tmp_path, monkeypatch)
    before = _remote_log(bare)

    _write_config(code, **{"publish-transitions": False})
    calls = _record_network(monkeypatch)
    assert main(["work", "start", slug]) == 0
    _assert_no_network(calls)
    assert _remote_log(bare) == before

    _write_config(code, **{"publish-transitions": "yes please"})
    assert FsWorkStore.open(code).publishes is True, \
        "a non-boolean must read as the default, not as false"


def test_nothing_is_published_when_nothing_is_committed(tmp_path, monkeypatch):
    """A cell the spec's Coverage tables did not enumerate, found while wiring
    step 4: `work.auto-commit-transitions: false` leaves the move uncommitted,
    so a push would contact the remote and publish nothing. The two switches are
    independent in config and must not be independent in effect."""
    code, bare, slug = _publishing_node(tmp_path, monkeypatch)
    before = _remote_log(bare)
    _write_config(code, **{"auto-commit-transitions": False})

    assert main(["work", "start", slug]) == 0

    assert _remote_log(bare) == before, "pushed without a commit to publish"
