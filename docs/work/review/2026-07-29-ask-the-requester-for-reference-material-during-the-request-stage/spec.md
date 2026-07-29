# Spec: ask the requester for reference material during the request stage

## Capability changes

**Changed:** [`plugin/work-lifecycle`](../../../capabilities/plugin/work-lifecycle/)
("Plan and drive work items", `cap-556620`, `Supported`) — its description says
the agent "records the lifecycle artifacts in the work item folder"; after this
change the `request` stage also asks the requester for reference material, which
is a new question the user is asked during planning. One sentence is added to the
capability body at completion. No status change (it is already `Supported`).

**New:** none. **Removed:** none.

No taxonomy delta: the change introduces no new noun and no new Feature. The
existing Features behind `plugin/work-lifecycle` cover it.

Recorded in this item's `capabilities.yaml` under `changed:`.

## Problem

The `request` stage exists to "capture intent that would otherwise be lost
between a conversation and a spec"
(`skills/tcw-work/references/stage-request.md:5-7`). It captures the ask but not
the *sources*. Its `Steps` are: honor bindings, ask the user what is unclear,
write the request, record constraints and out-of-scope, commit
(`stage-request.md:28-40`). Nothing asks the requester what material they were
reading when they formed the request.

`Produce` bounds the artifact to a title, the request body, and an optional
`## Notes` (`stage-request.md:16-26`) — so reference links survive today only if
the author happens to write them into a sentence. They often do:
`docs/work/completed/2026-07-29-close-the-originating-github-issue-when-a-work-item-completes/initial-request.md`
carries four inline links written that way. The behavior exists as a habit with
no place to live.

Downstream, `spec` is the stage that does the research — "a spec written without
reading the code it changes is a guess" (`stage-spec.md:12-14`) — and its
`Inputs` name only `initial-request.md` (`stage-spec.md:9-14`). So the stage best
positioned to use the requester's sources is not told they exist, and re-finds
material the requester already had open.

The requester is present at exactly one moment in the lifecycle: the `request`
stage, which is "not delegable to a subagent for exactly this reason"
(`stage-request.md:32-34`). That is the only place the question can be asked.

## Goals

1. An agent running the `request` stage asks the requester what reference
   material applies to the task.
2. The answer is recorded in `initial-request.md` in a bounded, named place.
3. An agent running the `spec` stage is told that place exists and starts its
   research there.
4. A raw inbox entry that already carries links or attachments does not lose them
   when `tcw work inbox accept` turns it into an item.
5. Codex and Claude get identical behavior.

## Non-goals

- **No CLI surface.** No `tcw work references` command, no new field on the work
  model, no section validation.
- **No fetching, validating, or summarizing** references at `request` time. Deeper
  research is `spec`'s job; pre-empting it "hides the alternatives"
  (`stage-request.md:35-36`).
- **No link-rot detection**, now or as a follow-up hook.
- **No attachments-folder convention** for reference material. Inbox entries may
  already be folders with attachments (`stage-inbox.md:16-17`); this item carries
  those through, it does not standardize them.
- **No prompting at the `spec` stage.** Re-interviewing the user is the thing the
  `request` stage exists to prevent (`stage-request.md:44-45`).
- **No `## References` in any other stage artifact** (`spec.md`, `plan.md`, …).

## Design

Three skill-document edits. No Python changes — see *Why no CLI change* below.

### 1. `stage-request.md` — produce and solicit the section

**`Produce`** gains an optional section alongside `## Notes`:

> Optional `## References`: reference material the requester considers relevant —
> a link, a repo path, or another work item — each with a one-line note on *why*
> it matters. The `spec` stage reads this; a bare list of URLs with no reason
> attached saves it nothing.

