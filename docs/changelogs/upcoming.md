# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Fixed

- **Two `tcw work tracker show` notes overstated what one ticket can show**
  (GitHub issue #36). Both are `Assessment.detail` strings in
  `tcw/tracker/claim.py`.
  - The `CLAIM_NOT_OFFERED` note named two explanations, a wrong
    `transitions.claim` name or a ticket past the claim, and missed a ticket that
    has not reached it yet (for example, one still in Triage). It now names all
    three.
  - The note for an offered claim said exclusivity "can only be read from a
    ticket already in that status". On an exclusive workflow that is false: `show`
    never passes `landing_status` to `assess()`, so the landed ticket still reports
    `NOT_DETERMINED`. The note now says a landed ticket can reveal a workflow that
    is not exclusive, never one that is, and that exclusivity is confirmed only
    when a claim is made or from the workflow definition.
  - `docs/guide/work.md` and `skills/tcw-work/references/commands.md` repeated both
    two-case explanations and are corrected to match. Two tests in
    `tests/test_tracker_claimability.py` assert the new wording and the absence of
    the old.
