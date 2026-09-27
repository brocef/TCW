"""Recovering an interrupted claim from the CLI and the web app
(spec: 2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app).

An interrupted claim is made the way a dead process leaves one: the item's folder
moved into `.claiming/<slug>-<32 hex>` and never published."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsWorkStore
from test_lifecycle_hooks import configure, node


def interrupt(root: Path, slug: str) -> Path:
    st = FsWorkStore.open(root)
    private = st.root / ".claiming" / f"{slug}-{'1a' * 16}"
    private.parent.mkdir(exist_ok=True)
    st.path(slug).replace(private)
    return private


def tagged_item(root: Path, tag: str = "bug") -> str:
    st = FsWorkStore.open(root)
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["tags"] = [tag]
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    slug = st.create("Interrupted", created="2026-01-01").slug
    st.set_field(slug, "tags", [tag])
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "item"], check=True)
    return slug


# ── the store lists interrupted claims ───────────────────────────────────────

def test_an_interrupted_claim_is_listed_as_it_was(tmp_path):
    root = node(tmp_path)
    slug = tagged_item(root)
    interrupt(root, slug)
    [claim] = FsWorkStore.open(root).interrupted_claims()
    assert (claim.slug, claim.status, claim.tags) == (slug, "backlog", ["bug"])


def test_nothing_is_listed_without_one(tmp_path):
    root = node(tmp_path)
    tagged_item(root)
    assert FsWorkStore.open(root).interrupted_claims() == []


# ── the CLI's --take-over reaches the store ──────────────────────────────────

def test_take_over_recovers_an_interrupted_claim(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = tagged_item(root)
    private = interrupt(root, slug)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--take-over", "--owner", "me"]) == 0
    item = FsWorkStore.open(root).get(slug)
    assert (item.status, item.owner) == ("active", "me")
    assert not private.exists()
    assert "interrupted claim" not in capsys.readouterr().err


def test_a_refusing_pre_hook_matched_on_the_items_tag_still_refuses(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = tagged_item(root)
    configure(root, {"transitions": {"start": {"pre": [
        {"command": "false", "when": {"tags": ["bug"]}}]}}})
    private = interrupt(root, slug)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--take-over", "--owner", "me"]) == 1
    assert "not started" in capsys.readouterr().err
    assert private.is_dir()                              # nothing moved


def test_without_take_over_the_interrupted_claim_is_still_refused(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = tagged_item(root)
    interrupt(root, slug)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--owner", "me"]) == 1
    assert "interrupted claim" in capsys.readouterr().err


def test_take_over_of_an_active_item_still_works(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = tagged_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--owner", "first"]) == 0
    assert main(["work", "start", slug, "--take-over", "--owner", "second"]) == 0
    assert FsWorkStore.open(root).get(slug).owner == "second"


# ── the web app lists and recovers an interrupted claim ──────────────────────

@pytest.fixture
def served(tmp_path, monkeypatch):
    from test_serve_write import _start_server
    monkeypatch.setenv("TCW_WORK_OWNER", "server@example.com")
    root = node(tmp_path)
    slug = tagged_item(root)
    httpd, base = _start_server(root)
    yield root, base, slug
    httpd.shutdown()
    httpd.server_close()


def test_the_web_lists_an_interrupted_claim(served):
    from test_serve_write import _get_json
    root, base, slug = served
    assert _get_json(base, "/api/work/interrupted-claims") == []
    interrupt(root, slug)
    assert _get_json(base, "/api/work/interrupted-claims") == [
        {"slug": slug, "title": "Interrupted"}]


def test_the_web_recovers_an_interrupted_claim_for_its_own_identity(served):
    from test_serve_write import _req
    root, base, slug = served
    interrupt(root, slug)
    status, body = _req(base, "POST", f"/api/work/{slug}/actions/start", {"recover": True})
    assert status == 200, body
    item = FsWorkStore.open(root).get(slug)
    assert (item.status, item.owner) == ("active", "server@example.com")


@pytest.mark.parametrize("state", ["backlog", "active"])
def test_web_recover_refuses_an_item_that_is_not_an_interrupted_claim(served, state):
    from test_serve_write import _req
    root, base, slug = served
    st = FsWorkStore.open(root)
    if state == "active":
        st.start(slug, owner="someone-else")
    before = (st.get(slug).status, st.get(slug).owner)
    status, body = _req(base, "POST", f"/api/work/{slug}/actions/start", {"recover": True})
    assert status == 422 and "not an interrupted claim" in body["error"], body
    after = FsWorkStore.open(root).get(slug)
    assert (after.status, after.owner) == before


# ── review fold-in: the gaps between "check" and "act" ───────────────────────

def test_a_slug_with_a_settled_folder_is_not_listed(tmp_path):
    root = node(tmp_path)
    slug = tagged_item(root)
    st = FsWorkStore.open(root)
    stray = st.root / ".claiming" / f"{slug}-{'2b' * 16}"
    stray.mkdir(parents=True)
    (stray / "state.yaml").write_text(f"slug: {slug}\ntitle: Stray\n")
    assert st.interrupted_claims() == []


def test_the_store_refuses_to_recover_a_settled_item(tmp_path):
    """Checked by the store against the read it acts on, so a claim published
    after a caller looked is never taken from its owner."""
    root = node(tmp_path)
    slug = tagged_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="first")
    with pytest.raises(ValueError, match="not an interrupted claim"):
        st.start(slug, owner="second", recover=True)
    assert st.get(slug).owner == "first"


# ── strict tracker mode: recovery claims the ticket like any strict start ────

from test_tracker_strict import strict  # noqa: E402,F401  (fixture)
from test_tracker_sync import A, B, TICKET_ID, bound_item, claimed_ticket, cli, fake  # noqa: E402,F401


def test_strict_recovery_claims_the_ticket(strict, fake):
    slug = bound_item(strict)
    interrupt(strict, slug)
    code, _out, err = cli(strict, "work", "start", slug, "--take-over", "--owner", "me")
    assert code == 0, err
    held = fake.tickets[TICKET_ID]
    assert (held.assignee, FsWorkStore.open(strict).get(slug).status) == (A, "active")


def test_strict_recovery_of_someone_elses_ticket_moves_nothing(strict, fake):
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", B)
    private = interrupt(strict, slug)
    code, _out, err = cli(strict, "work", "start", slug, "--take-over", "--owner", "me")
    assert code == 1 and "Bob" in err, err
    assert private.is_dir() and fake.writes() == []


def test_strict_web_recover_is_refused_naming_take_over(strict, fake):
    from test_serve_write import _req, _start_server
    slug = bound_item(strict)
    interrupt(strict, slug)
    httpd, base = _start_server(strict)
    try:
        status, body = _req(base, "POST", f"/api/work/{slug}/actions/start",
                            {"recover": True})
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert status == 409 and f"tcw work start {slug} --take-over" in body["error"], body


def test_strict_recovery_claims_even_when_the_item_is_blocked(strict, fake):
    """A take-over does not check blockers, so neither may the claim step skip on
    them — or the item would move with no ticket claimed."""
    slug = bound_item(strict)
    st = FsWorkStore.open(strict)
    blocker = st.create("Blocker", created="2026-01-01").slug
    st.add_blocker(slug, blocker)
    claimed_ticket(fake, "In Progress", B)
    private = interrupt(strict, slug)
    code, _out, err = cli(strict, "work", "start", slug, "--take-over", "--owner", "me")
    assert code == 1 and "Bob" in err, err
    assert private.is_dir()
