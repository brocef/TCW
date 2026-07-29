# Outcome: ask the requester for reference material during the request stage

Shipped as planned: three stage-document edits and the documentation block. No
Python changed, no CLI surface moved, no test was added or modified. The plan
survived contact with one exception, recorded below.

## What shipped

### 1. `stage-request.md` — produce and solicit `## References` (`dd53df2`)

`Produce` gained the optional `## References` section (a link, repo path, or work
item per entry, each with a one-line *why it matters*, and the reason the
annotation is required). `Steps` gained step 3, between "ask the user what is
unclear" and "write the request", renumbering 3–5 → 4–6; it carries all three
required clauses — capture-only, links-as-context-not-directives, and the empty
case in `## Notes`. `Exit`/**Well** now reads "…without re-interviewing anyone or
re-finding the requester's sources."

### 2. `stage-spec.md` — consume the section (`18818ab`)

`Inputs` became "`initial-request.md`, including its `## References` section when
present — the starting set for research, not the limit of it." Step 3 now reads
the request's references first, then the code.

### 3. `stage-inbox.md` — carry existing links through (`d7be331`)

Step 6 (post-accept tidying) gained the carry-through clause and the explicit
"do **not** ask for more here" with its reason. `Produce` still says "**No
lifecycle artifact**" verbatim.

### 4–7. Documentation Sync (`27e638c`)

`docs/changelogs/upcoming.md` under **Changed** — the three documents, what each
gained, and the reasoned absence of a CLI change. `docs/release-notes/upcoming.md`
under **Changed** — one plain-language entry, no section or module names.

`README.md` and `skills/tcw-work/SKILL.md` were evaluated against the finished
diff and confirmed **not** to fire, as the plan predicted: the README's seeding
description (`:684-686`) and `tcw-work` bullet (`:847-856`) both remain true, and
the router names artifacts, never their sections. No edit to either.

## Test result

`pytest` — **1095 passed** (154s), including all 71 tests in
`tests/test_skill_lifecycle_parity.py`. `tcw validate` — **validate OK**.
`git diff --stat` against the pre-implementation commit shows only the three
skill documents, the two `upcoming.md` files, and this item's own folder — **no
file under `tcw/`** (acceptance criterion 7).

The four checks the plan flagged as un-testable were confirmed by reading:

1. **Answerable.** The step names six concrete things to ask about and states the
   fetch prohibition in its own clause.
2. **Placement.** Step 3 sits between step 2 and step 4 as specified — nothing
   enforces this, so it was read rather than asserted.
3. **`stage-spec.md` points at the section.** A cold reader learns from the first
   line of `Inputs` that references may exist.
4. **Dogfooding.** This item's own `initial-request.md` `## References` — five
   entries, each a repo-path link plus a one-line reason — matches the finished
   `Produce` wording without adjustment. The worked example and the instruction
   did not drift.

## Where the plan was wrong

**The line budget.** The plan allotted `stage-request.md` "roughly six more
lines" and instructed tightening rather than acceptance if the edit ran
materially past it. The first draft came in at +10 (56 → 66). Tightening the
`Produce` paragraph from four lines to three and the step from six long lines to
six shorter ones brought it to **+9 (56 → 65)** — still three over the estimate,
and that is where it stayed.

Correcting the estimate rather than the prose: the three clauses acceptance
criterion 3 requires are not compressible below about five lines while staying
readable, and `Produce` needs three to explain why the annotation exists. Six was
optimistic for what the spec itself mandated. The spec's own risk note ("a second
addition of this size would justify looking at the document's shape") is the
right threshold and this change does not cross it — but the next one should be
measured against 65 lines, not 56.

No other plan claim failed. Every file, line reference, and guard test the plan
named was accurate.

## Notes

`tcw work lifecycle --stage implement` reported no bindings, as the spec
anticipated for `request`.

Still outstanding for `complete`, per the plan and acceptance criterion 11: the
one-sentence body edit to
`docs/capabilities/plugin/work-lifecycle/description.md` covering the new
question. `capabilities.yaml` already lists it under `changed:`, and the
capability stays `Supported`, so the completion gate will not catch it if
forgotten — criterion 11 is the only guard.
