As a user, I run `tcw work complete <slug> --resolution <r>`; the tool checks for unresolved blockers (refused unless I pass `--force`), then prints the Definition-of-Done checklist and refuses until I re-run with `--confirm`.
For epics, the tool refuses completion while related initiative child tasks are still open.
