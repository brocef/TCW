"""A wrong subcommand or stage name is answered with what was probably meant
(spec: 2026-09-29-suggest-what-was-meant-when-a-subcommand-or-stage-name-is-wrong)."""

import argparse
import subprocess
import sys

import pytest

from tcw.cli import build_parser, main



def usage_error(capsys, *argv: str) -> str:
    with pytest.raises(SystemExit) as raised:
        main(list(argv))
    assert raised.value.code == 2
    return capsys.readouterr().err


def stage(tmp_path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tcw.cli", "work", "stage", *argv],
                          cwd=tmp_path, capture_output=True, text=True, timeout=60)


# ── 1-3: subcommands ─────────────────────────────────────────────────────────

def test_a_subcommand_one_level_down_is_named_with_the_verb_meant(capsys):
    err = usage_error(capsys, "tracker", "status")
    assert "invalid choice: 'tracker'" in err, err            # today's text kept
    assert "tcw work tracker show" in err, err


def test_status_suggests_show_and_list(capsys):
    err = usage_error(capsys, "work", "status", "some-slug")
    assert "invalid choice: 'status'" in err, err
    assert "tcw work show" in err and "tcw work list" in err, err


def test_a_close_spelling_is_suggested(capsys):
    err = usage_error(capsys, "work", "strat", "some-slug")
    assert "tcw work start" in err, err


# ── 4, 5: stage names ────────────────────────────────────────────────────────

@pytest.mark.parametrize("word,meant", [
    ("refined-outcome", "verify"), ("refined-outcome.md", "verify"),
    ("outcome", "implement"), ("initial-request", "request"),
    ("post-mortem", "postmortem"),
])
def test_an_artifact_name_names_the_stage_that_writes_it(tmp_path, word, meant):
    out = stage(tmp_path, "gate", word, "some-slug")
    assert out.returncode == 1, out.stderr
    assert f"unknown stage '{word}'" in out.stderr, out.stderr    # today's text kept
    assert f"`{meant}` stage" in out.stderr, out.stderr


def test_a_transition_given_as_a_stage_names_its_command(tmp_path):
    out = stage(tmp_path, "gate", "start", "some-slug")
    assert out.returncode == 1 and "tcw work start" in out.stderr, out.stderr
    assert "transition" in out.stderr, out.stderr


def test_rework_names_its_artifact_and_its_transition(tmp_path):
    out = stage(tmp_path, "prompt", "rework", "some-slug")
    assert "`verify` stage" in out.stderr and "tcw work rework" in out.stderr, out.stderr


# ── 6: the removed stage spellings are never offered ─────────────────────────

def test_a_stage_verb_typo_is_offered_gate_and_no_removed_spelling(capsys):
    err = usage_error(capsys, "work", "stage", "gat", "x")
    assert "tcw work stage gate" in err, err
    assert "tcw work stage spec" not in err and "'spec'" not in err, err


def test_a_stage_id_at_the_top_is_not_sent_to_a_removed_spelling(capsys):
    err = usage_error(capsys, "spec")
    assert "tcw work stage spec" not in err, err


# ── 7: option values get no hint ─────────────────────────────────────────────

def test_an_option_value_gets_no_hint(capsys):
    err = usage_error(capsys, "work", "list", "--status", "actve")
    assert "invalid choice: 'actve'" in err, err
    assert "did you mean" not in err.lower(), err


# ── 8: every parser in the tree suggests ─────────────────────────────────────

def test_every_parser_in_the_tree_suggests():
    from tcw.cli_suggest import SuggestingParser

    def walk(p, path):
        assert isinstance(p, SuggestingParser), " ".join(path)
        for a in p._actions:
            if isinstance(a, argparse._SubParsersAction):
                for name, sp in a.choices.items():
                    walk(sp, path + [name])
    walk(build_parser(), ["tcw"])
