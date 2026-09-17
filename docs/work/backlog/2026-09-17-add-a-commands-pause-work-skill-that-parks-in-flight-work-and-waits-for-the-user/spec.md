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
  seventeenth skill takes a seventeenth entry. Seeded `Missing` with a `Planning doc`
  back-pointer, flipped to `Supported` at completion.
- Each sibling also carries `Feature: <skill-name>-skill` and `Subject: [skill]`
  (`docs/capabilities/skills/commands-verify-work/meta.yaml`). The Feature must be
  **registered in the taxonomy first**: `_check_feature` (`tcw/store/fs.py:2938`) refuses a
  write carrying a reference that does not resolve, so the order is taxonomy term, then
  capability. This is a taxonomy delta as well as a capability one.
- No `changed:` or `removed:`. `tcw capabilities search pause` returns nothing and
  `tcw capabilities check` reports `capabilities OK`.

## Problem

There is no instruction an agent can be given to stop mid-task.

The plugin ships four command skills, and all four are about moving work **forward**:
`commands-process-inbox`, `commands-plan-work`, `commands-drive-work-to-completion`,
`commands-verify-work` (`skills/work/references/commands.md:306`). Nothing covers stopping
part-way, so a user who has to step away tells the agent to stop in their own words and gets
whatever that agent improvises: an edit half-applied, a rationale that existed only in the
session's context, and a checkout that may not survive the gap.

The state that would let the work resume is exactly the state a conversation holds and a
work item does not. `tcw work edit` has no notes field (`tcw work edit --help`), `state.yaml`
fields are fixed, and writing a lifecycle artifact early is worse than writing nothing:
presence is what the board and the stage ladder read, so a partial `outcome.md` reports the
item as implemented and sends the next reader to `verify`.

## Goals

1. One thing a user types to make an agent stop, that works whether they are back in five
   minutes or on a different machine next week.
2. The agent stops at a coherent point rather than mid-edit.
3. A **standard, named place** for the handoff state, so a resuming agent knows where to look.
4. **Something on the resume path actually reads it.** A note nobody opens is litter.
5. The agent then holds — no completing, discarding, handing on, or resuming on its own.
6. Registered the way every other skill is, so the suite stays green and it is discoverable
   under both Claude Code and Codex.

## Non-goals

- **A paused status or a pause verb in the `tcw` CLI.** Fixed by the request: skill only, no
  Python changes.
- **A resume command.** The resume *rule* is added to the existing router (Design), not built
  as a second command skill.
- **Claim recovery.** A graceful pause runs no transition and leaves no claim to recover.
- **Pausing as indefinite parking or a handoff to a different person.**
- A sweep for sibling defects: nothing was reported broken. A narrow sweep was run —
  `grep -riE "\bpause|stop work|stand down|interrupt" skills/` finds only two mentions in
  `commands.md` (`:184`, about a command interrupted between its commit and the tracker call;
  `:319`, about an interrupted claim), neither of which tells an agent how to stop. The
  nearest existing guidance is `commands-drive-work-to-completion/SKILL.md:33-35`, which
  tells an agent to hold for user approval at `verify` — a different moment, and consistent
  with this.

## Design

### The handoff document

A paused agent writes **one file per affected work item**, in that item's folder, located
with `tcw work path <slug>` — never by composing the path. This is the same instruction
TCW's own shipped procedures already give: `tcw/work/procedures/create-work.md:125-126` has
agents `git -C <store folder> add/commit` against an absolute path obtained that way.

```
<stage-id>.handoff.md
```

`<stage-id>` is the lifecycle stage the agent was running: one of `request`, `spec`, `plan`,
`implement`, `verify`, `postmortem` (`LIFECYCLE_STEPS`, `tcw/store/base.py:1712`). When
between stages, the stage that would run next — the first missing artifact, which is the
`work` skill's "Finding your place" rule.

**`inbox` is excluded, deliberately.** At that stage there is no item and no folder; entries
live under `docs/work/inbox/` (`tcw/store/fs.py:5705`). A handoff written into a folder-shaped
entry would be swept into `attachments/` by `inbox_accept` (`fs.py:5860`, `:5895`) and then
have its source removed (`:5905`) — surviving under a name nothing looks for. An inbox-stage
pause writes no handoff: the raw entry is already the durable record, and the skill says so.

