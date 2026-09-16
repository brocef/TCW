"""`tcw.harness` — which agent harness directly ran this process.

`detect` is tested with literal ancestor chains and environments, so the answer
never depends on whoever happens to be running the suite: under Claude Code the
real chain holds `claude`, under Codex it holds `codex`, and in CI it holds
neither.
"""
from tcw.harness import ancestor_programs, detect


def test_the_nearest_harness_wins_when_claude_runs_codex():
    """Claude spawning `codex exec` is the common nesting: Codex's commands
    inherit Claude's environment, so only the process tree can tell them apart."""
    assert detect(["bash", "codex", "zsh", "claude"], {}) == "other"


def test_the_nearest_harness_wins_when_codex_runs_claude():
    assert detect(["bash", "claude", "codex"], {}) == "claude"


def test_a_real_claude_code_chain_reads_as_claude():
    """The chain observed from a Claude Code shell on 2026-09-16, including the
    login shell's leading dash and a full path."""
    chain = ["/opt/homebrew/bin/bash", "claude", "-bash", "/usr/bin/login"]
    assert detect(chain, {}) == "claude"


def test_a_codex_variable_outranks_a_claude_variable_without_a_tree():
    env = {"CLAUDECODE": "1", "CODEX_THREAD_ID": "x"}
    assert detect(None, env) == "other"


def test_a_claude_variable_alone_reads_as_claude():
    assert detect(None, {"CLAUDECODE": "1"}) == "claude"


def test_nothing_detected_reads_as_claude():
    """A person in a plain terminal gets the plain output, with no notice."""
    assert detect(None, {}) == "claude"


def test_a_tree_naming_neither_harness_falls_back_to_variables():
    assert detect(["bash", "node", "login"], {}) == "claude"
    assert detect(["bash", "node", "login"], {"CODEX_SANDBOX": "seatbelt"}) == "other"


def test_an_empty_variable_is_not_a_signal():
    assert detect(None, {"CODEX_THREAD_ID": ""}) == "claude"


def _assert_names_or_none(result):
    assert result is None or (isinstance(result, list)
                              and all(isinstance(n, str) and n for n in result)), result


def test_ancestor_programs_reads_this_machine_without_raising():
    _assert_names_or_none(ancestor_programs())


def test_ancestor_programs_without_ps_or_proc_answers_none(monkeypatch, tmp_path):
    """No `ps` on the search path and no `/proc`: the tree is unreadable, which
    is an answer (`None`), never an exception."""
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr("tcw.harness._PROC", tmp_path / "no-proc")
    assert ancestor_programs() is None
