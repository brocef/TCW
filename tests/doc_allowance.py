"""What the documents may still name while TCW 3.0 is being built (TCW-70
Design 14; the epic's decision 6).

TCW-70 removes commands and refuses configuration keys that the README, the
guides and the skills still name. Rewriting those documents is TCW-74's and
TCW-75's work, so until then `tests/test_documented_cli_surface.py` lets them
through, by these lists and nothing else.

Each list is guarded (`tests/test_doc_allowance.py`): every command in it must
really be gone from the CLI, and every key must really be refused, so an entry
cannot hide a new mistake.

TCW-71 and TCW-73 add their own removals. TCW-74 and TCW-75 shrink the lists
as they rewrite the text. **TCW-76 requires both to be empty before 3.0.0 is
cut.**
"""

# `tcw work` commands TCW-70 removed. A documented invocation starting with one
# of these is not checked.
REMOVED_COMMANDS = (
    "tcw work start",
    "tcw work submit",
    "tcw work rework",
    "tcw work complete",
    "tcw work drop",
    "tcw work delete",
    "tcw work inbox",
    "tcw work tracker",
    "tcw work tombstone",
    "tcw work reconcile",
    "tcw work delegate",
    "tcw work escalate",
    "tcw work scaffold",
    "tcw work stage gate",
    "tcw work stage validate",
    # TCW-73 (its Design 9.4). `tcw work procedure prompt <id>` needs no
    # entry: `prompt` parses as a procedure name, refused when the command runs.
    "tcw work init",
    "tcw work nodes",
    "tcw taxonomy init",
    "tcw taxonomy check",
    "tcw capabilities init",
    "tcw capabilities check",
)

# Flags TCW-70 removed from commands that survive, as (command, flag). A
# documented invocation of that command is not checked for that flag. Not in
# TCW-70's plan, which counted only whole commands; found when the surface test
# ran.
REMOVED_FLAGS = (
    ("tcw work list", "--status"),
    ("tcw work list", "--include-descendants"),
    ("tcw work new", "--initiative"),
    ("tcw work new", "--epic"),
    ("tcw work edit", "--type"),
    ("tcw work edit", "--initiative"),
    ("tcw work lifecycle", "--transition"),
    # TCW-73 (its Design 2 and 9.4).
    ("tcw work lifecycle", "--directive"),
    ("tcw work lifecycle", "--phase"),
    ("tcw work list", "--tags"),
    ("tcw work new", "--tags"),
    ("tcw work edit", "--tags"),
    ("tcw work edit", "--untags"),
    ("tcw taxonomy add", "-s"),
    ("tcw taxonomy add", "-p"),
    ("tcw capabilities list", "--local-only"),
    ("tcw capabilities add", "-s"),
)

# Whole invocations whose spelling TCW-73 removed while the command itself
# survives under a new shape (its Design 2): `capabilities extends <id>` is
# now `extends add <id>`. A documented invocation starting with one of these
# is not checked; each must fail to parse.
REMOVED_FORMS = (
    "tcw capabilities extends web-frontend",
)

# Configuration keys TCW-69's parser refuses that documents still name.
REFUSED_KEYS = (
    "work.lifecycle",
    "work.tracker",
    "work.retain",
    "work.auto-commit-transitions",
    "work.publish-transitions",
    "work.trunk-branch",
)
