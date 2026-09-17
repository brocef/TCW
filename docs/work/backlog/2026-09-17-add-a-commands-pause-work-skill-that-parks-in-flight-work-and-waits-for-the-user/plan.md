# Plan: commands-pause-work

Six tasks in four commits. The suite is green at every commit boundary, which is what
forces Task 2's shape: three tests read `skills/*/SKILL.md` as their source of truth, so
they go red the instant the new skill file exists. The skill and its registration are one
commit or they are a broken tree.

## Task 1 — Declare the capability

**Creates:** `docs/capabilities/skills/commands-pause-work/` (`meta.yaml` +
`description.md`), and `capabilities.yaml` in this item's folder.

```bash
tcw capabilities add skills/commands-pause-work \
  "Offer a skill dedicated to instructing agents how to pause work in progress and hand it off for resumption" \
  --status Missing
tcw capabilities set skills/commands-pause-work \
  --field "Planning doc=2026-09-17-add-a-commands-pause-work-skill-that-parks-in-flight-work-and-waits-for-the-user"
```

Then write the item's `capabilities.yaml`:

```yaml
new:
    - skills/commands-pause-work
```

Match `description.md` to the wording of the sibling entries — read
`tcw capabilities show skills/commands-verify-work` first and follow its shape rather than
inventing one.

**Proves it:** `tcw capabilities show skills/commands-pause-work` resolves and prints
`Status: Missing` with the `Planning doc` field set; `tcw capabilities check` exits 0.

**Commit:** on its own. It touches no test's source of truth, so the suite stays green.

## Task 2 — The skill, and every registration that must land with it

**Creates:** `skills/commands-pause-work/SKILL.md`.
**Modifies:** `skills/README.md`, `.codex-plugin/plugin.json`, `evals/coverage.py`.

These four files are **one commit**. Each of the last three is read by a test that
enumerates `skills/*/SKILL.md`, so creating the skill without them leaves three failures.

### `skills/commands-pause-work/SKILL.md`

Frontmatter: the exact key set `skills/commands-drive-work-to-completion/SKILL.md` carries —
`name`, `description`, `when_to_use`, `allowed-tools`, `metadata.author` (`Brian Cefali`),
`license` (`Apache-2.0`), `dynamic_skill`. Values specific to this skill:

- `name: commands-pause-work`
- `dynamic_skill: true`, followed by the same trailing comment the siblings carry
  (`# which skills a project may override, and why: ../README.md`)
- `allowed-tools`: `Bash(tcw *), Bash(git *), Read, Edit, Write` — the same set. The skill
  commits and pushes, which `Bash(git *)` already covers.
- `when_to_use`: must trigger on how a user actually says it — "pause", "stop for now",
  "hold on", "I'm about to lose connection", "I need to reboot" — and must **not** trigger
  on finishing, abandoning, or blocking work, which are `commands-drive-work-to-completion`
  and `tcw work discard`.

Body, in the order the spec's "What the pause does" gives, with these points stated
explicitly because the acceptance criteria check for them:

1. Reach a coherent resting point — *parses and is intelligible*, *not* builds or passes.
   Finish the edit in hand or back it out; start nothing new.
2. Commit **and push** a work-in-progress commit on the item's branch, marked as such.
   State why the push is not optional: a different machine sees only what reached the
   remote.
3. Write `<stage-id>.handoff.md` in each affected item's folder, where `<stage-id>` is one
   of `inbox`, `request`, `spec`, `plan`, `implement`, `verify`, `postmortem` — and when
   between stages, the stage that would run next, which is the `work` skill's "Finding your
   place" rule. Locate the folder with `tcw work path <slug>`; never compose the path.
   Contents: the stage and what within it was and was not done; the branch name and last
   commit; decisions taken and why; anything deliberately left broken and what it was going
   to become; the immediate next action.
4. Commit the handoff narrowly, into the repository holding the store
   (`git -C <store folder> add -- <path>` then commit by path), the way `work-create` does.
5. Report in one short message — item(s), branch, what to type to resume — and stop. State
   the silence rule plainly: no further tool calls, no scheduled check-in, no background
   task left that would wake the agent.

Two more rules the body must carry:

- **Scale to what is in flight.** Nothing uncommitted and nothing held only in the agent's
  head means **no handoff document is written** — say that, so an agent does not
  manufacture one.
