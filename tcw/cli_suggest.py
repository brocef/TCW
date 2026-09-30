"""Answer a mistyped subcommand with the command that was probably meant.

argparse reports a wrong subcommand by listing every valid choice at that level,
which says nothing when the word exists one level down (`tcw tracker` for
`tcw work tracker`) or is a synonym (`status` for `show`). `SuggestingParser`
keeps argparse's message word for word and adds one line after it.

Three rules, first match wins:

1. The word is a subcommand somewhere else in the tree: name each full command,
   and complete it with the word that followed when that is wrong there too —
   `tcw tracker status` → `tcw work tracker show`.
2. A small table of synonyms, offered only where their target is valid.
3. Close spellings among the choices valid at that level.

Only subcommands that `--help` lists are ever offered. That is what keeps the
removed `tcw work stage <id>` spellings — registered without `help=` so that the
old form can print its replacement — out of every suggestion, without naming
them here.
"""

from __future__ import annotations

import argparse
import difflib

# One clear target each. Words for removal are left out on purpose: `drop`,
# `delete` and `rm` destroy things, and pointing at one is worse than no hint.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "status": ("show", "list"),
    "info": ("show",),
    "view": ("show",),
    "get": ("show",),
    "cat": ("show",),
    "ls": ("list",),
}

_MAX = 3


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def visible_choices(action: argparse._SubParsersAction) -> list[str]:
    """The subcommands this action lists in its help, in its own order."""
    listed = {choice.dest for choice in action._choices_actions}
    return [name for name in action.choices if name in listed]


def _offered(word: str, choices: list[str]) -> list[str]:
    """Rules 2 and 3 for one level: synonyms valid here, else close spellings."""
    synonyms = [s for s in SYNONYMS.get(word, ()) if s in choices]
    if synonyms:
        return synonyms
    return difflib.get_close_matches(word, choices, n=_MAX, cutoff=0.6)


def _command(path: tuple[str, ...]) -> str:
    return "`" + " ".join(path) + "`"


def _phrase(commands: list[str]) -> str:
    if len(commands) == 1:
        return f"did you mean {commands[0]}?"
    if len(commands) == 2:
        return f"did you mean {commands[0]} or {commands[1]}?"
    return f"did you mean one of {', '.join(commands)}?"


class SuggestingParser(argparse.ArgumentParser):
    """An `ArgumentParser` whose wrong-subcommand error suggests what was meant.

    Every subparser gets this class too, since `add_subparsers` defaults to the
    parent's. `attach_index` gives the whole tree what the hint needs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Python 3.14 has argparse's own close-spelling hint. Off, explicitly,
        # so a later default cannot print a second, different suggestion.
        self.suggest_on_error = False

    def parse_known_args(self, args=None, namespace=None):
        # The root keeps what it was asked to parse: a nested parser reports its
        # own error and needs the word after the one it rejected.
        if getattr(self, "_tcw_root", None) is self:
            self._tcw_argv = list(args) if args is not None else None
        return super().parse_known_args(args, namespace)

    def _check_value(self, action, value):
        if not isinstance(action, argparse._SubParsersAction) or value in action.choices:
            return super()._check_value(action, value)
        choices = visible_choices(action)
        message = (f"invalid choice: {value!r} (choose from "
                   f"{', '.join(repr(c) for c in choices)})")
        if hint := self._hint(str(value), choices):
            message += f"\n{hint}"
        raise argparse.ArgumentError(action, message)

    def _hint(self, word: str, choices: list[str]) -> str:
        root = getattr(self, "_tcw_root", None)
        here = getattr(self, "_tcw_path", None)
        if root is None or here is None:
            return ""
        # Shallowest first: `tcw show` means `tcw work show` before it means
        # `tcw work inbox show`. `sorted` is stable, so ties keep tree order.
        elsewhere = sorted((p for p in root._tcw_index.get(word, ()) if p[:-1] != here),
                           key=len)
        if elsewhere:
            following = _following(root, here, word)
            commands = []
            for path in elsewhere[:_MAX]:
                commands += [_command(path + tail) for tail in _completion(root, path, following)]
            return _phrase(commands[:_MAX])
        offered = _offered(word, choices)
        return _phrase([_command(here + (o,)) for o in offered]) if offered else ""


def _following(root: SuggestingParser, here: tuple[str, ...], word: str) -> str:
    """The word after `word` on the command line, if it is not an option."""
    argv = getattr(root, "_tcw_argv", None) or []
    start = len(here) - 1                           # `here` includes "tcw"
    for index in range(start, len(argv)):
        if argv[index] == word:
            after = argv[index + 1] if index + 1 < len(argv) else ""
            return "" if after.startswith("-") else after
    return ""


def _completion(root: SuggestingParser, path: tuple[str, ...],
                following: str) -> list[tuple[str, ...]]:
    """How to finish `path` with the word typed after it: kept when it is valid
    there or there is nothing to finish, else what that word was likely meant as."""
    parser = root._tcw_parsers.get(path)
    action = _subparsers(parser) if parser is not None else None
    if not following or action is None:
        return [()]
    choices = visible_choices(action)
    if following in choices:
        return [(following,)]
    offered = _offered(following, choices)
    return [(o,) for o in offered] or [()]


def attach_index(root: SuggestingParser) -> None:
    """Walk the finished tree once: every parser learns its own path and the
    root, and the root learns every listed subcommand's full paths."""
    index: dict[str, list[tuple[str, ...]]] = {}
    parsers: dict[tuple[str, ...], argparse.ArgumentParser] = {}

    def walk(parser: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        parser._tcw_root = root
        parser._tcw_path = path
        parsers[path] = parser
        action = _subparsers(parser)
        if action is None:
            return
        listed = set(visible_choices(action))
        for name, child in action.choices.items():
            if name in listed:
                index.setdefault(name, []).append(path + (name,))
            walk(child, path + (name,))

    walk(root, (root.prog,))
    root._tcw_index = index
    root._tcw_parsers = parsers
