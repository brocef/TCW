# Spec: commands-pause-work

## Capability changes

Planned deltas only; nothing is written to the ledger at this stage.

```yaml
new:
    - skills/commands-pause-work
```

- **new** `skills/commands-pause-work` — "Offer a skill dedicated to instructing agents how
  to pause work in progress and hand it off for resumption". Every skill this plugin ships
  has exactly one capability under `skills/` (`tcw capabilities list`, 16 of them); a
  seventeenth skill takes a seventeenth entry. Seeded `Missing` at plan time with a
  `Planning doc` back-pointer, flipped to `Supported` at completion.
- No `changed:` or `removed:`. `tcw capabilities search pause` returns nothing and
  `tcw capabilities check` reports `capabilities OK`, so there is no standing entry this
  contradicts.

## Problem

There is no instruction an agent can be given to stop mid-task.

The plugin ships four command skills, and all four are about moving work **forward**:
`commands-process-inbox`, `commands-plan-work`, `commands-drive-work-to-completion`,
`commands-verify-work` (`skills/work/references/commands.md:304-309`). Nothing covers
stopping part-way, so a user who has to step away tells the agent to stop in their own
words and gets whatever that agent improvises: an edit half-applied, a rationale that
existed only in the session's context, and a checkout that may not survive the gap.

The state that would let the work resume is exactly the state a conversation holds and a
work item does not. TCW's own item model has nowhere to put it either. `tcw work edit` has
no notes field (`tcw work edit --help`), `state.yaml` fields are fixed (a node declaring its
own is a separate backlog item), and the two file registries are closed sets:
`WORK_ARTIFACTS` is the eight lifecycle artifacts and `WORK_SIDECARS` holds `capabilities.yaml`
and the reconcile output, with the comment "New sidecars are added here"
(`tcw/store/base.py:2472`, `:2484`). So the only places a pausing agent could write today are
the item's body — the requester's own words — or a lifecycle artifact it has not finished,
and writing `outcome.md` early is worse than writing nothing: presence is what the board and
the stage ladder read, so a partial one reports the item as implemented and sends the next
reader to `verify`.

## Goals

1. One thing a user types to make an agent stop, that works the same whether they are back
   in five minutes or on a different machine next week.
2. The agent stops at a coherent point rather than mid-edit, and nothing it had done is left
   only in a working tree or only in the session's context.
3. A **standard, named place** for the handoff state, so a resuming agent knows where to
   look without being told, and so the note does not accumulate as litter in artifacts that
   mean something else.
4. The agent then holds. It does not complete, discard, hand on, or resume on its own.
5. Registered the way every other skill in this plugin is registered, so it is discoverable
   under both Claude Code and Codex and the suite stays green.

## Non-goals

- **A paused status, a pause verb, or a new registered file shape in the `tcw` CLI.** Fixed
  by the request: skill only, no Python changes. The consequences are in Risks.
- **A resume command.** `commands-drive-work-to-completion` already detects where an item
  stands from its artifacts; this item's job is to leave it something worth reading. The
  resume *rule* (read the handoff, then delete it) is specified here and carried in the new
  skill, but no second skill is built.
- **Claim recovery.** Grounded below: a graceful pause runs no transition and so leaves no
  claim to recover. `2026-09-15-make-start-take-over-recover-an-interrupted-claim-…` stays
  related, not blocking.
- **Pausing as indefinite parking or a handoff to a different person.** That is an ordinary
  stop and the item's lifecycle already covers it.
- A sweep for sibling defects: nothing was reported broken. A narrow sweep was run anyway —
  `grep -riE "\bpause|stop work|stand down|interrupt" skills/` finds only two mentions of an
  *interrupted claim* in `commands.md` (`:184`, `:319`), neither of which tells an agent how
  to stop. There is no existing guidance to make consistent with this.

## Design

### The handoff document

A paused agent writes **one file per affected work item**, in that item's folder:

```
<stage-id>.handoff.md
```

`<stage-id>` is the lifecycle stage the agent was running: one of `inbox`, `request`, `spec`,
`plan`, `implement`, `verify`, `postmortem` (`LIFECYCLE_STEPS`, `tcw/store/base.py:1736ff`).
When the agent was between stages, it uses the stage it would run next — the first missing
artifact, which is the rule the `work` skill's "Finding your place" already gives, so no
second rule is introduced.

Naming it for the **stage** rather than the artifact is deliberate, and it diverges from the
neighbouring `<artifact>.draft.md` shape (`write_draft`, `tcw/store/fs.py:6475`). A stage is
in progress before anyone has decided what its artifact will say, and a resuming agent's
first question — answered by `tcw work stage`, which takes stage ids — is which stage it is
in. `verify` also produces two possible artifacts, so there is no single artifact name to
use. The inconsistency is chosen, not overlooked.

