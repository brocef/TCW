# Spec: separate lifecycle stage information from stage prompts

## Capability changes

**Changed:** `work/run-a-lifecycle-stage` (`cap-f42255`, currently `Supported`).

Its description states two things this work makes untrue:

- "TCW ships defaults for the six lifecycle stages that run against an existing
  item … `inbox` has none: it runs before an item exists."
- "`tcw work stage inbox` is refused too, and says why: `inbox` runs before an
  item exists, so there is no item to resolve a stage against."

After this work TCW ships defaults for **all seven** stages, and
`tcw work stage inbox` succeeds — taking no work item reference, because there
is still no item at that point. The capability stays `Supported`; its
description is rewritten at completion. No new capability is declared: the user
is doing the same thing, over a wider set of stages.

Contradiction check run against the standing ledger: `tcw capabilities check`
exits 0 on the tree as it stands. `work/manage-the-work-inbox` (`cap-e3d385`)
covers `tcw work inbox list | show | accept | path` and says nothing about
`tcw work stage`, so it is unaffected. No other capability mentions the stage
verb.

No taxonomy change. The relevant Feature, `configurable-work-lifecycle`, is
already registered and already linked from the capability; `lifecycle-stage` is
already a registered term under `work-item`.

## Problem

Three separate problems, all in how the `tcw-work` skill presents the lifecycle.

**1. `stage-inbox.md` is genuinely doing two jobs.** Six of the seven stage
documents are already short pointers over a prompt the command line tool prints;
that split shipped in v1.0.0 and `tests/test_skill_lifecycle_parity.py` enforces
it. `inbox` is the exception. `tcw/work/resolve.py:65` builds the shipped prompt
set as `sorted(set(STAGE_IDS) - {"inbox"})`, so no prompt ships for it;
`tcw/store/base.py:954` gives it an empty legal-status tuple, and
`tcw/work/cli.py:785-790` turns that emptiness into a refusal. With nowhere else
to put it, the whole inbox methodology lives in
`skills/tcw-work/references/stage-inbox.md`, which is 70 lines against a 40-line
ceiling every other stage document meets.

That is not only untidy. `docs/lifecycle/harness.md`, bound to this stage, says
**anything that must be guaranteed belongs in the `tcw` CLI**, because the CLI
behaves identically under Claude and Codex while a skill only reaches users who
installed the plugin. Today a user who installed `tcw` from PyPI and asked
"what do I do with this inbox entry?" gets an error message. The inbox judgment
— one item or several, how to title it, when to refuse an entry outright — is
guaranteed to nobody.

**2. The pointer wording is vague.** Each of the six routers says
"`tcw work stage <id> <slug>` prints the methodology; this document carries only
what the CLI cannot." That describes the division of labour to someone who
already understands it. It does not instruct. An agent reading it has to infer
that running the command is a step it must take.

**3. `references/` is a flat folder of seventeen files** with no grouping, mixing
per-stage documents, command reference, tag vocabulary, hook configuration, and
standalone procedures. Nothing signals which of them a reader needs at a stage
and which are read on demand.

There is also a fourth thing, reported to the requester and settled in
`initial-request.md`: the built-in prompts cannot move into the skill.
`load_builtins()` reads them out of the installed Python package via
`importlib.resources`, and `pyproject.toml:24-29` ships `tcw*` packages plus
`"tcw.work" = ["prompts/*.md"]` and nothing else. `skills/` reaches users
through the plugin, a different channel. Moving the prompts would leave every
PyPI-only install with no default instructions at all.

## Goals

1. Every one of the seven lifecycle stages gets its instructions from
   `tcw work stage`, so a user with the CLI and no plugin is never told to go
   read a document they do not have.
2. Every stage document states, as an instruction rather than a description,
   that the way to get the instructions is to run the command.
3. `references/` is grouped so a reader can tell a per-stage document from a
   procedure at a glance.
4. A reader of the skill can find the built-in prompts and understand which
   source of instructions beats which, without being sent to a file that does
   not exist.
5. Nothing that reaches a user through either the CLI or the plugin regresses:
   no dangling link, no test relaxed to accommodate a move.

## Non-goals

- **Moving `tcw/work/prompts/*.md`.** Settled above; they stay where the
  installed package reads them.
- **Rewriting the six existing prompts.** Their content is out of scope; only
  the new `inbox` prompt is authored here.
- **Changing what the `inbox` stage means.** The judgment moving into the prompt
  is the judgment already written in `stage-inbox.md`, condensed to fit the
  prompt ceiling — not a new policy on how intake works.
