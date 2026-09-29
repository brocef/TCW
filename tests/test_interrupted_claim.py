"""Recovering an interrupted claim from the CLI and the web app
(spec: 2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app).

An interrupted claim is made the way a dead process leaves one: the item's folder
moved into `.claiming/<slug>-<32 hex>` and never published."""

import subprocess
import threading
import time
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.base import AlreadyClaimed, IllegalTransition
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


# ── a claim that may still be in flight is not taken ─────────────────────────
# (spec: 2026-09-26-refuse-to-take-over-a-claim-that-may-still-be-in-flight)

def publish_as(st: FsWorkStore, folder: Path, slug: str, owner: str) -> None:
    """What a competing claimant's last two steps do: stamp, then publish."""
    state = yaml.safe_load((folder / "state.yaml").read_text())
    state["owner"] = owner
    (folder / "state.yaml").write_text(yaml.safe_dump(state))
    folder.replace(st.root / "active" / slug)


def live_claimant(monkeypatch, st: FsWorkStore, private: Path, slug: str,
                  owner: str) -> threading.Thread:
    """A claimant still between its two renames, publishing 50 ms after the
    recovery's wait begins — inside the window, whatever the machine's speed.
    Without the wait it never hears the signal and publishes too late."""
    waiting = threading.Event()
    real = FsWorkStore._await_interrupted

    def signalled(self, *args):
        waiting.set()
        return real(self, *args)

    monkeypatch.setattr(FsWorkStore, "_await_interrupted", signalled)

    def run():
        waiting.wait(timeout=3)
        time.sleep(0.05)
        try:
            publish_as(st, private, slug, owner)
        except FileNotFoundError:
            pass                                   # the recovery took it
    t = threading.Thread(target=run)
    t.start()
    return t


def assert_claim_area_clean(st: FsWorkStore) -> None:
    claiming = st.root / ".claiming"
    assert not claiming.exists() or list(claiming.iterdir()) == []


def test_take_over_refuses_a_claim_that_publishes_within_the_window(tmp_path, monkeypatch):
    root = node(tmp_path)
    slug = tagged_item(root)
    private = interrupt(root, slug)
    st = FsWorkStore.open(root)
    t = live_claimant(monkeypatch, st, private, slug, "alice")
    with pytest.raises(IllegalTransition, match="alice"):
        st.start(slug, owner="me", take_over=True)
    t.join()
    assert FsWorkStore.open(root).get(slug).owner == "alice"


def test_recover_refuses_a_claim_that_publishes_within_the_window(tmp_path, monkeypatch):
    root = node(tmp_path)
    slug = tagged_item(root)
    private = interrupt(root, slug)
    st = FsWorkStore.open(root)
    t = live_claimant(monkeypatch, st, private, slug, "alice")
    with pytest.raises(IllegalTransition, match="alice"):
        st.start(slug, owner="me", recover=True)
    t.join()
    assert FsWorkStore.open(root).get(slug).owner == "alice"


def test_a_claimant_whose_folder_is_taken_reports_the_winner(tmp_path, monkeypatch):
    root = node(tmp_path)
    slug = tagged_item(root)
    st = FsWorkStore.open(root)
    real = FsWorkStore._stamp_claim

    def taken_first(self, folder, *args, **kwargs):
        publish_as(self, folder, slug, "bob")
        return real(self, folder, *args, **kwargs)

    monkeypatch.setattr(FsWorkStore, "_stamp_claim", taken_first)
    with pytest.raises(AlreadyClaimed, match="bob"):
        st.start(slug, owner="me")
    assert FsWorkStore.open(root).get(slug).owner == "bob"
    assert_claim_area_clean(st)