Naming it for the **stage** rather than the artifact diverges from the neighbouring
`<artifact>.draft.md` shape (`write_draft`, `tcw/store/fs.py:6475`). A stage is in progress
before anyone has decided what its artifact will say; `verify` produces two possible
artifacts; and a resuming agent's first question is answered by `tcw work stage`, which takes
stage ids. The inconsistency is chosen.

**It contains no `tcw://` links.** `tcw validate` scans every `*.md` under the work root —
`_iter` is `root.rglob(pattern)` (`tcw/validate.py:62`) and the link pass runs over it
(`:313`) — and this repo binds `tcw validate` as `transitions.complete.pre`
(`tcw-config.yaml:74-76`). A handoff carrying a dangling reference would therefore **refuse
`tcw work complete`**. Reference other items by bare slug.

**Deleted when the work resumes**, by the agent that read it, in the same step as reading it.
It is a message in flight, not a record.

**A pause removes any handoff already there** before writing its own. Because the name is
keyed to the stage, a `spec` pause followed by an `implement` pause would otherwise leave two,
one describing a position the work has left.

Content, written for a reader with no memory of the session:

- the stage in progress and what within it was and was not done;
- **the branch name and the last commit**: `state.yaml`'s `branch` field
  (`tcw/store/fs.py:4268`) is written only by `start --worktree` (`tcw/work/cli.py:1045`), so
  nothing else records it;
- decisions already taken and the reasoning behind them;
- anything deliberately left broken, and what it was going to become;
- the immediate next action.

### What the pause does, in order

1. **Reach a coherent resting point.** Finish the edit in hand or back it out; start nothing
   new. "Coherent" means the checkout parses and the change is intelligible — not that it is
   complete or the suite is green.
2. **Ask whether to commit and push.** One question, and the answer decides the rest: the
   user is right there at the moment they type "pause", and they are the only one who knows
   whether this is five minutes or a different machine. Offer commit-and-push (durable
   anywhere), commit-only, or leave the tree alone. **An unanswered question is a yes**:
   silence plus an absent user is the cold-handoff case by definition, so the agent commits
   and pushes rather than leaving the work reachable from one checkout.
3. **Commit and push, if that was the answer.** A work-in-progress commit on the item's
   branch, marked as such.
4. **Write the handoff document** for each work item in flight, after the commit, so it can
   name it.
5. **Commit and push the handoff** — on the same answer. The push is not optional when the
   answer was yes, and it is a **second** push, not covered by step 3: the handoff is written
   after that commit, and where the work store is a different repository from the code
   (`work.repository`, provisioned per-machine under `~/.cache/tcw/` —
   `tcw/store/checkouts.py:60`) it is a different remote entirely. TCW's own publish path
   runs only on a transition (`_publish_after_transition`, `tcw/store/fs.py:5281`), and a
   pause runs none, so nothing pushes the store for you.
6. **Report and stop.** One short message: the item(s), the branch, whether the work reached
   the remote, and what to type to resume. If the user declined the commit, say plainly that
   the handoff exists only in this checkout. Then silence — no further tool calls, no
   scheduled check-in, no background task left that would wake the agent.

Effort scales with what is in flight: nothing uncommitted and nothing held only in the
agent's head is a pause that writes no handoff and says so.

### The resume side

A handoff nobody opens is litter, so the read is added to the router every resume path
already goes through, rather than left inside the pause skill — which loads when stopping,
not when starting.

`skills/work/SKILL.md`'s **"Finding your place"** (`:42-48`) gains one step, before artifact
detection: look for a `<stage-id>.handoff.md` in the item's folder; if one is there, read it,
let it inform where to pick up, and delete it as part of the same step.
`commands-drive-work-to-completion/SKILL.md` gains a sentence pointing at it, since it is the
skill a user names when resuming.

### Status and the claim

The skill runs **no transition**, so it changes no status and creates no claim state. What
the item's status *is* at pause time depends on the stage, and the earlier draft of this spec
got that wrong by asserting `active` for all of them:

| Stage paused in | Item status |
| --- | --- |
| `request`, `spec`, `plan` | `backlog` — `start` moves `backlog → active` (`tcw/store/base.py:1752`) and runs only before implementation begins |
| `implement` | `active` |
| `verify`, `postmortem` | `review` — `submit` moves `active → review` (`base.py:1756`) |

Consequences:

- **Pausing in `backlog` leaves no claim at all**, so a cold resume there runs
  `tcw work start` normally, which stamps `owner` from that machine's git identity
  (`_local_owner`, `tcw/work/cli.py:887`).
