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
