"""The documentation allowance cannot hide a real mistake (TCW-70 AC 22).

`tests/doc_allowance.py` lets documents name commands TCW-70 removed and keys
TCW-69 refuses. These guards make each entry prove it: a command still in the
CLI, or a key the parser still accepts, fails here.
"""

import argparse

import pytest

from tcw.cli import build_parser
from tcw.work.config import parse_work_config
from tests.doc_allowance import (REFUSED_KEYS, REFUSED_VALUES, REMOVED_COMMANDS,
                                  REMOVED_FLAGS, REMOVED_FORMS)


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
def test_a_refused_key_is_refused(key, tmp_path):
    if "." not in key:
        # A top-level key: the project registry reports it when it loads.
        from tcw.store.project import FsProjectRegistry
        (tmp_path / "tcw-config.yaml").write_text(f"id: p\n{key}: {{}}\n")
        problems = [str(f) for f in FsProjectRegistry.open(tmp_path).check()]
        assert any(key in p and "TCW 3.0" in p for p in problems), \
            f"{key} is accepted; take it out of REFUSED_KEYS"
        return
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


@pytest.mark.parametrize("form", REMOVED_FORMS)
def test_a_removed_form_no_longer_parses(form):
    with pytest.raises(SystemExit) as stop:
        build_parser().parse_args(form.split()[1:])
    assert stop.value.code == 2, f"{form} parses; take it out of REMOVED_FORMS"


@pytest.mark.parametrize("command, value", REFUSED_VALUES)
def test_a_refused_value_is_refused(command, value, tmp_path):
    """The value parses but the command refuses it, by name."""
    import subprocess
    import sys
    argv = [*command.split()[1:], value]
    script = ("import sys; from tcw.cli import main; "
              f"sys.exit(main({argv!r}))")
    r = subprocess.run([sys.executable, "-c", script], cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode != 0 and value in r.stderr, \
        f"{command} {value} is accepted; take it out of REFUSED_VALUES"


# Every entry must still be needed: some live document names it, read with the
# same helpers the scans use (TCW-75 Design 1.5; TCW-74's note 2). An entry no
# document names only hides a future mistake, so it is taken out.

def _live_texts():
    from tests.test_documented_cli_surface import DOC_FILES
    return [d.read_text(encoding="utf-8") for d in DOC_FILES]


@pytest.fixture(scope="module")
def live_texts():
    return _live_texts()


def _named_entries():
    from tests.test_shipped_text import _flag_named, _names
    entries = [(e, lambda t, e=e: _names(t, e))
               for e in (*REMOVED_COMMANDS, *REMOVED_FORMS, *REFUSED_KEYS)]
    entries += [(f"{c} {v}", lambda t, c=c, v=v: _names(t, f"{c} {v}"))
                for c, v in REFUSED_VALUES]
    entries += [(f"{c} {f}", lambda t, c=c, f=f: _flag_named(t, c, f))
                for c, f in REMOVED_FLAGS]
    return entries


@pytest.mark.parametrize("entry, named", _named_entries(),
                         ids=[e for e, _ in _named_entries()])
def test_an_entry_is_still_named_by_some_live_document(entry, named, live_texts):
    assert any(named(text) for text in live_texts), \
        f"no live document names {entry}; take it out of tests/doc_allowance.py"

