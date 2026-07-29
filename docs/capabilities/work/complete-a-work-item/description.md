As a user, I run `tcw work complete <slug> --resolution <r>` to close an item, and **the resolution picks where it lands**: `done` files it under `completed/`, while `wontfix`, `duplicate`, and `superseded` file it under `discarded/` (see [Discard a work item](tcw://C/work/discard-a-work-item)). So `completed/` answers "what shipped?" on its own.

I may complete from either `active` or `review`. Completing from `active` skips the verify stage, so the tool prints a note saying so on stderr — advisory only: it does not refuse and does not ask for a second confirmation.

Completing as `done`, the tool checks for unresolved blockers (refused unless I pass `--force`), then prints the Definition-of-Done checklist and refuses until I re-run with `--confirm`. Discarding skips both checks — a blocker is a reason to give up, not a reason I can't — but still requires `--confirm`.
For epics, the tool refuses completion while related initiative child tasks are still open. Once every child is resolved, an epic is **completable directly from `backlog`** — I don't have to `start` a coordinator epic into `active` just to close it. I can also let `tcw work reconcile <epic> --complete-when-ready` auto-complete a ready epic after refreshing its rollup; the Definition-of-Done and capability-reconciliation gates still run either way.

TCW commits the status move itself, scoped to the item's own folders so unrelated edits in my working tree are never swept in. I turn that off with `work.auto-commit-transitions: false` in `tcw-config.yaml`, and `work.trunk-branch` adds an advisory warning when I transition from some other branch.

If the work branch was merged outside TCW — a merged pull request, say — I add `--already-integrated` to skip TCW's merge-back. Every other gate still runs: blockers, the epic-children check, capability reconciliation, and `--confirm`. It is rejected on an item that has no worktree.

Completed items no longer store a Definition-of-Done list. It was the same checklist on every item, so it recorded nothing; the checklist is still printed before I confirm. Which entries it holds is my node's to choose — see [Customize the Definition of Done](tcw://C/work/customize-the-definition-of-done).

When the item came from a GitHub issue, closing it out includes answering that issue: `tcw work path <slug>` finds the item folder and its `initial-request.md` records the issue under `## Origin`. `done`, `duplicate`, and `wontfix` close the issue; `superseded` closes it only when the superseding item absorbed the request rather than deferring it. A discard prints no checklist at all, so on those paths nothing prompts me — see [Triage GitHub issues into work items](tcw://C/plugin/triage-github-issues).
