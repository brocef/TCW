"""The exit codes every `tcw` command returns.

TCW-73 owns the table that documents them; these are its numbers. `advance`
already returns them, which is why they exist before the commands that print
them.
"""

OK = 0
ERROR = 1  # the backend or TCW itself failed
USAGE = 2  # the command was asked for something that cannot be asked
REFUSED = 3  # a legal request that a rule or a gate turned down; nothing changed
NOT_FOUND = 4
UNREACHABLE = 5  # a backend or another project could not be reached
MOVED_WITH_PROBLEM = 6  # the item moved, but something after the move failed