- **Letting `tcw work stage inbox` take a work item reference.** There is no item
  at that point. A stray argument is refused, not interpreted.
- **Reorganizing any other skill's `references/`.** `documentation-sync`,
  `tcw-capabilities`, `tcw-plugin`, and `tcw-taxonomy` each have one, and they
  are not part of this item.
- **Relaxing the router ceiling, the prompt ceiling, or the `SKILL.md` line
  budget.** If the new material does not fit, it gets cut, not the limit.

## Design

### A. Ship a built-in `inbox` prompt

`tcw/work/prompts/inbox.md` is added, and `inbox` stops being excluded from the
shipped set at `tcw/work/resolve.py:65`. The set becomes `set(STAGE_IDS)` plain,
which keeps the property the existing comment claims: a stage added without a
prompt file fails at load rather than shipping a stage that says nothing.

Making the command accept it needs three small changes, and the shape of them
matters more than the size:

- `STAGE_STATUSES["inbox"]` at `tcw/store/base.py:954` stays `()`. It is a true
  statement — no work-item status is legal for a stage that runs before an item
  exists — and it is what the whole "is this stage legal here" check is written
  against. The `inbox` branch is decided **before** that check, by stage id, not
  by re-interpreting an empty tuple as "any status".
- `pstg.add_argument("slug")` at `tcw/work/cli.py:1455` becomes
  `nargs="?"`. `_stage` then requires a reference for the other six and refuses
  one for `inbox`, each with its own message. Argparse cannot express
  "required for six values of another positional", so the check belongs in the
  handler.
- The `inbox` path resolves the store with the existing `_store()` helper
  (`tcw/work/cli.py:91`) instead of `_resolve()`, and calls `resolve_prompts`
  with `item=None`. That signature already accepts `WorkItem | None`, and
  `Condition.matches` at `tcw/store/base.py:647-655` already answers "no item
  never matches" — so a project's `when:`-conditioned inbox binding correctly
  does not fire, rather than firing on nothing.

**Abstraction litmus test.** The operation is "given a stage id and no item,
resolve and print this project's instructions for that stage". A non-filesystem
store implements it the same way it implements the other six: it is a read of
lifecycle configuration plus shipped text, with no item lookup at all — strictly
less store surface than the existing path, not more. It passes.

**Harness test.** This is the point of the change: the guarantee moves from a
plugin document into the CLI, which reads identically under Claude and Codex.

### B. `references/` layout

```
skills/tcw-work/references/
  commands.md            unchanged location
  tags.md                unchanged location
  transitions.md         unchanged location
  hooks.md               unchanged location
  epic-deltas.md         unchanged location
  cross-node-deltas.md   unchanged location
  lifecycle/
    stage-inbox.md       moved
    stage-request.md     moved
    stage-spec.md        moved
    stage-plan.md        moved
    stage-implement.md   moved
    stage-verify.md      moved
    stage-postmortem.md  moved
    default/
      README.md          new
  procedures/
    decompose.md         moved
    delegation.md        moved
    audit-backlog.md     moved
    consolidate-plans.md moved
```

Files move with `git mv` so history follows them. Every inbound link is
rewritten; the full inbound set is enumerated under *Acceptance criteria*.

`references/lifecycle/default/README.md` is the discoverability note. It states
where the built-in prompts actually live (`tcw/work/prompts/*.md` inside the
installed package), why they live there rather than here (packaging — a
PyPI-only install must still have them), how to read one without a checkout
(`tcw work stage <id> <ref>`), and the order that decides which text wins: a
project's `prompt:` bindings replace the built-in outright, and `builtin: true`
in that list puts it back, composed in declaration order. It points at
`../../hooks.md` for the binding shapes rather than restating them.

### C. Pointer wording

Each of the seven stage documents carries, in its `Purpose` section, the
sentence the requester asked for:

> Get your instructions on how to produce the output by running
> `tcw work stage <id> <slug>`.

— with no `<slug>` for `inbox`, which takes none. The half-sentence it replaces
("prints the methodology; this document carries only what the CLI cannot") is
dropped; what that clause was explaining is stated once, in `SKILL.md`, rather
than seven times.

This sentence is fifteen words and will appear verbatim in seven documents.
`test_no_router_sentence_appears_in_its_prompt` compares each router only
against **its own** prompt, so seven routers sharing a sentence with each other
is not a violation — and none of the prompts contains it. The check that
matters, `test_every_stage_document_names_the_harness_neutral_binding_command`,
looks for `tcw work stage <id>` and is satisfied by construction. Its `inbox`
branch, which currently expects `tcw work lifecycle`, is removed.

