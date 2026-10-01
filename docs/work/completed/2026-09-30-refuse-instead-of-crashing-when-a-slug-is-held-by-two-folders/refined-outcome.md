# Refined outcome

**Accepted by the user on 2026-10-01**, together with its three sibling items.

## The acceptance criteria

All seven met: the board prints with the duplicated row marked; `start`,
`submit`, `show` and `edit --blocked-by` refuse in one line naming both folders
and `tcw validate`; `tcw validate` is unchanged; an item blocked by the
duplicate still prints; a duplicated epic does not take the descendant board
down. A sweep of every other verb taking a slug found no traceback.

## Folded in at verify

Two rounds, both recorded in `outcome.md`: the board and `start` label a
blocker held twice and the web app stays up (`e2364c76`); the refusals now say
to merge before removing, and the blocker-cycle wording has a test
(`d61a543f`).

## Deferred, with reasons

- Starting a child of a duplicated epic refuses with the epic's message rather
  than one about the child. A clean refusal, not a crash, and not a criterion.
- `tcw serve` was changed although the spec's non-goals excluded it; it was
  emptying the whole board on one duplicate, so it was fixed here.

## Evidence

- Full suite under bare `pytest` at `d61a543f`, clean tree: **5231 passed, 3 skipped**. This is
  the first full run after `d49c4fee`, which `outcome.md` noted had not had one;
  an earlier run at `0080da55` gave 5228 passed, 3 skipped.
- Each item was assessed against its spec by a separate read-only verifier that
  ran the item's targeted tests and reproduced the behaviour by hand in a
  throwaway project. Every acceptance criterion was met.

## Closeout

- The four items were built, reviewed and tested together and are accepted
  together. The code is already on `main`; there is no merge-back.
- The item was moved to `review` by hand in the session that built it (that
  session was editing `tcw/`); it is completed with `tcw work complete`, run
  against a clean, committed tree.
- No originating GitHub issue. The version cut that ships these four is the
  user's call; nothing is pushed or published by this closeout.
