"""The 3.0 command surface and its `--help` standard (TCW-73 Design 2, 5;
AC 1, 4).

Checked by walking the parser `build_parser()` actually builds rather than by
reading the source: subcommands are registered from several modules, and some
arguments are added in loops, so a regex over the files undercounts. This file
absorbs `tests/test_cli_help_coverage.py`, whose positional-help check is one
bullet here.
"""

from __future__ import annotations

import argparse
import re
import shlex

import pytest

from tcw.cli import build_parser

# Design 2's 3.0 column, less `config show`, which TCW-72 adds with its own row.
SURFACE = {
    "init", "provision", "validate", "serve", "projects list",
    "taxonomy list", "taxonomy add", "taxonomy show", "taxonomy path", "taxonomy rm",
    "taxonomy search", "taxonomy extends add", "taxonomy extends rm",
    "capabilities list", "capabilities show", "capabilities path", "capabilities add",
    "capabilities set", "capabilities reset", "capabilities rm", "capabilities search",
    "capabilities extends add", "capabilities extends rm", "capabilities drift",
    "work new", "work list", "work show", "work path", "work edit", "work advance",
    "work discard", "work comment", "work rename", "work stage prompt",
    "work procedure", "work lifecycle", "work docs", "work tags list", "work tags add",
    "work tags rm", "work tickets list", "work tickets adopt",
}

REMOVED = {
    "taxonomy init", "capabilities init", "work init", "taxonomy check",
    "capabilities check", "work nodes", "work stage gate", "work stage validate",
    "work procedure prompt", "work inbox", "work tracker", "work start", "work submit",
    "work rework", "work complete", "work drop", "work delete", "work tombstone",
    "work scaffold", "work reconcile", "work delegate", "work escalate",
    *(f"work stage {s}" for s in ("request", "spec", "plan", "implement", "review",
                                  "qa")),
}


def _walk(parser, path=()):
    """Every command path, with its parser and whether it is a leaf."""
    groups = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    for action in groups:
        helps = {c.dest: c.help for c in action._choices_actions}
        for name, child in action.choices.items():
            here = (*path, name)
            is_leaf = not any(isinstance(a, argparse._SubParsersAction)
                              for a in child._actions)
            yield " ".join(here), child, helps.get(name), is_leaf
            yield from _walk(child, here)


@pytest.fixture(scope="module")
def commands():
    return list(_walk(build_parser()))


@pytest.fixture(scope="module")
def leaves(commands):
    return {name: (parser, help) for name, parser, help, leaf in commands if leaf}


def test_the_surface_is_exactly_the_3_0_column(leaves):
    assert len(SURFACE) == 42
    assert set(leaves) == SURFACE


def test_no_removed_command_parses(commands):
    present = {name for name, *_ in commands}
    assert not (present & REMOVED), present & REMOVED


def test_every_command_and_group_has_help_and_a_description(commands):
    missing = [name for name, parser, help, _ in commands
               if not (help or "").strip() or not (parser.description or "").strip()]
    assert not missing, missing


def test_every_leaf_says_what_it_prints_and_writes(leaves):
    for name, (parser, _) in leaves.items():
        lines = parser.description.splitlines()
        assert any(line.startswith("Prints: ") for line in lines), name
        assert any(line.startswith("Writes: ") for line in lines), name


def test_every_leaf_has_examples_that_parse(leaves):
    for name, (parser, _) in leaves.items():
        examples = [line for line in (parser.epilog or "").splitlines()
                    if line.startswith("  tcw ")]
        assert examples, name
        for example in examples:
            # A shell redirection (`< request.md`) is the shell's, not tcw's.
            argv = shlex.split(example.split(" < ")[0])[1:]
            assert argv[:len(name.split())] == name.split(), (name, example)
            try:
                build_parser().parse_args(argv)
            except SystemExit:
                pytest.fail(f"{name}: example does not parse: {example}")


def test_every_argument_and_option_has_help(commands):
    missing = [(name, action.dest) for name, parser, _, _ in commands
               for action in parser._actions
               if not isinstance(action, (argparse._SubParsersAction,
                                          argparse._HelpAction))
               and not (action.help or "").strip()]
    assert not missing, missing


def test_options_are_long_form_with_one_spelling(commands):
    for name, parser, _, _ in commands:
        for action in parser._actions:
            spellings = [o for o in action.option_strings if o not in ("-h", "--help")]
            assert all(not re.fullmatch(r"-[A-Za-z]", o) for o in spellings), (name, spellings)
            assert len(spellings) <= 1, (name, spellings)


def choices_hidden(parser) -> list[str]:
    """Each choice of an option or argument that its command's help does not
    show (Design 5.5: choices are shown in the help)."""
    text = parser.format_help()
    return [f"{action.dest}={choice}" for action in parser._actions
            if action.choices and not isinstance(action, argparse._SubParsersAction)
            for choice in action.choices if str(choice) not in text]


def test_choices_are_shown_in_the_help(commands):
    hidden = [(name, missing) for name, parser, _, _ in commands
              if (missing := choices_hidden(parser))]
    assert not hidden, hidden
    with_choices = {name for name, parser, _, _ in commands for action in parser._actions
                    if action.choices and not isinstance(action, argparse._SubParsersAction)}
    assert {"taxonomy add", "provision"} <= with_choices, with_choices
    # The check sees a choice its help hides: a metavar replaces the `{a,b}`
    # list argparse would print, and the help text names neither.
    probe = argparse.ArgumentParser()
    probe.add_argument("--mode", choices=["alpha", "beta"], metavar="M", help="a mode")
    assert choices_hidden(probe) == ["mode=alpha", "mode=beta"]


def test_top_level_help_carries_the_exit_codes_and_the_stream_rule(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    text = capsys.readouterr().out
    for code in range(7):
        assert re.search(rf"^\s+{code}\s", text, re.MULTILINE), code
    assert "stdout" in text and "stderr" in text


def test_the_walk_sees_the_whole_tree(commands):
    """Guards the walk: if it stopped descending, the tests above would pass by
    seeing nothing rather than by finding nothing."""
    names = {name for name, *_ in commands}
    assert {"work", "work tags", "taxonomy extends", "work tags add"} <= names
