# Refined outcome: ask the requester for reference material during the request stage

**Accepted.** The user reviewed the assessment — including the three prose defects
found during verification and the two corrections to `outcome.md` — and approved
closeout without requested changes.

## The decision

Accepted as shipped. No rework. The user had pre-approved the change on its
merits before verification began ("it's approved from my end") and confirmed
closeout after seeing the assessment, the defects, and the corrected deviation
number.

## Evidence

All 11 acceptance criteria met. Verified twice: once by the implementing session
and once independently by the `tcw-verifier` agent, which re-ran both checks
itself rather than reading them out of `outcome.md`.

| Criterion | Evidence |
|---|---|
| 1 — `Produce` names optional `## References` with a reason per entry | `stage-request.md:28-30` |
| 2 — solicit step, marked, correctly placed | new step 3 at `:39-44`, between step 2 (`:36`) and step 4 (`:45`); marker `[judgment]` |
| 3 — capture-only, context-not-directive, empty case in `## Notes` | all three at `:41-43`, plus six concrete things to ask about at `:39-40` |
| 4 — `stage-spec.md` `Inputs` names the section, keeps `initial-request.md` | `stage-spec.md:10-13`; `test_inputs_names_every_artifact_the_table_lists[spec]` green |
| 5 — code-reading step reads references first | `stage-spec.md:40-41` |
| 6 — inbox carries links through, no prompt; `Produce` phrase intact | `stage-inbox.md:44-47`; "**No lifecycle artifact**" verbatim at `:24` |
| 7 — nothing under `tcw/` | `git diff --name-only` over the item's range: 3 skill docs, 2 `upcoming.md`, 1 capability body, the item folder |
| 8 — suite green | `pytest` **1095 passed**, exit 0, twice: after implementation and again after the defect fixes |
| 9 — `tcw validate` zero | `validate OK` |
| 10 — changelog and release notes | `docs/changelogs/upcoming.md` **Changed** block; `docs/release-notes/upcoming.md` plain-language entry |
| 11 — `capabilities.yaml` + ledger body | `changed: plugin/work-lifecycle` in the sidecar; body sentence added at closeout (`ecc3d6f`) |

The four checks no test can make were confirmed by reading: the step is
answerable, correctly placed, `stage-spec.md` points at the section from its first
`Inputs` line, and this item's own `## References` (four entries) matches the
finished `Produce` wording without drift.

## What verification changed

Verification was not a formality here — it found three gaps in the new prose that
no test could catch, all fixed before acceptance (`eb9cd9a`, detailed in
`outcome.md`):

1. `stage-spec.md` step 3 used "references" in two senses in one sentence.
2. The "asked; none provided" empty-case marker had no reader — the rationale
   `stage-request.md` gives for writing it was inert as shipped. `stage-spec.md`
   `Inputs` now states what the absence of both signals means.
3. The inbox carry-through path — the one path that writes `## References` without
   reading `stage-request.md` — never inherited the annotation requirement.

Defect 2 is the one worth remembering: the spec booked the empty case as a risk at
the *writing* end (`spec.md:201-207`) and never noticed the *reading* end was
missing. A spec can pass its own acceptance criteria while leaving a mechanism
half-built, because the criteria were written from the same blind spot.

## Deviation from plan

One, disclosed and corrected: `stage-request.md` grew **+10 lines (55 → 65)**
against an allotted six. The plan said to tighten rather than accept overage; the
implementation tightened once (66 → 65) and then revised the estimate instead —
the branch the plan told it not to take. Accepted: 10 lines on a hot-path document
is small, and the three clauses criterion 3 mandates do not compress much further.

The "56 lines today" baseline in `spec.md:217` and `plan.md:42` was itself off by
one; `outcome.md` initially inherited the error and reports the corrected figure
now. **The next addition to this document is measured against 65 lines, not 56** —
the spec's own escalation threshold ("a second addition of this size would justify
looking at the document's shape") is untouched but nearer than the planning
artifacts imply.

## Deferred follow-ups

None created. Two options stay recorded in `spec.md` Risks rather than becoming
items, because neither has evidence of being needed yet:

- **Always-present `## References` with an explicit "None provided"** if the
  optional-section-plus-`Notes` convention proves unreliable. A one-line change to
  `Produce` when and if that shows up.
- **Link-rot detection** — out of scope by choice, not deferred by accident.

Also noted, not actioned: the dogfooding example's four entries are all in-repo
paths, so the worked example never exercises the "bare URLs save it nothing"
caution against an external link. Harmless; worth knowing the example is
one-sided if someone later edits that wording.

## Closeout choices

- **Route:** direct to `main`, matching this item's own planning commits. No PR.
- **Documentation:** complete at `implement` per the lifecycle's documentation
  gate. `README.md` and `skills/tcw-work/SKILL.md` were evaluated against the
  finished diff and confirmed not to fire.
- **Capabilities:** `plugin/work-lifecycle` body updated at closeout; status stays
  `Supported`. `tcw capabilities check` and `tcw validate` both clean.
- **Version:** patch, chosen by the user in advance of verification.
- **Post-mortem:** not run. Verification found three prose defects and one
  documented deviation — real, but ordinary stage-level findings rather than the
  serious unforeseen problems that warrant one. Defect 2 is the only candidate,
  and it is recorded above where the next reader of this item will find it.
