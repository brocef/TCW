# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Commands that move a work item now tell you where it went

Starting, completing, accepting, or creating an item moves it into a different
folder, and until now nothing said which one — so it was easy to go looking for
a started item where it used to be instead of where it now is.

Those four commands now name the item's new home, as a path relative to the
project root:

- `tcw work start my-item` → `started my-item → docs/work/active/my-item`
- `tcw work complete my-item …` → `completed my-item (done) → docs/work/completed/my-item`
- `tcw work inbox accept request.md` → `→ now at docs/work/backlog/my-item`
- `tcw work new "My item"` → `→ created at docs/work/backlog/my-item`

`inbox accept` and `new` still print just the item's name on their normal
output, so anything scripted around them keeps working — the location goes to
the side channel, alongside the hints they already print. Starting with
`--worktree` still reports the worktree, now with the folder as well. Nothing
else about these commands changed.

## Epic summaries now list the capabilities an item declares

When you ran `tcw work reconcile` on an epic, its **Capability deltas** section
would say a child item's capability file was "present but not a list — skipped",
even when the file was written exactly as documented and every other command
accepted it. The summary was reading an older format; the file was fine.

It now lists what each item actually declares:

```
**Capability deltas:**
- child-a/2026-01-01-slice: new billing/download-invoice
- child-a/2026-01-01-slice: changed auth/delete-account
```

If a capability file genuinely cannot be read, the summary now says so and names
the problem, instead of describing it as the wrong shape — and one unreadable
file no longer stops the rest of the summary from being produced.
