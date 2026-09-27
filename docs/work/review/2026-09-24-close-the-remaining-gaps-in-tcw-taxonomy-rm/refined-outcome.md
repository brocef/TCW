# Refined outcome: close the remaining gaps in tcw taxonomy rm

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-6 (3, 4 and 6 as revised during implementation — see
  `outcome.md`): `tests/test_taxonomy_rm_gaps.py` and the existing taxonomy
  and capabilities tests (135 for the verifier), and its hands-on runs of each
  case, symlinks included.
- Criterion 7: full suite 4519 passed, 3 skipped on the final code; after
  merging main, the affected files passed again (260), and this repository's
  own `tcw validate` is OK.

## For the user to know

The revised contract: `tcw taxonomy rm` now refuses when any untracked file sits
under the term (naming it), deletes only `.DS_Store`, `Thumbs.db` and
`desktop.ini` with the term, and refuses every removal while the capabilities
cannot be read (a broken `extends` included).

## Follow-ups

- Filed: `2026-09-26-check-capability-overrides-for-taxonomy-references-in-capabilities-check-and-taxonomy-rm`.
- Not filed: a possible false refusal when git and the disk spell a name
  differently (case, Unicode form) — unverified, and it can only refuse.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- No capability ledger change. Version not cut.