### D. `stage-inbox.md` becomes a router

The methodology in the current 70-line document is the source for the new
prompt. What stays behind in the router is what the CLI cannot say: that the
stage is **not delegable** because it is interactive (`procedures/delegation.md`
already records this), the `[gated]` / `[judgment]` markers, and the
cross-references to the plugin-only siblings — `tcw-triage-issues`, which reuses
this judgment for GitHub issues, and `procedures/decompose.md`.

The router drops its `Exit` section, matching the other six: "how this stage
ends badly" is redirect material and belongs in the prompt. Its `Produce`
section keeps the words "no lifecycle artifact", which
`test_a_stage_producing_nothing_says_so_explicitly` reads.

### E. Tests that move with the code

Not incidental — three of them encode the old layout as fact, and each needs a
deliberate decision rather than a path substitution.

`tests/test_skill_lifecycle_parity.py`:

- `stage_doc()` resolves under `REFS / "lifecycle"`.
- `test_no_stage_document_exists_for_an_unknown_id` globs
  `REFS / "lifecycle"`.
- `ROUTER_IDS` becomes all of `STAGE_IDS`; the `!= "inbox"` exclusion goes, and
  so does the module comment explaining it.
- `test_every_stage_document_has_the_sections_in_order` loses its `inbox`
  branch — all seven are four-section routers now.
- `test_every_stage_document_names_the_harness_neutral_binding_command` loses
  its `inbox` branch.
- `test_no_reference_filename_carries_an_ordinal` and
  `test_the_router_routes_to_every_reference_file` switch from `glob` to
  `rglob`, and the latter matches on the path relative to `references/` so that
  a link written as `references/lifecycle/stage-spec.md` counts as reaching it.

`tests/test_shipped_prompts.py`: `SHIPPED` becomes `set(STAGE_IDS)`, and
`test_every_stage_but_inbox_ships_a_prompt` is renamed and inverted to assert
that every stage ships one.

`tests/test_stage_verb.py`: `test_inbox_is_rejected_with_its_reason` and
`test_inbox_still_ships_no_prompt` are **replaced**, not deleted — by tests that
`tcw work stage inbox` with no argument exits 0 and prints the prompt on stdout,
and that `tcw work stage inbox <slug>` is refused with a message saying the
stage takes no work item. `test_each_row_is_what_the_lifecycle_contract_says`
keeps `"inbox": ()` and gains a comment saying the empty tuple no longer implies
a refusal.

`tests/test_documentation_sync_wiring.py:41-42`: the two `LIFECYCLE_REFS` paths
gain `lifecycle/`.

### F. `SKILL.md` is at exactly its 60-line body budget

Measured, not assumed. Rewriting links to longer paths costs no lines. The one
new reachable file, `lifecycle/default/README.md`, must be named somewhere in
`SKILL.md` or `test_the_router_routes_to_every_reference_file` fails. It is
folded into the existing `tcw work stage` bullet under `## Always`, which
already ends in a pointer to `hooks.md` — an inline addition, not a new line.
If any of this pushes the body over 60, the rule the test states applies:
extract, never grow.

## Acceptance criteria

1. `pytest -q` passes with no test skipped, deleted, or weakened. A test whose
   assertion is inverted (the two named in §E) has a replacement asserting the
   new behavior.
2. `tcw work stage inbox`, run in this repository with no further arguments,
   exits 0 and prints the inbox instructions on stdout with stderr empty.
3. `tcw work stage inbox <any-slug>` exits 1, prints nothing on stdout, and
   prints a message on stderr saying the `inbox` stage takes no work item.
4. `tcw work stage spec <slug>` still exits 0 and prints the same text it prints
   before this change, for an item in `backlog`.
5. `python -c "from tcw.work.resolve import load_builtins;
   print(sorted(load_builtins().stage_prompts))"` lists all seven stage ids.
6. `tcw/work/prompts/inbox.md` is at most 50 lines and has at least 15 non-blank
   lines — the bounds `tests/test_shipped_prompts.py` already applies to the
   other six.
7. Every file in `skills/tcw-work/references/lifecycle/` is at most 40 lines,
   `stage-inbox.md` included.
8. Each of the seven documents in `references/lifecycle/` contains the literal
   string "Get your instructions on how to produce the output by running".
