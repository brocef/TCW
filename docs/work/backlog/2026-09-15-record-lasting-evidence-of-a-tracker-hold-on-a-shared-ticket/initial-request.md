# Record lasting evidence of a tracker hold on a shared ticket

## What is wanted

When several work items are bound to one ticket as different parts, TCW holds the
ticket back: moving one part does not move the ticket while another part is still
open. Nothing is written when that happens. Later, the last part may only find the
ticket in an earlier status if another part's item is present in this checkout.

That fails in two ordinary cases — the earlier part was completed in another clone
(finished folders are gitignored by default), or it was removed by
`work.retain.completed: false`. Completing the last part from `review` then finds the
ticket still in the active status: reported as a conflict (exit 1, local move still
made) without strict mode, and refused with it.

Wanted: a hold leaves evidence that outlives this checkout, so the last part can
finish normally wherever it is completed.

## Questions the request leaves open

The follow-up must settle, and the entry's authors named these explicitly:

- what durable evidence of a hold looks like;
- whether that evidence stays valid after someone moves the ticket back in the
  tracker on purpose;
- how it survives clones and retention without blocking worktree merge-backs.

## Constraints

- Acceptance cases must include both an unseen completed part and a reviewer's
  deliberate move back.
- The options already weighed are on record in `intake.md` and should be inherited
  rather than re-argued: a `held` record on the item was judged costly (it breaks
  "only failures are recorded", leaves a staged file after every held move, blocks
  merge-backs, and trips strict mode's own record check); treating any non-`default`
  part as shared was rejected. Reading the ticket's own change history was suggested
  as a way that needs no write.

## Out of scope

- The epic-worktree note and the locked held item under strict mode — tracked in
  `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`.

## Notes

- Kept on its own at triage, although it concerns the same sync feature as the sync
  delivery item, because it is an open design question rather than a fix.
- Today's behaviour is the documented limit chosen when strict mode shipped (Codex
  and an Opus advisor both chose "document and ship").
- Reference material: asked; none provided.

## References

- `docs/work/completed/2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes/` —
  the review that found this, and where the limit is documented.