- **Pausing in `active` keeps the claim** and needs no `--take-over` to resume: an
  "interrupted claim" is a leftover `.claiming/<slug>-<uuid>` directory from a `start` that
  never published (`_claiming_dirs`, `tcw/store/fs.py:3835`; `_lost_the_claim`, `:3862`), and
  an item sitting in `active/` has none. Resuming an already-`active` item never calls
  `start`.
- **One exception, for tracker-configured nodes.** `_started_by_someone_else`
  (`tcw/work/cli.py:2259`) refuses `tcw work tracker link --sync-status` (`:2342`) and
  refuses-or-silently-skips `tracker sync` (`:2488`) when `item.owner` differs from the local
  identity, naming `--take-over` as the remedy. A same-person cold resume usually carries the
  same git email and is unaffected; a different identity is not. TCW itself configures no
  tracker, so this never surfaces here — the skill states it so that a node which does
  configure one is not surprised.

### Registration

`commands-pause-work` carries a procedure of its own, unlike the four existing command
skills, which only name a stage range and hand each stage to `work-stage` — which is why
`skills/README.md` marks all four `fixed (Rule 2)`. A pause is not a lifecycle stage, so Rule
2 does not apply and Rule 1 decides. Its subject — how to stop, what to commit, how much to
write down — is *conduct*, so the verdict is **overridable** and `dynamic_skill: true`.