**The document is deleted when the work resumes**, by the agent that read it. It is a message
in flight, not a record: it says where someone got to, which stops being true the moment they
carry on, and a stale one is worse than none. The lasting record is the artifact and the
commit.

Its content is whatever resuming needs and nothing more — written for a reader with no memory
of the session, possibly on another machine, from a fresh clone:

- the stage in progress and what within it was done and not done;
- **the branch name and the last commit**, since nothing else records them: `state.yaml` has a
  `branch` field (`tcw/store/fs.py:4268`) but it is populated only for `--worktree` items, and
  making it general is a separate backlog item;
- decisions already taken and the reasoning behind them, which is the part a commit diff
  cannot show;
- anything deliberately left broken or half-done, and what it was going to become;
- the immediate next action.

### What the pause does, in order

1. **Reach a coherent resting point.** Finish the edit in hand or back it out; start nothing
   new. "Coherent" means the checkout parses and the change is intelligible — not that it is
   complete or that the suite is green, which for a mid-task pause it usually will not be.
2. **Commit and push.** A work-in-progress commit on the item's branch, marked as such, then
   pushed. A different machine can only see what reached the remote, so the push is part of
   the pause. Committing before writing the handoff is what lets the handoff name the commit.
3. **Write the handoff document** for each work item in flight.
4. **Commit the handoff** with the store's own commit, narrow, the way every skill here does.
5. **Report and stop.** One short message naming the item(s), the branch, and what to type to
   resume. Then silence: no further tool calls, no scheduled check-in, no background task
   left to wake it.

Effort scales with what is in flight, as the request requires: nothing uncommitted and
nothing in the agent's head is a pause that writes no handoff at all and just says so.

### Status and the claim

The item stays `active` and stays claimed, and the skill runs **no transition**. This costs
nothing and needs no take-over, which is worth stating because the request flagged it as a
tension to resolve:

- An "interrupted claim" is a leftover `.claiming/<slug>-<uuid>` directory — a transient
  artifact of a `start` that never finished publishing (`_claiming_dirs` / `_lost_the_claim`,
  `tcw/store/fs.py:3835`, `:3878`). An item sitting in `active/` has no such directory.
- A pause runs no transition, so it creates none. A reboot mid-pause cannot either, because
  the only window is inside `start`.
- Resuming an `active` item never calls `start` — `commands-drive-work-to-completion` runs it
  only "if the item is not already active" — so the owner identity is never compared and a
  cold resume on another machine needs no `--take-over`.

### Registration

`commands-pause-work` carries a procedure of its own, which is what distinguishes it from the
four existing command skills: they only name a stage range and hand each stage to
`work-stage`, which is why `skills/README.md` marks all four `fixed (Rule 2)`. A pause is not
a lifecycle stage and has no stage document behind it, so Rule 2 does not apply and Rule 1
decides. Its subject — how to stop, what to commit, how much to write down — is *conduct*,
the project's to change, so the verdict is **overridable** and `dynamic_skill: true`. The one
rule that stays TCW's, and must not be overridable-away, is where the handoff lives and that
resuming deletes it; the spec places that in the fixed half, the way `skills/README.md`
describes for a mixed document.

Registration therefore covers: the skill folder and `SKILL.md` with the frontmatter shape the
other skills use; a verdict row in `skills/README.md`; the Codex manifest prose, which names
every skill and states the count in words and is guarded by
`tests/test_plugin_manifests.py::test_the_codex_description_counts_the_skills_it_ships`
(`sixteen` → `seventeen`; `seventeen` is already in `NUMBER_WORDS`, so only the prose moves);
the "Command skills" paragraph in `skills/work/references/commands.md:304`, which says "Four
skills"; `README.md`, a `Public-API` documentation entry; the eval coverage registry
`evals/EXCLUSIONS` (`evals/coverage.py:34`), enforced by `tests/test_eval_coverage.py`; and
the release-note and changelog entries `tcw work docs` requires.

## Acceptance criteria

1. `skills/commands-pause-work/SKILL.md` exists, with `name`, `description`, `when_to_use`,
   `allowed-tools`, `metadata.author`, `license` and `dynamic_skill` — the same frontmatter
   keys `skills/commands-drive-work-to-completion/SKILL.md` carries.
2. `dynamic_skill: true`, and `skills/README.md` has a row for
   `commands-pause-work` / `SKILL.md` with the verdict `overridable`.
3. `pytest tests/test_dynamic_skill_marker.py` passes.
4. `pytest tests/test_plugin_manifests.py` passes: `.codex-plugin/plugin.json`'s
   `interface.longDescription` says "seventeen skills" and contains the backticked name
   `` `commands-pause-work` ``.