**`Steps`** gains one step immediately after the existing step 2 ("Ask the user
what is unclear"), pushing the current steps 3–5 down by one:

> 3. **Ask the requester for reference material.** What were they reading — docs,
>    a spec, an issue, prior art, a file in this repo, a related work item?
>    Record link plus one-line reason; do not fetch, validate, or summarize them
>    here. A link is context for the `spec` stage, not a decision it must accept.
>    If they have none, say so in `## Notes` ("asked; none provided") so `spec`
>    can tell that apart from a stage that never asked.
>    — agent `[judgment]`

The step sits **after** "ask what is unclear" deliberately: the requester's
sources are most useful once the ask itself is settled, and asking for links
first invites a link dump in place of a request.

**`Exit` / Well** is amended so that the bar becomes: the `spec` stage can start
without re-interviewing anyone *or re-finding the requester's sources*.

The marker is `[judgment]`, not `[prompted]` — nothing in the tool enforces it.
That is honest rather than aspirational; see Risks.

### 2. `stage-spec.md` — consume it

**`Inputs`** becomes:

> `initial-request.md`, including its `## References` section when present — the
> starting set for research, not the limit of it.

**Step 3** ("Read the code the change touches and record what is actually true")
gains a leading clause: read the request's references before hunting for sources
independently.

`Inputs` must keep naming the literal string `initial-request.md`, which
`tests/test_skill_lifecycle_parity.py:96-104` asserts against
`LIFECYCLE_STEPS[spec].inputs`. The wording above does.

### 3. `stage-inbox.md` — carry links through, do not ask

The `inbox` stage produces "**No lifecycle artifact**" (`stage-inbox.md:22-26`);
`tcw work inbox accept` writes `initial-request.md` from the entry's own text. So
the edit is carry-through, added as a clause on the existing step 6 (`tcw work
edit` / post-accept tidying):

> If the entry carried links or attachments, make sure they survived into the
> item — collect them under `## References` rather than leaving them buried in
> pasted text. Do **not** ask for more here: the requester is usually a GitHub
> issue reporter or another node and is not present. The `request` stage asks.

### Why no CLI change

The harness rule sends anything that must be *guaranteed* into the `tcw` CLI, so
the absence of a CLI change needs its reason stated:

- `LIFECYCLE_STEPS` (`tcw/store/base.py:593-609`) is the machine-readable source
  of truth for each stage's objective, inputs, and output — but `inputs` is a
  tuple of **artifact filenames**, not sections. `spec` already declares
  `inputs=("initial-request.md",)`, and `## References` lives inside that file,
  so the table is already correct and needs no edit.
- Nothing in the CLI reads artifact *contents*: `initial-request.md` appears in
  `tcw/work/cli.py:296-305` only as the board's presence marker `"R"`. Teaching
  it to require a section would be new machinery for a section that is optional
  by design.
- The behavior being added is *asking a human a question*, which no CLI can do.
  The right layer for it is the stage document, which both harnesses read
  identically — so the Codex/Claude parity goal is satisfied by construction.

`skills/tcw-work/SKILL.md` names artifacts, never their sections
(`SKILL.md:30,43`), so the router needs no change and its 60-line budget
(`tests/test_skill_lifecycle_parity.py:184-192`) is not at risk.

### Documentation Sync

- `docs/changelogs/upcoming.md` — Changed: the three stage documents.
- `docs/release-notes/upcoming.md` — plain-language note that planning now asks
  for reference material.
- `skills/tcw-work/SKILL.md` — no change (reasoned above). The skill *is* the
  deliverable here, so the "always update the matching skill" trigger is
  satisfied by the work itself.

## Acceptance criteria

1. `stage-request.md`'s `Produce` section names an optional `## References`
   section and states that each entry carries a one-line reason.
2. `stage-request.md`'s `Steps` contains a step that asks the requester for
   reference material, carries a recognized enforcement marker, and sits after
   the "ask the user what is unclear" step and before the "write the request"
   step.
3. That step states all three of: capture-only (no fetch/validate/summarize),
   links are context rather than directives, and the empty case is recorded in
   `## Notes`.
4. `stage-spec.md`'s `Inputs` section mentions `## References` and still contains
   the literal string `initial-request.md`.
5. `stage-spec.md`'s step that reads the code also directs the agent to read the
   request's references first.
6. `stage-inbox.md` tells the agent to carry an entry's existing links or
   attachments into the item's `## References`, and explicitly says not to prompt
   for more at that stage.
7. No file under `tcw/` is modified by this item.
8. `pytest` passes, in particular every test in
   `tests/test_skill_lifecycle_parity.py` (five sections still in order, every
   step marked, no unknown markers, `Inputs`/`Produce` still naming their
   artifacts, SKILL.md within budget).
9. `tcw validate` exits zero.
10. `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` each carry
    an entry for this change.
11. `capabilities.yaml` lists `plugin/work-lifecycle` under `changed:`, and that
    capability's `description.md` gains a sentence covering the new question at
    completion time.

## Risks

- **Nothing enforces the new step.** It is `[judgment]`, like every other step in
  the stage. An agent in a hurry skips it and no test fails. Accepted: the
  alternative is CLI machinery for an optional prose section, which the
  Non-goals rule out. The mitigation is placement — a numbered step in the
  stage's own document is the strongest available signal short of a gate.
- **The empty case is the weak link.** "Omit the section, note it in `## Notes`"
  (the user's choice) means a `spec`-stage agent can only distinguish "asked,
  none" from "never asked" if the `Notes` line was actually written — by the same
  judgment that might have skipped the question. If this proves unreliable in
  practice, the fallback is to make `## References` always-present with an
  explicit "None provided"; that is a one-line change to `Produce` later, so
  nothing here forecloses it.
- **Link dumping.** A requester given a place to put links may put links there
  instead of writing the request, or may attach a link that implies a solution —
  exactly what `stage-request.md:35-36` warns against. Mitigated by ordering the
  step after the ask is settled, and by the "context, not directives" clause.
- **Reference rot.** Recorded links go stale and nothing notices. Out of scope by
  choice; the annotation ("why it matters") is what keeps a dead link partly
  useful.
- **Prose creep in a hot path.** `stage-request.md` is loaded on every planning
  run, so every added line is a recurring cost. This adds roughly six lines to a
  56-line document. Acceptable; a second addition of this size would justify
  looking at the document's shape instead.

## Notes

`tcw work lifecycle --stage request` currently reports only the objective and
`produces: initial-request.md` — no bindings — so there is no hook to honor and
none to add.

`tcw capabilities check` passes on the tree as it stands, checked before writing
this spec.
