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