5. `pytest tests/test_eval_coverage.py` passes, with `commands-pause-work` carrying an
   exclusion reason specific enough to disagree with — not a copy of the four command skills'
   reason, which does not apply to a skill that carries its own procedure.
6. The "Command skills" paragraph at `skills/work/references/commands.md:304` names five
   skills and says "Five", and `README.md` names the new skill where it lists the others.
7. The skill's body states, in terms a reader can follow without this spec: the file name
   `<stage-id>.handoff.md`; that `<stage-id>` is a lifecycle stage id and which stage to use
   when between stages; that the resuming agent reads it and then deletes it; and the five
   content items listed under "The handoff document", branch and last commit among them.
8. The skill's body instructs: reach a coherent resting point, commit **and push** a marked
   work-in-progress commit, write the handoff, commit it narrowly, report, then stop — and
   states that no transition is run and the item stays `active` and claimed.
9. The skill tells the agent to fall silent: no further tool calls, no scheduled check-in, no
   background task left that would wake it.
10. The skill scales effort to what is in flight, and says explicitly that nothing in flight
    means no handoff document is written.
11. Nothing under `tcw/` changes. `git diff --stat` on the finished branch shows no file under
    `tcw/`.
12. `tcw capabilities show skills/commands-pause-work` resolves, carries
    `Planning doc=<this slug>`, and reads `Supported` once the item completes; the item's
    `capabilities.yaml` lists it under `new:`.
13. `pytest` passes whole, and `tcw validate` exits 0.
14. `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` each carry an entry for
    the new skill, per `tcw work docs`.

## Risks

- **The handoff file is unregistered, so `tcw` cannot see it.** It is in neither
  `WORK_ARTIFACTS` nor `WORK_SIDECARS`, and both places that enumerate an item's files list
  only those registries — `_modified_timestamp` (`tcw/store/fs.py:4276`) and
  `_validation_resources` (`:5686`). Consequences, accepted: the item's `modified` timestamp
  does not move when a handoff is written or deleted; `tcw://` links inside a handoff are not
  resolved by `tcw validate`; and `tcw serve` does not display or offer to edit it. It does
  **survive a status transition**, because a transition moves the whole item directory
  (`_mv`, `tcw/store/fs.py:6413`) rather than copying known names. Registering `handoff` in a
  registry is the obvious follow-up and needs the Python change this item excludes.
- **It is also outside the abstraction litmus test's bounded namespace.** The prime directive
  names "globbing a store folder as an open namespace" as something to keep out of the model,
  bounded to "body + named fields + named attachments". A file the skill writes by convention
  is exactly that, and the honest reading is that this is a **skill-layer convention living
  beside the model, not in it** — which is tolerable only because the name is fixed and small
  (seven possible values, one per stage) and because nothing in `tcw` depends on it. The
  follow-up above is what would move it inside.
- **A stale handoff outlives its truth.** Deletion on resume is carried by prose, and nothing
  enforces it. A resume that reads the file and forgets to delete it leaves a document
  describing a position the work has since left — the failure mode the "message, not a record"
  framing exists to prevent, and the reason the skill says to delete it in the same step as
  reading it rather than at the end of the resumed work.
- **"Coherent resting point" is a judgment, and a bad one costs the user the thing they
  wanted.** A pause that tries to reach green tests is a pause that takes ten minutes while
  the user is already offline. The criterion is stated as *parses and is intelligible*, not
  *builds* or *passes*, and effort scales with what is in flight — but an agent can still read
  it too ambitiously.
- **The push can fail, and the user may already be gone.** A network that is dropping is
  precisely the situation this skill is for. Unresolved here on purpose and left to `plan`:
  whether a failed push aborts the pause, or the pause completes and the report says the work
  is committed locally only, which is the honest state and the one the user can act on when
  they return.

## Notes

- The `verify` stage produces either `refined-outcome.md` or `rework.md`; stage-id naming
  sidesteps that, which is a second reason for it beyond the one in Design.
- `<artifact>.draft.md` was considered as the home for the handoff and rejected. It is the
  better-integrated shape — it is a real store operation (`write_draft`), it is deliberately
  invisible to `artifacts()` so presence stays honest, and `tcw work scaffold` already writes
  one. But a draft is *the artifact, partially written*, and a handoff is not: it carries
  branch names, what was left broken, and what to do next, none of which belongs in the
  document that ships. Keeping them separate also keeps the delete-on-resume rule from
  destroying real drafted work.
- Assumption, not verified against a run: that no tooling rejects an unrecognized file in an
  item folder. Grounded negatively — the two enumerations above list only known names and
  nothing found scans for unexpected ones — but no test was written to confirm it. `plan`
  should have the implementation confirm it with `tcw validate` against an item holding a
  handoff file.
