# A missing parent project blocks epic gates that only look down

## Desired outcome

Completing an epic, and making an epic a plain item (`tcw work edit --type ""`),
refuse over a partial project graph only when a project that could hold the epic's
children is missing — a child or descendant — not when only a parent is.

## Context

Found by code review of
`2026-09-15-let-tcw-work-edit-change-an-item-s-type-to-or-from-epic`.

- `FsWorkStore.initiative_children` (`tcw/store/fs.py`) looks at this node and its
  descendants only, and `initiative_epic` resolves an epic upward. A slice in a
  parent node is therefore never a child of an epic here.
- Both gates refuse on `incomplete_graph_note()`, which comes from
  `FsProjectRegistry.unreachable()` (`tcw/store/project.py`) and lists **every**
  declared project that is missing, parents included.
- Reproduced by the reviewer: a node whose `connected-projects.parent` is not checked
  out, holding an epic with no children — `update_work(epic, type="")` refuses with
  "this checkout is missing connected project(s): away-parent. Run from a checkout
  that has them." The same holds for `complete`'s epic gate
  (`tcw/store/base.py`, "Cannot verify the initiative children").

So in a multi-repository setup where only a child repository is cloned, no epic
there can be completed without `--force`, or made plain at all, and the message
sends the user to fetch a repository that cannot hold any children.

## Notes

- Fix both gates together; they share the note on purpose.
- `edit --type ""` has no `--force`, so it is the harder of the two to get past.
