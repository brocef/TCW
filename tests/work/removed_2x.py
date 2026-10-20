"""The 2.x commands that must stay gone from the 3.0 CLI.

This list is permanent. It is what the code tests check against
(`tests/work/test_removed_commands.py`, `tests/work/test_no_2x_names.py`,
`tests/work/test_cli_config.py`), and it is not the documentation allowance
TCW-70 kept, which listed what documents could still name while they were
rewritten; TCW-76 emptied and deleted that before 3.0.0 (TCW-76 Design 7).

The entries are those `REMOVED_COMMANDS` held at `5b0dcf95`, when every
removal of TCW-70 and TCW-73 had landed.
"""

REMOVED_2X_COMMANDS = (
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
