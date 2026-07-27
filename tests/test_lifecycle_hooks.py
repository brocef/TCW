"""Hook execution and `tcw work lifecycle`.

The load-bearing test in this file is
`test_a_failing_pre_hook_writes_no_field`. `complete()` writes the resolution
*before* it moves the item, so a `pre` hook evaluated inside the store would
strand a resolution on an unmoved item — one reading as closed while sitting in
`active`. Asserting "did not move" alone would pass that broken implementation.
"""
import json
import subprocess
from pathlib import Path

import yaml

from tcw.cli import main
from tcw.store.fs import FsWorkStore, init


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    return root


def configure(root: Path, lifecycle: dict) -> None:
    p = root / "tcw-config.yaml"
    cfg = yaml.safe_load(p.read_text()) or {}
    cfg.setdefault("work", {})["lifecycle"] = lifecycle
    p.write_text(yaml.safe_dump(cfg, sort_keys=False))
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "configure"], check=True)


def make_item(root: Path, title: str = "Task") -> str:
    st = FsWorkStore.open(root)
    slug = st.create(title, created="2026-01-01").slug
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", f"add {slug}"], check=True)
    return slug


def state_of(root: Path, status: str, slug: str) -> dict:
    return yaml.safe_load(
        (root / "docs/work" / status / slug / "state.yaml").read_text())


# ── pre hooks gate the transition ────────────────────────────────────────────

def test_a_passing_pre_hook_lets_the_transition_through(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    configure(root, {"transitions": {"start": {"pre": [{"command": "true"}]}}})
    monkeypatch.chdir(root)

    assert main(["work", "start", slug]) == 0
    capsys.readouterr()
    assert FsWorkStore.open(root).get(slug).status == "active"


def test_a_failing_pre_hook_aborts_the_transition(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    configure(root, {"transitions": {"start": {"pre": [{"command": "exit 3"}]}}})
    monkeypatch.chdir(root)

    assert main(["work", "start", slug]) == 1
    assert "exit 3" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(slug).status == "backlog"


def test_a_failing_pre_hook_writes_no_field(tmp_path, monkeypatch, capsys):
    """The reason hook execution lives in the CLI rather than the store.

    `complete()` calls `set_field("resolution", ...)` before `transition()`. A
    hook evaluated inside it would abort having already stamped a resolution onto
    an item still sitting in `active` — closed by its data, open by its folder.
    Asserting only that it did not move would pass that implementation.
    """
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug]) == 0
    capsys.readouterr()
    configure(root, {"transitions": {"complete": {"pre": [{"command": "false"}]}}})

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    capsys.readouterr()

    assert FsWorkStore.open(root).get(slug).status == "active"
    assert state_of(root, "active", slug).get("resolution") is None


