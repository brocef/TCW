"""The documentation allowance cannot hide a real mistake (TCW-70 AC 22).

`tests/doc_allowance.py` lets documents name commands TCW-70 removed and keys
TCW-69 refuses. These guards make each entry prove it: a command still in the
CLI, or a key the parser still accepts, fails here.
"""

import argparse

import pytest

from tcw.cli import build_parser
from tcw.work.config import parse_work_config
from tests.doc_allowance import REFUSED_KEYS, REMOVED_COMMANDS, REMOVED_FLAGS


def _commands(parser: argparse.ArgumentParser, path=("tcw",)):
    """Every command path the parser offers, as `tcw a b` strings, with the
    flags it takes."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                here = (*path, name)
                yield " ".join(here), {o for a in child._actions
                                       for o in a.option_strings}
                yield from _commands(child, here)


@pytest.fixture(scope="module")
def commands():
    return dict(_commands(build_parser()))


def test_the_walk_sees_the_cli(commands):
    assert {"tcw work list", "tcw work stage prompt", "tcw work tags add"} <= set(commands)
    assert "--tag" in commands["tcw work list"]


@pytest.mark.parametrize("command", REMOVED_COMMANDS)
def test_a_removed_command_is_gone(command, commands):
    assert command not in commands, \
        f"{command} is still a command; take it out of REMOVED_COMMANDS"


@pytest.mark.parametrize("key", REFUSED_KEYS)
def test_a_refused_key_is_refused(key):
    section, _, name = key.partition(".")
    assert section == "work"
    # The removal refusal, not any refusal: a key refused only for its value
    # (`tags: {}`) is a key the parser still accepts.
    _, problems = parse_work_config({name: {}})
    assert any(p.key_path == ("work", name) and "removed in TCW 3.0" in p.message
               for p in problems), \
        f"{key} is accepted by the parser; take it out of REFUSED_KEYS"


@pytest.mark.parametrize("command, flag", REMOVED_FLAGS)
def test_a_removed_flag_is_gone(command, flag, commands):
    assert command in commands, f"{command} is not a command at all"
    assert flag not in commands[command], \
        f"{command} still takes {flag}; take it out of REMOVED_FLAGS"
