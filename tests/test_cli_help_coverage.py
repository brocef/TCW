"""Every positional argument in the whole CLI carries a `help=`.

A positional has no flag to hint at its meaning, so with no `help=` the only clue
to what it wants is its position — which is why `tcw work tracker link slug ticket`
could not tell a reader which of the two was which. That defect was reported
against one command group and was never particular to it.

The check walks the parser `build_parser()` actually builds rather than reading
the source: a regex over `cli.py` undercounted the same gap by 21 while this was
being specified, because subcommands are registered from three modules and some
arguments are added in loops.
"""

from __future__ import annotations

import argparse

from tcw.cli import build_parser


def positionals_without_help(parser, path=("tcw",)) -> list[tuple[str, str]]:
    """`(command path, dest)` for every positional carrying no help text."""
    missing: list[tuple[str, str]] = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                missing += positionals_without_help(sub, (*path, name))
        elif not action.option_strings and not (action.help or "").strip():
            missing.append((" ".join(path), action.dest))
    return missing


def test_the_walk_reaches_all_three_command_groups():
    """Guards the walk: if it stopped descending, the test below would pass by
    seeing nothing rather than by finding nothing."""
    seen = set()

    def visit(parser, path=("tcw",)):
        seen.add(" ".join(path))
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, sub in action.choices.items():
                    visit(sub, (*path, name))

    visit(build_parser())
    for command in ("tcw work", "tcw taxonomy", "tcw capabilities",
                    "tcw work tracker link", "tcw taxonomy extends add"):
        assert command in seen, command
    assert len(seen) > 60, len(seen)


def test_every_positional_has_help():
    missing = positionals_without_help(build_parser())
    assert not missing, "positionals with no help=:\n" + "\n".join(
        f"  {command} → {dest}" for command, dest in sorted(missing))