def test_later_pre_hooks_do_not_run_after_a_failure(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    marker = root / "second-ran.txt"
    configure(root, {"transitions": {"start": {"pre": [
        {"command": "false"},
        {"command": f"touch {marker}"},
    ]}}})
    monkeypatch.chdir(root)

    assert main(["work", "start", slug]) == 1
    capsys.readouterr()
    assert not marker.exists()


def test_pre_hooks_run_in_declared_order(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    log = root / "order.txt"
    configure(root, {"transitions": {"start": {"pre": [
        {"command": f"echo first >> {log}"},
        {"command": f"echo second >> {log}"},
    ]}}})
    monkeypatch.chdir(root)

    assert main(["work", "start", slug]) == 0
    capsys.readouterr()
    assert log.read_text().split() == ["first", "second"]


# ── post hooks never roll back ───────────────────────────────────────────────

def test_a_failing_post_hook_leaves_the_item_moved(tmp_path, monkeypatch, capsys):
    """The move and its commit have already happened. Unwinding a committed
    transition is worse than the failure — so report it, exit non-zero, and leave
    the item where it went."""
    root = node(tmp_path)
    slug = make_item(root)
    configure(root, {"transitions": {"start": {"post": [{"command": "exit 7"}]}}})
    monkeypatch.chdir(root)

    assert main(["work", "start", slug]) == 1               # loud
    err = capsys.readouterr().err
    assert "does not roll that back" in err
    assert FsWorkStore.open(root).get(slug).status == "active"   # but moved

    committed = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True, text=True, check=True).stdout
    assert committed.strip() == ""                          # and committed


# ── the execution contract ───────────────────────────────────────────────────

def test_a_hook_runs_at_the_node_root_with_the_tcw_environment(
        tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    out = root / "env.txt"
    configure(root, {"transitions": {"start": {"pre": [
        {"command": f'{{ pwd; echo "$TCW_SLUG"; echo "$TCW_STATUS"; '
                    f'echo "$TCW_TRANSITION"; echo "$TCW_NODE_ROOT"; }} > {out}'},
    ]}}})
    # Run from a subdirectory: cwd must be the node root, never the process cwd.
    sub = root / "docs"
    monkeypatch.chdir(sub)

    assert main(["work", "start", slug]) == 0
    capsys.readouterr()
    cwd, got_slug, status, transition, node_root = out.read_text().split("\n")[:5]
    assert Path(cwd).resolve() == root.resolve()
    assert got_slug == slug
    assert status == "backlog"                              # the status it moves *from*
    assert transition == "start"
    assert Path(node_root).resolve() == root.resolve()


def test_a_hook_exceeding_the_timeout_is_a_failure(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    configure(root, {"timeout": 1,
                     "transitions": {"start": {"pre": [{"command": "sleep 5"}]}}})
    monkeypatch.chdir(root)

    assert main(["work", "start", slug]) == 1
    assert "timeout" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(slug).status == "backlog"


def test_a_skill_binding_is_reported_and_never_executed(tmp_path, monkeypatch, capsys):
    """The CLI cannot invoke a skill; only the agent can. The ref here would be a
    perfectly good shell command if anything tried to run it."""
    root = node(tmp_path)
    slug = make_item(root)
    marker = root / "should-not-exist.txt"
    configure(root, {"transitions": {"start": {"pre": [
        {"skill": f"touch {marker}"},
    ]}}})
    monkeypatch.chdir(root)

    assert main(["work", "start", slug]) == 0
    assert "invoke the" in capsys.readouterr().err
    assert not marker.exists()
    assert FsWorkStore.open(root).get(slug).status == "active"


def test_a_node_with_no_policy_transitions_exactly_as_before(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug]) == 0
    assert main(["work", "submit", slug]) == 0
    capsys.readouterr()
    assert FsWorkStore.open(root).get(slug).status == "review"


# ── the binding keys on the move, not the verb ───────────────────────────────

def test_a_done_completion_fires_complete_not_discard(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug]) == 0
    capsys.readouterr()
    hit = root / "which.txt"
    configure(root, {"transitions": {
        "complete": {"post": [{"command": f"echo complete > {hit}"}]},
        "discard": {"post": [{"command": f"echo discard > {hit}"}]},
    }})

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    capsys.readouterr()
    assert hit.read_text().strip() == "complete"


def test_a_wontfix_completion_fires_discard_not_complete(tmp_path, monkeypatch, capsys):
    """One binding firing for both "we shipped it" and "we gave up on it" would
    erase the distinction `discard` exists to preserve."""
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug]) == 0
    capsys.readouterr()
    hit = root / "which.txt"
    configure(root, {"transitions": {
        "complete": {"post": [{"command": f"echo complete > {hit}"}]},
        "discard": {"post": [{"command": f"echo discard > {hit}"}]},
    }})

    assert main(["work", "complete", slug, "--resolution", "wontfix", "--confirm"]) == 0
    capsys.readouterr()
    assert hit.read_text().strip() == "discard"


# ── tcw work lifecycle ───────────────────────────────────────────────────────

