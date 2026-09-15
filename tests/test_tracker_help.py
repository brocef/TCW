"""`tcw work tracker --help`: what the six subcommands say they do.

These commands reach a system outside the repository and two of them take two
positionals whose order the command name does not give away, so `--help` is the
only thing standing between a reader and a ticket moved by surprise. The
assertions are structural — a description exists, each positional has one, the
word "claim" is absent from `link`'s — because prose drifts and a test pinned to
wording would be edited away with it. Whether the prose is any *good* is a human
read, recorded at the item's verification.
"""

from __future__ import annotations

import argparse

import pytest

from tcw.cli import build_parser

TRACKER_COMMANDS = ("list", "show", "import", "link", "unlink", "sync")


def _tracker_group() -> argparse._SubParsersAction:
    """The five parsers as `build_parser()` actually builds them — walked, not
    reconstructed, so the test cannot pass against a parser nobody runs."""
    parser = build_parser()
    for name in ("work", "tracker"):
        [group] = [a for a in parser._actions
                   if isinstance(a, argparse._SubParsersAction)]
        parser = group.choices[name]
    [group] = [a for a in parser._actions
               if isinstance(a, argparse._SubParsersAction)]
    return group


def tracker_subparsers() -> dict[str, argparse.ArgumentParser]:
    return dict(_tracker_group().choices)


def listing_help(command: str) -> str:
    """The one-liner `tcw work tracker --help` shows beside the subcommand. It lives
    on the parent's action, not on the subparser, so a test that reads only the
    subparser cannot see the sentence most readers actually read."""
    [action] = [a for a in _tracker_group()._choices_actions if a.dest == command]
    return action.help or ""


def positionals(parser: argparse.ArgumentParser) -> list[argparse.Action]:
    return [a for a in parser._actions
            if not a.option_strings and not isinstance(a, argparse._SubParsersAction)]


def test_the_five_tracker_subcommands_are_all_here():
    """Guards the walk itself: a renamed subcommand must fail loudly rather than
    silently shrink what the tests below range over."""
    assert sorted(tracker_subparsers()) == sorted(TRACKER_COMMANDS)


@pytest.mark.parametrize("command", TRACKER_COMMANDS)
def test_tracker_help_describes_every_subcommand(command):
    parser = tracker_subparsers()[command]
    assert parser.description and parser.description.strip(), command
    assert parser.epilog and parser.epilog.strip(), command
    for action in positionals(parser):
        assert action.help and action.help.strip(), f"{command} {action.dest}"


@pytest.mark.parametrize("command", TRACKER_COMMANDS)
def test_every_tracker_epilog_shows_an_example_invocation(command):
    """An epilog exists to hold the examples; one that holds none is a heading."""
    assert f"tcw work tracker {command}" in tracker_subparsers()[command].epilog


def test_tracker_link_help_does_not_promise_a_claim():
    """`link` used to claim the ticket. Its own help said so, and that sentence is
    the one a reader would act on, so its absence is worth pinning."""
    link = tracker_subparsers()["link"]
    text = (f"{link.description}\n{link.epilog}\n{link.format_help()}\n"
            f"{listing_help('link')}").lower()
    assert "claim" not in text
    assert "assign" not in text


def test_import_help_still_says_it_claims_and_assigns():
    """The other half of the same distinction: `link` stopping is only meaningful
    if `import` is still described as doing it."""
    text = f"{tracker_subparsers()['import'].description}\n{listing_help('import')}".lower()
    assert "claim" in text and "assign" in text