def test_a_take_over_whose_steal_loses_reports_the_winner(tmp_path, monkeypatch):
    root = node(tmp_path)
    slug = tagged_item(root)
    interrupt(root, slug)
    st = FsWorkStore.open(root)

    def published_after_the_wait(self, slug_, found):
        publish_as(self, found, slug_, "bob")

    monkeypatch.setattr(FsWorkStore, "_await_interrupted", published_after_the_wait)
    with pytest.raises(AlreadyClaimed, match="bob"):
        st.start(slug, owner="me", take_over=True)
    assert FsWorkStore.open(root).get(slug).owner == "bob"
    assert_claim_area_clean(st)


def test_a_claimant_resuming_after_a_take_over_cannot_publish(tmp_path, monkeypatch):
    """A claimant suspended past the window resumes after the recoverer has
    stamped: its rename must fail, not publish the recoverer's stamp as its own."""
    root = node(tmp_path)
    slug = tagged_item(root)
    found = interrupt(root, slug)
    st = FsWorkStore.open(root)
    monkeypatch.setattr(FsWorkStore, "_await_interrupted", lambda self, s, f: None)
    real = FsWorkStore._stamp_claim
    resumed = []

    def claimant_resumes(self, folder, *args, **kwargs):
        real(self, folder, *args, **kwargs)
        try:
            found.replace(self.root / "active" / slug)
            resumed.append("published")
        except FileNotFoundError:
            resumed.append("refused")

    monkeypatch.setattr(FsWorkStore, "_stamp_claim", claimant_resumes)
    st.start(slug, owner="me", take_over=True)
    assert resumed == ["refused"]
    assert FsWorkStore.open(root).get(slug).owner == "me"


def test_the_cli_take_over_refuses_a_claim_published_while_its_hooks_ran(
        tmp_path, monkeypatch, capsys):
    """The CLI finds the claim, runs `pre` hooks, then calls the store; a claim
    published in between must be refused, not taken over as an active item."""
    import tcw.work.cli as work_cli
    root = node(tmp_path)
    slug = tagged_item(root)
    private = interrupt(root, slug)
    st = FsWorkStore.open(root)
    real = work_cli.run_pre
    published = []

    def hooks_while_claimant_publishes(*args, **kwargs):
        if not published:
            publish_as(st, private, slug, "alice")
            published.append(True)
        return real(*args, **kwargs)

    monkeypatch.setattr(work_cli, "run_pre", hooks_while_claimant_publishes)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--take-over", "--owner", "me"]) == 1
    assert "not an interrupted claim" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(slug).owner == "alice"


def test_an_unrelated_missing_folder_at_publish_rolls_the_claim_back(tmp_path, monkeypatch):
    """Only a claim folder that is gone means a lost race. A publishing rename
    that fails for another reason, with the claim folder still there, is an
    ordinary failure, and the item goes back to backlog as before."""
    import os
    import tcw.store.fs as fs
    root = node(tmp_path)
    slug = tagged_item(root)
    st = FsWorkStore.open(root)
    real = os.replace

    def publish_fails(src, dst):
        if Path(dst).parent.name == "active":
            raise FileNotFoundError(dst)       # as if `active/` had gone
        return real(src, dst)

    monkeypatch.setattr(fs.os, "replace", publish_fails)
    with pytest.raises(FileNotFoundError):
        st.start(slug, owner="me")
    monkeypatch.setattr(fs.os, "replace", real)
    assert FsWorkStore.open(root).get(slug).status == "backlog"
    assert_claim_area_clean(st)


def test_a_stamp_leaves_nothing_behind_and_keeps_the_items_fields(tmp_path):
    root = node(tmp_path)
    slug = tagged_item(root)
    st = FsWorkStore.open(root)
    other = st.create("Interrupted too", created="2026-01-01").slug
    st.set_field(other, "tags", ["bug"])
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "other"], check=True)
    st.start(slug, owner="first")
    interrupt(root, other)
    st.start(other, owner="second", take_over=True)
    assert_claim_area_clean(st)
    for s, owner in ((slug, "first"), (other, "second")):
        state = yaml.safe_load((st.path(s) / "state.yaml").read_text())
        assert (state["owner"], state["tags"], state["created"]) == (owner, ["bug"], "2026-01-01")
        assert state["title"]


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
