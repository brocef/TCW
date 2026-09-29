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
