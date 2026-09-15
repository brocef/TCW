"""Lifecycle synchronization: a bound item's ticket follows the item.

`start` claims; `submit`, `rework`, `complete` and discarding move the ticket to the
tracker status configured for the item's new status; what did not reach the tracker
is recorded in the binding and retried by `tcw work tracker sync`. The local move is
never undone or blocked.

Every node is built by `make_node`, whose `statuses` argument has no default: which
statuses are mapped is the axis delivery branches on.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
from pathlib import Path

import jsonschema
import pytest
import yaml

from tcw.store.base import classify_binding
from tcw.store.fs import FsWorkStore, init
from tcw.tracker.intake import binding_document, unlink_document, with_sync_record
from tcw.work.projection import WORK_ITEM_SCHEMA
from tracker_fake import BASE_URL, GLOBAL, SYNC, FakeJira, install_sites

SENTINEL = "sentinel-token-do-not-print"
A, B = "acct-a", "acct-b"
KEY, TICKET_ID = "SYNC-1", "20001"
STATUSES = {"active": "In Progress", "review": "In Review", "completed": "Done",
            "discarded": "Won't Do"}
RECORD = {"state": "pending", "move": "submit", "since": "In Progress", "claim": "done",
          "reason": "the tracker could not be reached", "at": "2026-09-14T10:00:00Z"}


def document(**overrides) -> str:
    values = dict(provider="jira-cloud", project="alpha", part="default",
                  ticket_id=TICKET_ID, ticket_key=KEY,
                  ticket_url=f"{BASE_URL}/browse/{KEY}", bound="2026-09-14", unlinked=[])
    values.update(overrides)
    return binding_document(**values)


# ── the record in the binding ────────────────────────────────────────────────


def test_a_record_is_carried_on_the_binding():
    bound = classify_binding(yaml.safe_load(with_sync_record(document(), RECORD)))
    assert bound.sync == RECORD and bound.ticket_key == KEY


@pytest.mark.parametrize("sync", [5, {**RECORD, "state": "late"},
                                  {**RECORD, "move": "wander"},
                                  {**RECORD, "claim": "maybe"},
                                  {k: v for k, v in RECORD.items() if k != "reason"},
                                  {**RECORD, "at": None}],
                         ids=["not-mapping", "state", "move", "claim", "missing", "null"])
def test_an_unusable_record_is_a_problem_and_the_binding_stays_bound(sync):
    data = yaml.safe_load(document())
    data["sync"] = sync
    bound = classify_binding(data)
    assert bound.ticket_key == KEY
    assert set(bound.sync) == {"problem"}


def test_setting_and_removing_a_record_keeps_every_other_key_in_place():
    original = document()
    with_record = with_sync_record(original, RECORD)
    assert yaml.safe_load(with_record)["sync"] == RECORD
    assert with_sync_record(with_record, None) == original


def test_unlink_takes_the_record_with_the_binding():
    content = unlink_document(with_sync_record(document(), RECORD),
                              reason="wrong ticket", today="2026-09-14")
    data = yaml.safe_load(content)
    assert "sync" not in data
    assert classify_binding(data).__class__.__name__ == "Unbound"


# ── shared fixtures for the delivery tests ───────────────────────────────────


def make_node(tmp_path: Path, *, statuses: dict | None,
              name: str = "alpha", email_env: str = "TCW_A_EMAIL",
              tracker: bool = True, base_url: str = BASE_URL) -> Path:
    """A git-backed node. `statuses` has no default; `None` leaves the block out."""
    root = tmp_path / name
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "a@example.test"],
                   check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "a"], check=True)
    init(["work"], root, project_id=name)
    config = yaml.safe_load((root / "tcw-config.yaml").read_text(encoding="utf-8"))
    if tracker:
        block = {
            "provider": "jira-cloud", "base-url": base_url,
            "candidate-query": "assignee = currentUser()",
            "credentials": {"email-env": email_env, "token-env": "TCW_PROBE_TOKEN"},
            "transitions": {"claim": "Start Progress"},
        }
        if statuses is not None:
            block["statuses"] = statuses
        config.setdefault("work", {})["tracker"] = block
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                          encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "init"], check=True)
    return root


def cli(root: Path, *argv: str) -> tuple[int, str, str]:
    from tcw.cli import main
    previous = os.getcwd()
    out, err = io.StringIO(), io.StringIO()
    os.chdir(root)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(list(argv))
            except SystemExit as exit_:
                code = exit_.code or 0
    finally:
        os.chdir(previous)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_B_EMAIL", "b@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake = FakeJira(workflow=SYNC)
    fake.account("a@example.test", A, "Alice")
    fake.account("b@example.test", B, "Bob")
    fake.ticket(id=TICKET_ID, key=KEY, summary="A ready ticket")
    return fake.install(monkeypatch)


def bound_item(root: Path, title: str = "Bound item", *, part: str = "default",
               ticket: str = KEY) -> str:
    st = FsWorkStore.open(root)
    slug = st.create(title).slug
    code, _out, err = cli(root, "work", "tracker", "link", slug, ticket, "--part", part)
    assert code == 0, err
    return slug


def record(root: Path, slug: str) -> dict | None:
    return FsWorkStore.open(root).get(slug).tracker["sync"]


def binding_text(root: Path, slug: str) -> str:
    return FsWorkStore.open(root).read_sidecar(slug, "tracker.yaml").content


def status(root: Path, slug: str) -> str:
    return FsWorkStore.open(root).get(slug).status


def test_the_json_document_validates_with_a_record_a_problem_and_none(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    for sync in (None, RECORD, 5):
        content = yaml.safe_load(binding_text(root, slug))
        content.pop("sync", None)
        if sync is not None:
            content["sync"] = sync
        (st.path(slug) / "tracker.yaml").write_text(yaml.safe_dump(content),
                                                    encoding="utf-8")
        code, out, err = cli(root, "work", "show", slug, "--json")
        assert code == 0, err
        import json
        jsonschema.validate(json.loads(out), WORK_ITEM_SCHEMA)


# ── a binding from another site ──────────────────────────────────────────────


SITE_A, SITE_B = "https://a.invalid", "https://b.invalid"


def set_base_url(root: Path, url: str) -> None:
    path = root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["work"]["tracker"]["base-url"] = url
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


@pytest.fixture()
def two_sites(monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    old, new = FakeJira(workflow=SYNC, site=SITE_A), FakeJira(workflow=SYNC, site=SITE_B)
    for fake_ in (old, new):
        fake_.account("a@example.test", A, "Alice")
    old.ticket(id="10052", key="OLD-6", summary="On the old site")
    new.ticket(id="10052", key="NEW-9", summary="On the new site", assignee=A)
    install_sites(monkeypatch, old, new)
    return old, new


def test_same_site_compares_scheme_host_and_browse_path():
    from tcw.tracker.intake import same_site
    assert same_site("https://A.invalid/browse/X-1", "https://a.invalid")
    assert same_site("https://a.invalid/jira/browse/X-1", "https://a.invalid/jira")
    assert not same_site("https://b.invalid/browse/X-1", "https://a.invalid")
    assert not same_site("http://a.invalid/browse/X-1", "https://a.invalid")
    assert not same_site("https://a.invalid/other/X-1", "https://a.invalid")
    assert not same_site("", "https://a.invalid")
    assert not same_site("browse/X-1", "https://a.invalid")


def test_import_refuses_a_same_id_ticket_from_another_site(tmp_path, two_sites):
    old, new = two_sites
    root = make_node(tmp_path, statuses=None, base_url=SITE_A)
    code, out, err = cli(root, "work", "tracker", "import", "OLD-6")
    assert code == 0, err
    old_slug = out.strip()
    set_base_url(root, SITE_B)
    code, out, err = cli(root, "work", "tracker", "import", "NEW-9")
    assert code == 1
    assert old_slug in err and SITE_B in err
    assert "already bound" not in err
    assert new.writes() == []
