# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Delete a capability with `tcw capabilities rm`

`tcw capabilities rm <path>` deletes a capability from your ledger. Until now the
only choices were marking it `Omitted`, which says you deliberately don't offer
it, or deleting its folder by hand.

It deletes exactly the one capability you name, and refuses, deleting nothing,
when that would do something you didn't ask for:

- the capability comes from another project you inherit from (change it there,
  or drop your local override with `tcw capabilities reset`);
- other capabilities are nested under its path (remove those first);
- another capability still points at it through `Superseded by`, `Blocked by`,
  `Roles` or `When` (the message names each one, so you can repoint it first).

When a work item deletes a capability, list its path under `removed:` in the
item's `capabilities.yaml`:

```yaml
removed:
    - billing/legacy-export
```

Completing the item is refused while that path still exists.
