As a user, I run `tcw capabilities rm <path>` to delete a local capability I no
longer describe — for example, one whose behavior has been folded into another
capability, where marking it `Omitted` would wrongly say we deliberately do not
have it. It deletes the capability's files and nothing else: each file removed
is named on standard error, and nothing is staged or committed.

It deletes exactly one capability, so it refuses, and deletes nothing, when:

- the path matches no capability, or points outside the capabilities tree
  (exit 4);
- the capability is inherited from another project. I change it at its source;
  if I have a local override of it,
  [`tcw capabilities reset`](tcw://C/capabilities/reset-an-override) drops that
  override;
- a bare path matches capabilities in more than one inherited project (a usage
  error, exit 2);
- another capability or override is nested under its path. The message names
  them, and I remove those first;
- another capability still points at it through `Superseded by`, `Blocked by`,
  `Roles` or `When`. The message names each one and the field, and I repoint
  those fields first.

The other refusals exit 3.

When a work item deletes a capability, I list its path under `removed:` in the
item's `capabilities.yaml`. That record is what the work gates check: moving the
item on from implementation is refused while that path still resolves (see
[Advance a work item](tcw://C/work/advance-a-work-item)), and removing the
capability is my own step, not something completing the item does for me.
