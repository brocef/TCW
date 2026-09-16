"""`tcw work stage validate` — the argument check `tcw-work-stage` injects first.

Valid means "`tcw work stage prompt` would accept these". Everything is run
in-process with the harness pinned, so the output never depends on whether the
suite itself runs under Claude Code, Codex, or CI.
"""
import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsWorkStore, init

ERROR = ("**Skill Invocation Error: The tcw-work-stage skill must be invoked with "
         "one to two arguments: `tcw-work-stage stage-id [work-slug]`**")
NOTICE = ("Your AI agent harness does not support dynamic context injection. You "
          "will need to manually run all commands with !`command` to interpret "
          "this skill.")
HARNESS_VARIABLES = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID",
                     "CODEX_SANDBOX", "CODEX_SESSION_ID")


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


@pytest.fixture
def node(tmp_path, monkeypatch):
    """A work node holding one backlog item, with no harness detectable."""
    root = _node(tmp_path)
    item = FsWorkStore.open(root).create("Thing", body="req\n")
    monkeypatch.chdir(root)
    monkeypatch.setattr("tcw.work.cli.ancestor_programs", lambda: None)
    for name in HARNESS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return item.slug


def _validate(capsys, *words):
    code = main(["work", "stage", "validate", *words])
    out, err = capsys.readouterr()
    return code, out, err


def _assert_invalid(code, out, err, reason):
    assert code == 1
    assert out == f"{ERROR}\n\n{reason}\n", out
    assert err == "", err


# ── valid: prints nothing ────────────────────────────────────────────────────

def test_a_stage_and_an_existing_item_print_nothing(node, capsys):
    assert _validate(capsys, "spec", node) == (0, "", "")


def test_inbox_alone_prints_nothing(node, capsys):
    assert _validate(capsys, "inbox") == (0, "", "")


def test_the_item_is_optional_for_other_stages(node, capsys):
    assert _validate(capsys, "plan") == (0, "", "")


def test_the_item_status_is_not_checked(node, capsys):
    """`prompt` prints a stage's instructions for an item in the wrong status,
    so `validate` must not refuse it: the item is in backlog, `verify` is not."""
    assert _validate(capsys, "verify", node) == (0, "", "")


# ── invalid: the error and a reason ──────────────────────────────────────────

def test_no_arguments(node, capsys):
    _assert_invalid(*_validate(capsys), "No arguments were given.")


def test_too_many_arguments(node, capsys):
    _assert_invalid(*_validate(capsys, "spec", node, "extra"),
                    f"3 arguments were given: `spec {node} extra`.")


def test_an_unknown_stage(node, capsys):
    code, out, err = _validate(capsys, "nope")
    _assert_invalid(code, out, err,
                    "`nope` is not a stage; expected one of inbox, request, spec, "
                    "plan, implement, verify, postmortem.")


def test_inbox_refuses_an_item(node, capsys):
    _assert_invalid(*_validate(capsys, "inbox", node),
                    "`inbox` runs before a work item exists and takes no work item.")


def test_an_item_that_does_not_exist(node, capsys):
    _assert_invalid(*_validate(capsys, "spec", "no-such-item"),
                    "No work item matches `no-such-item`.")


def test_an_unknown_project_qualifier_reports_resolves_message_on_stdout(node, capsys):
    """`_resolve` prints its own reason to stderr; `validate` captures it so the
    whole report is on stdout, where an injected line or a pipe reads it."""
    code, out, err = _validate(capsys, "spec", "nowhere/thing")
    assert code == 1
    assert out.startswith(f"{ERROR}\n\ntcw work stage validate: "), out
    assert err == "", err


@pytest.mark.parametrize("words", [("plan",), ("inbox",)])
def test_one_word_outside_a_work_node_is_invalid_like_prompt(tmp_path, monkeypatch,
                                                             capsys, words):
    """`prompt` needs a work node even with no item, so `validate` must too —
    otherwise the answer would depend on how many words were given."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("tcw.work.cli.ancestor_programs", lambda: None)
    for name in HARNESS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    code, out, err = _validate(capsys, *words)
    assert code == 1
    assert out.startswith(f"{ERROR}\n\ntcw work: no tcw work node here"), out
    assert err == "", err


def test_a_dash_word_after_the_separator_is_judged_not_parsed(node, capsys):
    """The skill line passes `--` first, so a stage typed as `-h` is reported as
    an unknown stage rather than printing argparse's help into the skill."""
    code, out, err = _validate(capsys, "--", "-h")
    assert code == 1
    assert "`-h` is not a stage" in out, out
    assert "usage:" not in out, out


# ── under another harness: the notice first ─────────────────────────────────

def test_another_harness_gets_the_notice_alone_when_valid(node, capsys, monkeypatch):
    monkeypatch.setenv("CODEX_THREAD_ID", "x")
    assert _validate(capsys, "spec", node) == (0, f"{NOTICE}\n", "")


def test_another_harness_gets_the_notice_then_the_error(node, capsys, monkeypatch):
    monkeypatch.setenv("CODEX_THREAD_ID", "x")
    code, out, err = _validate(capsys, "nope")
    assert code == 1
    assert out.startswith(f"{NOTICE}\n\n{ERROR}\n\n`nope` is not a stage"), out


def test_claude_code_gets_no_notice(node, capsys, monkeypatch):
    monkeypatch.setattr("tcw.work.cli.ancestor_programs",
                        lambda: ["bash", "claude", "-bash"])
    monkeypatch.setenv("CODEX_THREAD_ID", "inherited")
    assert _validate(capsys, "spec", node) == (0, "", "")


# ── the verb group ───────────────────────────────────────────────────────────

def test_help_lists_all_three_verbs():
    r = subprocess.run(["tcw", "work", "stage", "--help"],
                       capture_output=True, text=True)
    assert "{prompt,gate,validate}" in r.stdout, r.stdout
