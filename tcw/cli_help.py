"""How every `tcw` command describes itself (TCW-73 Design 5).

A leaf command's `--help` says what it is for, then two closing lines, what it
prints on stdout and what it writes, and an epilog of example invocations. A
command group has a one-line help and a description. Both are built here, so
the standard is applied in one place and `tests/test_cli_help_standard.py`
checks the result by walking the parser.
"""

from __future__ import annotations

import argparse


def command(sub: argparse._SubParsersAction, name: str, *, help: str, prints: str,
            writes: str, examples: list[str], description: str = "",
            **kwargs) -> argparse.ArgumentParser:
    """A leaf command parser. `prints` and `writes` become the description's
    `Prints:` and `Writes:` lines; each of `examples` is a command line
    without the leading `tcw `."""
    lead = (description or help).strip()
    lead = lead[0].upper() + lead[1:]
    text = f"{lead}{'' if lead.endswith('.') else '.'}\n\nPrints: {prints}\nWrites: {writes}"
    epilog = "examples:\n" + "\n".join(f"  tcw {example}" for example in examples)
    return sub.add_parser(name, help=help, description=text, epilog=epilog,
                          formatter_class=argparse.RawDescriptionHelpFormatter,
                          **kwargs)


def group(sub: argparse._SubParsersAction, name: str, help: str,
          description: str = "") -> argparse.ArgumentParser:
    """A command group parser: a one-line help, and a description."""
    lead = (description or help).strip()
    return sub.add_parser(name, help=help,
                          description=lead[0].upper() + lead[1:])


EXIT_CODES = """\
stdout carries only what a command produces; everything said to a person
(progress, files written, warnings, errors) goes to stderr.

exit codes:
  0  OK
  1  error: the backend or TCW itself failed
  2  usage: a malformed command or value
  3  refused: a gate, a name collision or a record that depends on this one
  4  not found: no such item, term, capability, tag or ticket
  5  unreachable: Jira, or a declared project not on this machine
  6  the item moved, but something after the move failed"""
