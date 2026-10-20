"""What the documents may still name while TCW 3.0 is being built (TCW-70
Design 14; the epic's decision 6).

TCW-70 removes commands and refuses configuration keys that the README, the
guides and the skills still name. Rewriting those documents is TCW-74's and
TCW-75's work, so until then `tests/test_documented_cli_surface.py` lets them
through, by these lists and nothing else.

Each list is guarded (`tests/test_doc_allowance.py`): every command in it must
really be gone from the CLI, and every key must really be refused, so an entry
cannot hide a new mistake.

TCW-71 and TCW-73 added their own removals; TCW-74 and TCW-75 shrank the
lists as they rewrote the text, and TCW-76 removed the last entry when it
rewrote `AGENTS.md`. A list emptied entirely stays as an empty tuple, so its
importers keep working. **TCW-76 requires every list to be empty before 3.0.0
is cut.**
"""

# `tcw work` commands TCW-70 and TCW-73 removed. A documented invocation
# starting with one of these is not checked. TCW-76 rewrote `AGENTS.md`, the
# last document naming one.
REMOVED_COMMANDS: tuple[str, ...] = ()

# Flags removed from commands that survive, as (command, flag). A documented
# invocation of that command is not checked for that flag.
REMOVED_FLAGS: tuple[tuple[str, str], ...] = ()

# Whole invocations whose spelling TCW-73 removed while the command itself
# survives under a new shape. Each must fail to parse.
REMOVED_FORMS: tuple[str, ...] = ()

# Positional values the parser accepts but the command refuses, as (command,
# value).
REFUSED_VALUES: tuple[tuple[str, str], ...] = ()

# Configuration keys TCW-69's parser refuses that documents still name. TCW-76
# rewrote the last capability record that named them.
REFUSED_KEYS: tuple[str, ...] = ()