- **Resuming deletes the handoff**, in the same step as reading it. Say why: it is a message
  in flight, not a record, and a stale one describes a position the work has left. Mark this
  and the file name as the parts a project overriding this skill does not get to change —
  `skills/README.md` calls that a mixed document keeping its rules fixed.

State that the skill runs **no transition**: the item stays `active` and claimed, and
resuming needs no `--take-over`. Keep the reasoning out of the skill — it is in `spec.md`.

Route, do not restate: name the `work` skill for the stage ladder and `work-stage` for any
stage the agent resumes into, the way the sibling command skills do.

### `skills/README.md`

Add one row to the verdict table, in the block with the other `commands-*` rows:

| `commands-pause-work` | `SKILL.md` | overridable | ... |

The reason must be specific enough to disagree with, and must say what the other four rows
do not: this skill is `overridable` rather than `fixed (Rule 2)` **because it carries a
procedure of its own** — a pause is not a lifecycle stage and has no stage document behind
it — and what it carries (how to stop, what to commit, how much to write down) is conduct.
Name the fixed half in the same row: the handoff file's name and delete-on-resume are
TCW's, per the mixed-document rule above it.

### `.codex-plugin/plugin.json`

In `interface.longDescription`: `sixteen skills` → `seventeen skills`; `four command
skills` → `five command skills`; add `` `commands-pause-work` `` to that enumeration with a
clause saying what it does. The test matches the name **backticked**, so plain text does not
satisfy it.

### `evals/coverage.py`

