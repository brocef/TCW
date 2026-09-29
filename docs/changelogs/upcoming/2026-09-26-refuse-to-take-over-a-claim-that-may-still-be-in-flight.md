## Fixed

- Recovering an interrupted claim (`start --take-over`, `start(recover=True)`
  behind the web app's Recover) no longer takes a claim that is still in flight.
  `FsWorkStore.start` waits the same 500 ms publication window `get` uses
  (`_await_interrupted`) and refuses with `AlreadyClaimed` if the claim publishes
  meanwhile; it then takes the claim folder by rename into a fresh
  `.claiming/<slug>-<hex>` before writing into it, so a claimant that resumes
  late can no longer publish the recoverer's owner as its own.
- Owner stamps into a claim's `state.yaml` go through `_stamp_claim`, which
  replaces the file atomically from a temporary file in `.claiming/` instead of
  truncating it in place. A claimant or recoverer that loses the claim folder at
  its stamp, its publishing rename or its rollback now reports the lost race
  through `_lost_the_claim` rather than raising `FileNotFoundError` (a 500 from
  the web app).
- `tcw work start --take-over` that found an interrupted claim now calls
  `start(recover=True)`, so a claim that publishes while the `pre` hooks run is
  refused instead of being taken over as an active item. The refusal from the
  wait is an `IllegalTransition` naming who started the item, and no longer
  advises re-running `--take-over`.
- `init`'s pristine-store check ignores a stray `.claiming/.stamp-*.yaml` left
  by a process that died mid-stamp.

## Internal

- One `_publication_window` generator is the 500 ms wait shared by `get`,
  `_lost_the_claim` and recovery, so the three cannot drift apart.
