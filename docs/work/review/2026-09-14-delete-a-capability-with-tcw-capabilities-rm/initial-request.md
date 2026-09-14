# Delete a capability with tcw capabilities rm

## What is being asked for

A command that deletes a capability from the ledger: `tcw capabilities rm <path>`,
the counterpart of the existing `tcw taxonomy rm <path>`.

Today nothing can delete a capability. `tcw capabilities --help` lists `init, list,
show, path, add, set, reset, search, extends, check, drift`. The only ways to get
rid of an entry are to mark it `Omitted`, which the capabilities skill defines as
"we deliberately don't have this", or to delete its folder by hand, which is the
filesystem shortcut `docs/lifecycle/abstraction.md` rules out.

## Why now

`2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill` folds nine
existing capabilities into one capability per skill. The behavior they describe
still works, so marking them `Omitted` would make the ledger say something false.
The requester chose (2026-09-14) to add a delete command in its own item, landing
first, so that item can delete the nine entries outright. That item is blocked by
this one.

## What the requester and the reviews established

- It should mirror `tcw taxonomy rm`: path-addressed, refuses an ambiguous or
  unknown path, writes nothing when refused.
- It must pass the abstraction litmus test: a non-filesystem store must be able to
  implement "delete this capability", so it belongs in the store interface, not as
  a filesystem trick.
- **A work item must be able to declare a removal.** The completion gate refuses
  a `changed:` path that does not resolve (`tcw/work/recursion.py:62` onward), so a
  deleted capability cannot be listed there. The item needs a way to record
  "removed" in `capabilities.yaml` that the gate accepts.
- `skills/tcw-capabilities/SKILL.md:107` already tells agents to "use `remove`" for
  a standalone local capability — a command that does not exist. This item makes
  that sentence true, or corrects it to the real command name.

## Notes

- Written from the brainstorming and review conversation for the consolidation
  item, not from a separate conversation with the requester. Assumptions for
  `spec` to confirm: what `rm` does to an inherited capability (refuse, like
  `reset` refuses a standalone one?), what it does when another capability's
  `Superseded by` or `Blocked by` points at the target, and what happens to a
  local override.
- Reference material: asked in the consolidation item's request; none provided.

## References

- `2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill` — the
  item that needs this; its spec lists the nine capabilities to delete.
- `tcw/taxonomy/cli.py:104` (`_rm`) — the command to mirror.
- `tcw/work/recursion.py` — the completion gate that reads `capabilities.yaml`.
- `skills/tcw-capabilities/SKILL.md:107` — the stale "use `remove`" instruction.
