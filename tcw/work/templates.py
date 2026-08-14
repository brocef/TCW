"""TCW's built-in artifact templates — the starting point `tcw work scaffold`
writes when a project has bound no template of its own.

A plain module-level map rather than package data: there is exactly one
definition of each template, no wheel work, and nothing to go missing from an
install. Each skeleton is derived from the matching stage document's `Produce`
section (`skills/tcw-work/references/stage-*.md`), so the built-in asks for what
the lifecycle already asks for.

**These are drafts, never documents.** `scaffold` writes `<artifact>.draft.md`;
the stage writes the artifact.
"""

# `intake` is empty on purpose: intake is whatever someone supplied, so it has no
# prescribed structure. Scaffolding it gives you an empty file to type into
# rather than headings that would misrepresent it. Asserted empty by the tests so
# nobody helpfully adds sections later.
_INTAKE = ""

_INITIAL_REQUEST = """\
# <Title>

_What is being asked for, and why. Enough that someone resuming cold knows what
was wanted. For an epic, the coordination goal too._

## Notes

_Optional: anything worth keeping that has no home in the request itself._

## References

_Optional: a link, a repo path, or another work item — each with a one-line why
it matters. A bare URL with no reason attached saves the spec stage nothing._
"""

_SPEC = """\
# Spec — <Title>

## Capability changes

_Planned ledger deltas only — new, changed, removed, or none. No records are
written here._

## Problem

_What is wrong today, grounded in the code with file and line. A claim recalled
rather than checked is how a spec starts lying._

## Goals

## Non-goals

## Design

_For an epic, replace this with the child boundaries and their ordering
constraints._

## Acceptance criteria

_Each one checkable by someone else without asking what it meant._

## Risks

## Notes

_Optional._
"""

_PLAN = """\
# Plan — <Title>

## Tasks

_Ordered. Each says what it changes and how it is verified._

### 1. <task>

## Documentation Sync

_One named task per entry in the project's Documentation Sync section whose
trigger will fire. If none fires, say so and why._

## Verification

_What the suite cannot check, and someone has to look at._

## Notes

_Optional._
"""

_OUTCOME = """\
# Outcome — <Title>

## What shipped

_Task by task, with commit references._

## Tests

_The actual result, pasted. No completion claim without fresh output._

## Corrections

_Anything the plan or spec got wrong, corrected in place, with the correction
recorded here. Finding one is a success, not a problem._

## Notes

_Optional._
"""

_REFINED_OUTCOME = """\
# Refined outcome — <Title>

_Accepted. This artifact is the verdict; never write it beside a `rework.md`._

## Decision

## Evidence

_What was checked, and what it showed._

## Deferred follow-ups

## Closeout choices

_Version, documentation, capability, and merge decisions taken at completion._

## Notes

_Optional._
"""

_REWORK = """\
# Rework — <Title>

_Rejected. This artifact is the verdict; delete `refined-outcome.md` if one
exists, because it asserts the work was verified._

## What is still required

_Each item concrete enough to implement without asking a question._

## Notes

_Optional._
"""

_POST_MORTEM = """\
# Post-mortem — <Title>

## What went wrong

## Which stage could first have caught it

## What would have had to be different

## Is that change worth making

_A post-mortem that recommends "be more careful" has not finished._

## Notes

_Optional._
"""

# One entry for every `WORK_ARTIFACTS` name — asserted as exact set equality, so
# a new artifact cannot ship without a template.
ARTIFACT_TEMPLATES: dict[str, str] = {
    "initial-request": _INITIAL_REQUEST,
    "spec": _SPEC,
    "plan": _PLAN,
    "outcome": _OUTCOME,
    "refined-outcome": _REFINED_OUTCOME,
    "rework": _REWORK,
    "post-mortem": _POST_MORTEM,
    "intake": _INTAKE,
}