**What that key can and cannot do here, stated plainly because the earlier draft implied
more.** `skills/README.md` says outright: "The key is for people. Neither Claude Code nor
Codex acts on it." A project actually replacing a procedure's text needs a procedure id, and
ids are TCW's closed set (`PROCEDURE_IDS`) — adding one is the Python change this item
excludes. So `true` here **records intent**, exactly as `skills/README.md` permits ("Until a
skill is converted, `true` records the intent"), and the fixed/overridable split is prose, not
a mechanism. The row must say so rather than promising enforcement that does not exist.

Registration covers: the skill folder and `SKILL.md`; a verdict row in `skills/README.md`;
the Codex manifest prose, guarded by
`tests/test_plugin_manifests.py::test_the_codex_description_counts_the_skills_it_ships`
(`sixteen` → `seventeen`; `seventeen` is already in `NUMBER_WORDS` at `:71`); the "Command
skills" paragraph at `skills/work/references/commands.md:306`; `README.md:681-688`; the eval
coverage registry (`evals/coverage.py:34`); the taxonomy Feature and the capability; and the
release-note and changelog entries.

## Acceptance criteria

1. `skills/commands-pause-work/SKILL.md` exists with the same frontmatter keys
   `skills/commands-drive-work-to-completion/SKILL.md` carries — `name`, `description`,
   `when_to_use`, `allowed-tools`, `metadata.author`, `license`, `dynamic_skill`.
2. `dynamic_skill: true`, with a row in `skills/README.md` for `commands-pause-work` /
   `SKILL.md` whose verdict is `overridable` and whose reason states both that the skill
   carries its own procedure and that the key records intent rather than a mechanism.
3. `pytest tests/test_dynamic_skill_marker.py` passes.
4. `pytest tests/test_plugin_manifests.py` passes; the Codex `longDescription` says
   "seventeen skills" and contains the backticked name `` `commands-pause-work` ``.
5. `commands-pause-work` is in `evals/EXCLUSIONS` with a reason that is not a copy of the
   four command skills' reason. **Checked by reading** — `tests/test_eval_coverage.py` tests
   key presence only (`evals/coverage.py:96`), so any string passes it and it cannot prove
   this criterion.
6. `skills/work/references/commands.md` names five command skills, says "Five", and its
   following sentence ("each invokes the `work-stage` skill for the stage it runs") is
   reworded so it is true of all five. `README.md` has a matching table row.
7. The skill's body states: the file name `<stage-id>.handoff.md`; that `<stage-id>` is a
   lifecycle stage id and which stage to use when between stages; that `inbox` is excluded
   and why; that it carries no `tcw://` links; that a pause first removes any handoff already
   present; that resuming reads it and deletes it in the same step; and the five content
   items, branch and last commit among them.
8. The skill's body instructs, in order: coherent resting point → **ask whether to commit and
   push, treating no answer as yes** → commit and push → write the handoff → commit and push
   the handoff **as a second push** → report → stop. It states that no transition is run and
   that nothing pushes the store automatically.
9. The skill tells the agent to fall silent: no further tool calls, no scheduled check-in, no
   background task left that would wake it.
10. The skill scales effort to what is in flight, and says that nothing in flight means no
    handoff is written.
11. `skills/work/SKILL.md`'s "Finding your place" instructs a resuming agent to look for,
    read, and delete a handoff before detecting the stage from artifacts; and
    `commands-drive-work-to-completion/SKILL.md` points at that step.
12. Nothing under `tcw/` changes: `git diff --stat main...HEAD -- tcw/` is empty.
13. The taxonomy Feature `commands-pause-work-skill` is registered, and
    `tcw capabilities show skills/commands-pause-work` resolves carrying `Feature`, `Subject`
    and `Planning doc`, reading `Supported` once the item completes; the item's
    `capabilities.yaml` lists it under `new:`.
14. A handoff file present in an item folder does not change what `tcw validate`,
    `tcw work show` or `tcw work list` report, and **survives a status transition** — proven
    by running one, not asserted.
15. `pytest` passes whole, and `tcw validate` exits 0.
16. `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` carry entries for the
    new skill, **and their existing "sixteen"/"four" counts are corrected** — both are
    unreleased entries for the version this ships in
    (`docs/changelogs/upcoming.md:92`, `docs/release-notes/upcoming.md:64`).

## Risks

- **The handoff is unregistered, so parts of `tcw` do not know it.** It is in neither
  `WORK_ARTIFACTS` nor `WORK_SIDECARS` (`tcw/store/base.py:2472`, `:2484` — three entries:
  `capabilities.yaml`, the reconcile rollup, and `tracker.yaml` at `:2504`), and the two
  places enumerating an item's files list only those — `_modified_timestamp`
  (`tcw/store/fs.py:4276`) and `_validation_resources` (`:5686`). So the item's `modified`
  timestamp does not move, and `tcw serve` neither displays nor offers to edit it. It **does**
  survive a status transition: `_effect_transition_locked` (`fs.py:6007`) moves the whole
  directory via `git_mv` (`:607`), which stages untracked contents first. Registering
  `handoff` in `WORK_SIDECARS` is the obvious follow-up and needs the excluded Python change.
- **An uncommitted handoff can refuse completion.** `_require_retrievable`
  (`tcw/store/fs.py:4828`) refuses to delete an item folder holding content no commit holds,
  and this node sets `work.retain.completed: false`. The window is between writing the
  handoff and committing it — reachable if the user declines the commit, or if it fails.
  Mitigated by the resume-side delete and by the skill saying what state it left behind; not
  eliminated.
- **A stale handoff outlives its truth.** Deletion is carried by prose. Placing the read in
  "Finding your place" narrows it, because the delete now sits on the path every resume takes
  rather than only in a skill the resumer may never load.
- **"Coherent resting point" is a judgment.** A pause that tries to reach green tests is a
  pause that takes ten minutes while the user is already offline. Stated as *parses and is
  intelligible*.
- **Asking costs a round trip at the worst moment.** The user may be losing connection as the
  question is asked. The no-answer-is-yes rule is what keeps that from losing the work, but it
  means an agent can commit and push against a user who would have said no.
- **The `dynamic_skill: true` verdict promises less than it looks like.** Recorded above; the
  risk is a reader taking the row as enforcement.

## Notes

- **The abstraction litmus test was considered and does not bite.** It governs operations
  added to the store interface; this item adds none. TCW's own shipped procedure already
  instructs agents to write and commit files located with `tcw work path`
  (`tcw/work/procedures/create-work.md:125-126`), so a skill saying "write a file in the item
  folder" is the established pattern, not a departure from it.
- `<artifact>.draft.md` was considered as the handoff's home and rejected: a draft is *the
  artifact, partially written*, while a handoff carries branch names, what was left broken,
  and what to do next — none of which belongs in the document that ships. Keeping them apart
  also stops delete-on-resume destroying real drafted work.
- A second "stage id" namespace exists — declared plan-stage documents at `plan/<id>.md`
  (`tcw/store/fs.py:5627`). No collision (`plan.handoff.md` is a file, `plan/` a directory),
  but the skill should say "lifecycle stage id" rather than "stage id".
- This spec was rewritten after an adversarial review of its first draft. Corrected: the
  push gap, the missing resume-side reader, the false claim that `tcw validate` ignores the
  file, the wrong assertion that the item is always `active`, the unhomed `inbox` handoff, the
  missing taxonomy prerequisite, and six imprecise citations.