Add `commands-pause-work` to `EXCLUSIONS` (`:34`) with its **own** reason. Do not extend the
four-name `**{name: ...}` comprehension — its reason ("Composes `work` stage documents that
axis A measures, and has no case of its own yet") is false here, and reusing it would be the
silent partial coverage the module's docstring exists to prevent. The honest reason: the
skill's observable outcome is an agent that stops and stays stopped, so a graded run has no
produced artifact to read and would have to measure an absence — plus the handoff document
it writes is deleted by the resume it is graded against. Say that a case becomes worth
writing if the harness gains a way to assert a run ended deliberately.

**Proves it:**
`pytest tests/test_dynamic_skill_marker.py tests/test_plugin_manifests.py tests/test_eval_coverage.py`
passes; `python evals/coverage.py` reports nothing uncovered.

## Task 3 — The two enumerations in prose

**Modifies:** `skills/work/references/commands.md`, `README.md`.

- `commands.md:304-309` (heading at `:304`, prose at `:306-309`) — the "Command skills" paragraph opens "Four skills carry the
  everyday workflows" and lists four. Make it five and add `commands-pause-work`. The
  sentence after it ("Each works by invoking the skill, under any harness, and each invokes
  the `work-stage` skill for the stage it runs") is **now false of one member** — this skill
  invokes `work-stage` only if the agent resumes into a stage. Reword so it stays true of
  all five rather than leaving a sentence that quietly excludes the new one.
- `README.md:681-688` — add a row to the **Command skills: the everyday workflows** table,
  matching the one-sentence, second-person style of its neighbours. The table has no count
  sentence, so nothing else moves.

**Proves it:** `grep -c` finds `commands-pause-work` in both; reading the reworded
`commands.md` sentence against all five skills shows no false claim.

**Commit:** with Task 2's four files if that keeps the change legible, or on its own. Either
boundary is green — nothing here is a test's source of truth.

## Task 4 — Confirm the handoff file is tolerated

**Modifies:** nothing.

The spec records an assumption it did not verify: that no tooling rejects an unrecognized
file in an item folder. Confirm it before the skill tells anyone to write one.

```bash
# in this item's folder, via `tcw work path <slug>` — do not compose the path
printf '# handoff\n\ntest\n' > "$(tcw work path <slug>)/implement.handoff.md"
tcw validate; tcw work show <slug>; tcw work list
rm "$(tcw work path <slug>)/implement.handoff.md"
```

**Proves it:** `tcw validate` exits 0 with the file present, and `tcw work show` / `tcw work
list` report the item no differently.

**If it fails,** the design is wrong and this returns to `spec` rather than being worked
around — the handoff has no fallback home that the spec did not already reject.

## Documentation Sync

Evaluated against `tcw work docs`; scheduled as one block, run over the finished diff.

| Entry | Trigger | Fires | Task |
| --- | --- | --- | --- |
| `README.md` | `Public-API` | **yes** — a new shipped skill is public surface | Task 3 |
| `docs/release-notes/upcoming.md` | `Public-API` | **yes** | Task 5 |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **yes** | Task 5 |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **yes, narrowly** | Task 3 |
| `docs/guide/jira.md` | `Tracker-Change` | no | — |
| `skills/configure/references/<document>.md` | `Configuration-Key-Change` | no | — |

- **`Skill-Driven-Component` fires narrowly and the reason is worth recording.** The trigger
  is written for a component changing — its CLI surface, model, lifecycle or guardrails —
  and no component changes here: nothing under `tcw/` moves. What changes is a *fact inside*
  the `work` skill's own reference document, which enumerates the command skills and would
  become wrong. Treated as firing on that basis alone.
- **`Tracker-Change` does not fire.** No `tcw work tracker` command changes, no `work.tracker`
  key changes, and — because a pause runs no transition — no lifecycle command's effect on a
  bound ticket changes either.
- **`Configuration-Key-Change` does not fire.** `dynamic_skill` is skill frontmatter, not a
  key in `tcw-config.yaml`, a component config file, `docs/work/dod.yaml`, or a
  `TCW_PROJECT_<ID>` variable.

### Task 5 — Write the entries

**Modifies:** `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`.

- Release note: plain language, no module names — a user can now tell an agent to pause, and
  it stops, writes down what resuming needs, and waits. Name the `<stage-id>.handoff.md`
  file, since a user will see it in their item folder and needs to know what it is and that
  resuming removes it.
- Changelog: `Added` — the skill, its capability, the manifest and coverage registrations.
  Both files already carry entries for this cycle; follow their existing grouping.

**Proves it:** both files name the new skill; `tcw validate` exits 0.

**Commit:** on its own, after the suite is green — the documentation gate runs once over the
finished diff, not per task.

## Task 6 — Flip the capability at completion

**Modifies:** `docs/capabilities/skills/commands-pause-work/meta.yaml`.

`tcw capabilities set skills/commands-pause-work --status Supported`, as the item's final
pre-freeze step. The completion gate blocks `tcw work complete` while a `new:` path still
reads `Missing`, so this is not optional.

**Proves it:** `tcw work complete` is not refused by the capability gate.

## Verification

Beyond the suite:

1. **Nothing under `tcw/` changed** — `git diff --stat main...HEAD -- tcw/` is empty. This is
   the request's hard constraint and no test enforces it.
2. **`pytest`** whole, and **`tcw validate`** exits 0.
3. **The skill is discoverable by its trigger, not just present.** Read `when_to_use` and
   check it fires on "pause", "stop for now", "I'm about to lose connection", and does not
   fire on "finish this" or "drop this". No test can check a description's triggering; it is
   read and judged.
4. **The skill stands alone under Codex.** Read `SKILL.md` as a Codex agent would: no
   dependence on Claude-only mechanisms, no `agents/` dispatch carrying a requirement, every
   instruction executable with the `tcw` CLI and git. This is the harness-compatibility rule
   the `spec` stage bound; nothing automated checks it.
5. **The reworded `commands.md` sentence is true of all five skills** — checked by reading,
   per Task 3.
6. **End-to-end, once:** pause this very item mid-implementation — write
   `implement.handoff.md`, commit, then read it back as if resuming with no memory, and
   check it answers where the work stood, on which branch, and what to do next. If it does
   not, the skill's content list is wrong and Task 2 is not done. Delete it afterwards, which
   is also the delete-on-resume rule being exercised once.

## Notes

- Task 1 is **not** run at the `plan` stage; it is the first task of implementation. The
  ledger record and `capabilities.yaml` are written once the plan is approved, so a plan sent
  back for changes leaves no orphan `Missing` capability behind.
- No blockers recorded. The two related items —
  `2026-09-15-make-start-take-over-recover-an-interrupted-claim-…` and
  `2026-09-10-record-a-work-item-s-branch-…` — neither block this nor are blocked by it: the
  spec establishes that a pause runs no transition and so never meets the take-over path, and
  the branch name is written into the handoff as text precisely because `state.yaml` does not
  carry it for non-worktree items.
- The obvious follow-up — registering `handoff` in `WORK_SIDECARS` so `tcw` can see, validate
  and display it — is deliberately not filed yet. It needs the Python change this item
  excludes, and whether it is worth making is better judged after the convention has been
  used a few times than before it has been used once.