9. `git log --follow` on each moved file reaches commits from before this item,
   confirming the moves were `git mv` and not delete-plus-create.
10. `skills/tcw-work/references/lifecycle/default/README.md` exists, names the
    path `tcw/work/prompts/`, and does not reproduce the body of any prompt.
11. No file tracked by git outside `docs/work/`, `docs/changelogs/`, and
    `docs/release-notes/` contains a link to `references/stage-`,
    `references/decompose.md`, `references/delegation.md`,
    `references/audit-backlog.md`, or `references/consolidate-plans.md`.
    Verified with:
    `git grep -n -e 'references/stage-' -e 'references/decompose.md' -e 'references/delegation.md' -e 'references/audit-backlog.md' -e 'references/consolidate-plans.md' -- . ':!docs/work' ':!docs/changelogs' ':!docs/release-notes'`
    — which must print nothing. The three excluded trees are archives: a
    changelog naming a path that existed when it was written is a true
    historical statement, and the existing
    `test_no_reference_to_a_deleted_document_survives` excludes them for the
    same reason.
12. The known inbound links, all rewritten: `skills/tcw-work/SKILL.md` (7 stage
    rows plus the `## Read on demand` list), `skills/tcw-post-mortem/SKILL.md`
    (2), `skills/tcw-triage-issues/SKILL.md` (3),
    `skills/documentation-sync/SKILL.md` (3), `skills/tcw-plugin/SKILL.md` (1),
    `agents/tcw-verifier.md` (1), `commands/tcw-verify-work.md` (1),
    `commands/tcw-plan-work.md` (3), `commands/tcw-drive-work-to-completion.md`
    (1), `commands/tcw-triage-issues.md` (1), `commands/tcw-process-inbox.md`
    (2), and the two test paths in `tests/test_documentation_sync_wiring.py`.
    Criterion 11 is the check; this list is what to edit.
13. `tcw validate` exits 0.
14. `tcw capabilities check` exits 0.
15. The `work/run-a-lifecycle-stage` description no longer says
    `tcw work stage inbox` is refused, and no longer says TCW ships defaults for
    six stages. (Written at completion, per the capability lifecycle — declared
    here so `plan` schedules it.)
16. `skills/tcw-work/SKILL.md` body is at most 60 lines.

## Risks

**The `inbox` prompt loses judgment on the way through the 50-line ceiling.**
The source is 70 lines and the destination is 50, and roughly 15 of the source's
lines are router material that stays behind — so it is close, but not free. The
risk is that a real rule (refuse a duplicate entry; do not invent scope for a
vague one) gets cut as filler. Mitigation: the condensation is reviewed against
the original document side by side before the old one is overwritten, and the
`Exit badly` branches are treated as content to preserve, not trimming stock.

**A sibling defect sweep was scoped deliberately, not inherited.** The requester
named the `tcw-work` skill. Four other skills have a `references/` folder with
the same flat shape, and `tcw-capabilities`' is the largest. None of them has
the specific defect this item fixes — none has a document doing double duty with
a CLI-shipped prompt, because none of them has CLI-shipped prompts at all. They
are excluded as a non-goal on that basis rather than by inheriting the
requester's scope. The one sweep that *is* repo-wide is criterion 11: the link
check runs over the whole tree, not over the files the plan happens to name.

**`git mv` history is easy to lose.** Rewriting a moved file's contents in the
same commit as the move can defeat rename detection. Mitigation: criterion 9,
and moving before editing.

**Changing argument handling on a command with a machine-readable contract.**
`tcw work stage` promises stdout carries the prompt and nothing else, and that
any failure prints nothing on stdout. The `inbox` branch is a new early path
through `_stage` and could violate that. Criteria 2 and 3 check both directions
explicitly.

**Driving `tcw work` while `tcw work` is being edited.** This item changes
`tcw/work/cli.py` and `tcw/work/resolve.py` against an editable install, so the
CLI used to run the lifecycle is the code under change. Recorded here so `plan`
sequences the status transitions clear of the edits rather than interleaving
them.

## Notes

Two things in this spec are inference rather than something read off the tree,
and are marked as such:

- That folding the `default/README.md` pointer into the existing `## Always`
  bullet keeps `SKILL.md` at 60 lines. The budget is measured (it is exactly 60
  now) but the rewrite is not written yet.
- That the inbox methodology condenses to 50 lines without losing a rule. The
  arithmetic is above; whether it holds is a `plan`-stage question, and the
  first risk is the fallback if it does not.
