As a user, I run `tcw capabilities rm <path>` to delete one of my project's own
capabilities, an override included, that I no longer describe — for example, one whose behavior has been folded into another
capability, where marking it `Omitted` would wrongly say we deliberately do not
have it. It deletes the capability's files and nothing else: each file removed
is named on standard error, and nothing is staged or committed.

It deletes exactly one capability, so it refuses, and deletes nothing, when:

- the path matches no capability, or points outside the capabilities tree
  (exit 4);
- the capability belongs to another project: its full identifier, or a path
  my project has nothing of its own at but inherits a capability at. I change
  it at its source;
- another capability or override is nested under its path. The message names
  them, and I remove those first;
- another capability still points at it through `Superseded by`, `Blocked by`,
  `Roles` or `When`. The message names each one and the field, and I repoint
  those fields first.

The other refusals exit 3.

Removing an override is how I stop overriding an inherited capability, as
[`tcw capabilities reset`](tcw://C/capabilities/reset-an-override) also does;
standard error then adds `<id-path> now shows <full id>`, naming the inherited
capability the path shows again. When the inherited capabilities cannot be
read, that line is left out and the removal still happens.

When a work item deletes a capability, I list its path under `removed:` in the
item's `capabilities.yaml`. That record is what the work gates check: moving the
item on from implementation is refused while that path still resolves (see
[Advance a work item](tcw://C/work/advance-a-work-item)), and removing the
capability is my own step, not something completing the item does for me.

A removal is refused while anything it would delete holds a state file, or a TCW 3.x `meta.yaml` or `item.yaml`, which names tcw migrate.
