# Refined outcome — Reconcile `read_artifact` with the canonical presence rule

**Accepted.** The user approved closeout on 2026-08-19, having first sent the
item back at `verify` and asked for the 404 to be fixed rather than deferred.

## The decision

Accepted after one rework. The first submission was rejected because the spec's
premise — "no user-facing path reaches the disagreement" — was false, and the
disproof was executed over real HTTP rather than argued.

## Evidence

Everything below is output from a command run during this item, not inference.

- **The defect, reproduced before the fix.** `GET /api/work/<slug>` returned two
  contradictory presence answers for one whitespace-only artifact in a single
  payload: `item.artifacts['outcome'] = False` (lifecycle rule) against
  top-level `artifacts[].present = True` (resource rule). The web client binds
  to the second and draws an **Open** button; `POST …/artifacts/outcome/open`
  gates on the first and returned `404 'artifact is not present'`. A button that
  could never work.
- **After the fix**, the same reproduction prints
  `CONTRADICTION IN ONE PAYLOAD: False`.
- **Three tests written red first** in `tests/test_serve.py` pin it: a blank
  artifact reports `present: false` in both places of one payload, and the
  `/open` gate agrees.
- **The characterization test earned its place.** With `read_artifact` mutated
  to use `_present`, **388 tests** across the work-store, scaffold, serve,
  projection and show-json suites passed and only the new test failed.
- **No behavior change in the store layer**, verified structurally by comparing
  the ASTs of `tcw/store/base.py` and `tcw/store/fs.py` before and after with
  docstrings stripped — identical. The behavior change is in `tcw/serve/` alone.
- Full suite green at closeout.

## A verification error in this item, recorded not buried

Acceptance criterion 7 grepped for the string `"the one presence rule"` and
passed — but it returned nothing *before* the change too, because the tree had
`"The"` capitalised. The docstring genuinely did change; the check proved
nothing. Found by review, not by me, and confirmed against `git show 6825a76^`.
A criterion that tests a string rather than a property is a spec defect, and it
is the second one this item produced.

## Capability ledger

Reconciled: `tcw capabilities drift` reports **no capability drift**. This item
declared no new capability — it corrected a contract and a consumer of it.

## Closeout choices

- **Merge route:** none needed. All work landed directly on `main`; no branch,
  no PR, no worktree.
- **Documentation:** `docs/changelogs/upcoming.md` — the entry claiming "**No
  behavior changes**" was false once the serve fix landed; narrowed to "no
  behavior change in the store layer" and the serve fix filed separately under
  `## Fixed`. `docs/release-notes/upcoming.md` gained a plain-language entry.
- **Version:** folded into the unpushed **v1.0.0**, on the user's decision. The
  gate was re-run against the network immediately before: `STATUS: FOLDABLE`,
  exit 0 — the tag is still absent from `origin`.
- **Follow-up filed:** the affordance gap — whether the web UI should
  distinguish "this file exists but its stage has not run" from "this file does
  not exist". Reporting `present: false` consistently is not the same as
  explaining why.

## Notes

No post-mortem for this item alone. The pattern worth examining spans the
release, not this item, and is recorded in the stdin item's record and carried to
the release post-mortem.
