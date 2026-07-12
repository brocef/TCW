As a user, I run `tcw work start <slug>` to move an item from backlog into active. The tool refuses if the item has unresolved blockers; I pass `--force` to override.
For initiative child tasks, the tool also refuses to start the task until its related epic is active.
