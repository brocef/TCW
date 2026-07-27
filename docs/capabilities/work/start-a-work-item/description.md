As a user, I run `tcw work start <slug>` to move an item from backlog into active. The tool refuses if the item has unresolved blockers; I pass `--force` to override.
For initiative child tasks, the tool also refuses to start the task until its related epic is active.

TCW commits the status move itself, scoped to the item's own folders so unrelated edits in my working tree are never swept in. I turn that off with `work.auto-commit-transitions: false` in `tcw-config.yaml`, and `work.trunk-branch` adds an advisory warning when I transition from some other branch.