def test_lifecycle_lists_every_id_in_order(tmp_path, monkeypatch, capsys):
    from tcw.store.base import LIFECYCLE_STEPS
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "lifecycle"]) == 0
    out = capsys.readouterr().out
    positions = [out.index(f"{s.id}  [{s.kind}]") for s in LIFECYCLE_STEPS]
    assert positions == sorted(positions)


def test_lifecycle_json_exposes_the_same_contract(tmp_path, monkeypatch, capsys):
    from tcw.store.base import LIFECYCLE_STEPS
    root = node(tmp_path)
    configure(root, {"stages": {"spec": [{"skill": "superpowers:brainstorming"}]}})
    monkeypatch.chdir(root)

    assert main(["work", "lifecycle", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [s["id"] for s in payload["steps"]] == [s.id for s in LIFECYCLE_STEPS]
    spec = next(s for s in payload["steps"] if s["id"] == "spec")
    assert spec["produces"] == "spec.md"
    assert spec["bindings"]["bind"] == [{"skill": "superpowers:brainstorming"}]


def test_lifecycle_shows_configured_bindings(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    configure(root, {"transitions": {"complete": {"pre": [{"command": "pytest -q"}]}}})
    monkeypatch.chdir(root)
    assert main(["work", "lifecycle", "--transition", "complete"]) == 0
    out = capsys.readouterr().out
    assert "command:pytest -q" in out


def test_lifecycle_never_changes_state(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    before = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout
    assert main(["work", "lifecycle", slug]) == 0
    capsys.readouterr()
    assert FsWorkStore.open(root).get(slug).status == "backlog"
    after = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                           capture_output=True, text=True, check=True).stdout
    assert before == after


# ── --directive ──────────────────────────────────────────────────────────────

def test_directive_emits_one_complete_instruction_when_bound(
        tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    configure(root, {"stages": {"spec": [{"skill": "superpowers:brainstorming"}]}})
    monkeypatch.chdir(root)

    assert main(["work", "lifecycle", "--stage", "spec", "--directive"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == "For this stage, invoke the superpowers:brainstorming skill."


def test_directive_emits_nothing_when_unbound(tmp_path, monkeypatch, capsys):
    """Empty, not a fragment. This is injected verbatim into an agent's context,
    so a bare value would render as a broken sentence."""
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "lifecycle", "--stage", "implement", "--directive"]) == 0
    assert capsys.readouterr().out == ""


def test_directive_exits_non_zero_with_empty_stdout_on_an_unknown_id(
        tmp_path, monkeypatch, capsys):
    """A silent empty injection must never mask an error — otherwise a typo in an
    injected command is indistinguishable from an unbound stage."""
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "lifecycle", "--stage", "brainstorm", "--directive"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "brainstorm" in captured.err


def test_directive_rejects_a_stage_id_given_as_a_transition(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "lifecycle", "--transition", "spec", "--directive"]) == 1
    assert capsys.readouterr().out == ""


def test_directive_names_a_command_binding_without_running_it(
        tmp_path, monkeypatch, capsys):
    """A read-only inspection command stays read-only. Running the command is the
    agent's step, at the same `[judgment]` level as any other binding."""
    root = node(tmp_path)
    marker = root / "ran.txt"
    configure(root, {"stages": {"plan": [{"command": f"touch {marker}"}]}})
    monkeypatch.chdir(root)

    assert main(["work", "lifecycle", "--stage", "plan", "--directive"]) == 0
    out = capsys.readouterr().out
    assert "touch" in out and out.rstrip().endswith(".")
    assert not marker.exists()


def test_directive_combines_a_skill_and_a_command_into_one_sentence(
        tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    configure(root, {"transitions": {"complete": {"pre": [
        {"command": "pytest -q"}, {"skill": "reviewer"},
    ]}}})
    monkeypatch.chdir(root)

    assert main(["work", "lifecycle", "--transition", "complete", "--directive"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("For the complete transition,") and out.endswith(".")
    assert "reviewer" in out and "pytest -q" in out
    assert out.count("\n") == 0                             # one line, always
