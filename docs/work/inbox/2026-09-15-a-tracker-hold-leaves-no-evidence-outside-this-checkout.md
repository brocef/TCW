# A tracker hold leaves no evidence outside this checkout

Found by the review of `2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes`.
It was judged to need its own change.

When several items are bound to one ticket as different parts, TCW holds the ticket
back: moving one part does not move the ticket while another part is still open.
Nothing is written when that happens, because only failed deliveries are recorded.
Later, the last part is allowed to find the ticket in an earlier status only when
another part's item is present in this checkout.

The earlier part is not seen in two cases:

- it was completed in another clone, since finished folders are gitignored by
  default;
- it was removed by `work.retain.completed: false`.

In either case, completing the last part from `review` finds the ticket still in the
active status. Without strict mode that is reported as conflicting, and the local
move still happens with exit 1. With strict mode it is refused. The message names
the possible hold and the fix: move the ticket by hand, or discard the item.

**Options weighed, and the choice made for now.** Codex and an Opus advisor both
chose to document the limit and ship.

- **Write a `held` record on the held item.** This is stronger evidence. The
  costs: it breaks the rule that only failures are recorded, gives the `sync` schema
  a new state, leaves a staged file after every held move, blocks worktree
  merge-backs, and is refused by strict mode's own "undelivered record" check.
- **Treat any part other than `default` as shared.** Rejected. A split ticket can
  keep a `default` part, and this would carry forward a lone part's ticket that a
  reviewer sent back.

A follow-up should settle three things:

- what durable evidence of a hold looks like;
- whether that evidence stays valid after someone moves the ticket back in the
  tracker;
- how it survives clones and retention without blocking merge-backs.

Its acceptance cases should include both an unseen completed part and a deliberate
move back by a reviewer. One idea that needs no write is to read the ticket's own
change history.

## Also: an epic worktree from before strict mode

An epic started with `--worktree` before `strict: true` was set can still merge its
branch when it completes, because epics are exempt from the gates. Strict mode only
refuses starting an epic with a worktree.
