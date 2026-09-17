# Plan: commands-pause-work

Seven tasks in five commits. The suite is green at every boundary, which is what forces
Task 3's shape: three tests read `skills/*/SKILL.md` as their source of truth and go red the
instant the new skill file exists, so the skill and its registration are one commit or a
broken tree.

Task 1 runs first because its write is refused without it.

## Task 1 — Register the taxonomy Feature

**Creates:** a taxonomy Feature entry, `commands-pause-work-skill`.

Every sibling capability carries `Feature: <skill-name>-skill` and `Subject: [skill]`
(`docs/capabilities/skills/commands-verify-work/meta.yaml`), and `_check_feature`
(`tcw/store/fs.py:2938`) **refuses** a capability write naming a Feature that does not
resolve. So the term exists before the capability, not after.

Read `tcw taxonomy show commands-verify-work-skill` first and mirror its kind, wording and
any links; do not invent a shape.

**Proves it:** `tcw taxonomy show commands-pause-work-skill` resolves and reports kind
`Feature`; `tcw taxonomy check` (or `tcw validate`) exits 0.

**Commit:** on its own.

## Task 2 — Declare the capability

**Creates:** `docs/capabilities/skills/commands-pause-work/` (`meta.yaml`,
`description.md`), and `capabilities.yaml` in this item's folder.

```bash
tcw capabilities add skills/commands-pause-work \
  "Offer a skill dedicated to instructing agents how to pause work in progress and hand it off for resumption" \
  --status Missing
tcw capabilities set skills/commands-pause-work \
  --field "Feature=commands-pause-work-skill" --field "Subject=skill"
tcw capabilities set skills/commands-pause-work \
  --field "Planning doc=2026-09-17-add-a-commands-pause-work-skill-that-parks-in-flight-work-and-waits-for-the-user"
```

`capabilities.yaml`:

```yaml
new:
    - skills/commands-pause-work
```

Match `description.md` to `tcw capabilities show skills/commands-verify-work`.

**Proves it:** `tcw capabilities show skills/commands-pause-work` prints `Status: Missing`
with `Feature`, `Subject` and `Planning doc` all set. Note that `tcw capabilities check`
returning OK does **not** prove this — `Feature` is optional throughout `CAP_FIELDS`
(`tcw/store/base.py:668`), so a missing one passes; read the fields.

**Commit:** on its own.

## Task 3 — The skill, and every registration that must land with it

**Creates:** `skills/commands-pause-work/SKILL.md`.
**Modifies:** `skills/README.md`, `.codex-plugin/plugin.json`, `evals/coverage.py`.

One commit. Each of the last three is read by a test enumerating `skills/*/SKILL.md`.

### `skills/commands-pause-work/SKILL.md`

Frontmatter: the exact key set `skills/commands-drive-work-to-completion/SKILL.md` carries.
`name: commands-pause-work`; `dynamic_skill: true` with the siblings' trailing comment;
`allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write`. `when_to_use` must fire on
"pause", "stop for now", "hold on", "I'm about to lose connection", "I need to reboot", and
must **not** fire on finishing, abandoning or blocking work.

Body, in the spec's order:

1. Reach a coherent resting point — *parses and is intelligible*, not builds or passes.
2. **Ask whether to commit and push.** One question: commit-and-push, commit-only, or leave
   the tree alone. State the rule for silence explicitly — **no answer is a yes** — and why:
   an absent user is the cold-handoff case.
3. Commit and push the work-in-progress, if that was the answer, on the item's branch, marked
   as such.
4. Write `<stage-id>.handoff.md` in each affected item's folder, located with
   `tcw work path <slug>` — never composed. Say "lifecycle stage id", because `plan/<id>.md`
   is a second stage-id namespace (`tcw/store/fs.py:5627`). Valid ids: `request`, `spec`,
   `plan`, `implement`, `verify`, `postmortem`; when between stages, the one that would run
   next. **`inbox` is excluded** — there is no item folder yet — and the skill says so and
   why. **Remove any handoff already present** before writing. **No `tcw://` links**; refer
   to other items by bare slug, because `tcw validate` scans every `*.md` under the work root
   (`tcw/validate.py:62`, `:313`) and gates `complete` here (`tcw-config.yaml:74-76`).
   Contents: the five items the spec lists, branch and last commit among them.
5. Commit and push the handoff — a **second** push, and say why it is not covered by step 3:
   the handoff is written after that commit, and the store may be a different repository
   (`work.repository`). Say that nothing pushes the store for you: TCW publishes only on a
   transition (`tcw/store/fs.py:5281`) and a pause runs none.
6. Report — item(s), branch, whether the work reached the remote, what to type to resume — and
   if the user declined the commit, that the handoff exists only in this checkout. Then the
   silence rule: no further tool calls, no scheduled check-in, no background task left.

Also carry: **scale to what is in flight** (nothing in flight ⇒ no handoff, say so); that the
skill runs **no transition** and changes no status; and the status-per-stage table's
consequence in one line — a `backlog` pause leaves no claim, an `active` one keeps it and
needs no `--take-over`, and a tracker-configured node with a differing identity is the one
exception (`tcw/work/cli.py:2259`).

Route, do not restate: name the `work` skill for the stage ladder and `work-stage` for a
resumed stage.

### `skills/README.md`

One row in the verdict table, beside the other `commands-*` rows:
`commands-pause-work` | `SKILL.md` | **overridable**. The reason must say two things the
other four rows do not: that this skill is `overridable` rather than `fixed (Rule 2)`
**because it carries a procedure of its own**, and that the key here **records intent** —
there is no procedure id behind it, so nothing mechanises the override. Do not write the row
as though the fixed/overridable split were enforced.

### `.codex-plugin/plugin.json`

`interface.longDescription`: `sixteen skills` → `seventeen skills`; `four command skills` →
`five command skills`; add `` `commands-pause-work` `` **backticked** (the test matches the
backticked form) with a clause saying what it does.

### `evals/coverage.py`

Add `commands-pause-work` to `EXCLUSIONS` (`:34`) with its **own** reason. Do not extend the
four-name comprehension — its reason is false here. The honest reason: the skill's observable
outcome is an agent that stops and stays stopped, so a graded run has no produced artifact to
read and would have to measure an absence; and the handoff it writes is deleted by the resume
it would be graded against. Say a case becomes worth writing if the harness gains a way to
assert a run ended deliberately.

**Proves it:**
`pytest tests/test_dynamic_skill_marker.py tests/test_plugin_manifests.py tests/test_eval_coverage.py`
passes. Note the coverage test checks **key presence only** (`evals/coverage.py:96`), so it
cannot prove the reason is not a copy — that is checked by reading, and is why acceptance
criterion 5 says so.

## Task 4 — The resume side

**Modifies:** `skills/work/SKILL.md`, `skills/commands-drive-work-to-completion/SKILL.md`.

Without this the handoff has no reader and the design does not work.

- `skills/work/SKILL.md` "Finding your place" (`:42-48`) gains one step **before** artifact
  detection: look in the item's folder for a `<stage-id>.handoff.md`; if one is there, read
  it, let it inform where to pick up, and **delete it in the same step**. Keep it to two or
  three sentences: no test constrains this file's length —
  `test_each_router_stays_within_its_ceiling` applies to `stage-<id>.md`, not to
  `SKILL.md` — but the section is a router, and a router that grows into a procedure is the
  drift `skills/README.md`'s Rule 2 exists to prevent.
- `skills/commands-drive-work-to-completion/SKILL.md` gains one sentence pointing at that
  step, since it is the skill a user names when resuming.

**Proves it:** `pytest tests/test_skill_lifecycle_parity.py` passes; reading the edited
"Finding your place" shows the handoff check ordered before artifact detection, with the
delete attached to the read rather than deferred.

**Commit:** with Task 3, or on its own — both boundaries are green.

## Task 5 — The two enumerations in prose

**Modifies:** `skills/work/references/commands.md`, `README.md`.

- `commands.md:306-309` — "Four skills carry the everyday workflows" becomes five, with
  `commands-pause-work` added. The next sentence, "Each works by invoking the skill, under any
  harness, and each invokes the `work-stage` skill for the stage it runs", is **now false of
  one member**: this skill invokes `work-stage` only if the agent resumes into a stage.
  Reword so it is true of all five.
- `README.md:681-688` — add a row to the **Command skills: the everyday workflows** table in
  its neighbours' one-sentence, second-person style. No count sentence there, so nothing else
  moves.

**Proves it:** both files name `commands-pause-work`; the reworded `commands.md` sentence
read against all five skills makes no false claim.

## Task 6 — Prove the handoff is tolerated, across a transition

**Modifies:** nothing permanently.

The spec's survival claim is that an unregistered file rides a status transition because the
whole directory moves. Prove it rather than asserting it, on a scratch item — not on this one,
whose status this must not disturb.

```bash
scratch=$(tcw work new "Scratch: handoff tolerance probe" --tag tech-debt <<'EOF'
Temporary probe for the commands-pause-work item. Discard when done.
EOF
)
folder=$(tcw work path <scratch-slug>)
printf '# handoff\n\nprobe\n' > "$folder/implement.handoff.md"
git -C "$folder" add -- "$folder/implement.handoff.md"
git -C "$folder" commit -m "probe" -- "$folder/implement.handoff.md"
tcw validate; tcw work show <scratch-slug>; tcw work list
tcw work start <scratch-slug>          # backlog → active: the transition under test
ls "$(tcw work path <scratch-slug>)"   # the handoff must still be there
tcw work discard <scratch-slug> --reason "probe complete"
```

**Proves it:** `tcw validate` exits 0 with the file present; `tcw work show` / `tcw work list`
report the item no differently; and the file is still in the folder after `start` has moved
it. Also note whether `tcw work discard` carries or destroys it, and record the answer —
the spec's retention risk (`_require_retrievable`, `tcw/store/fs.py:4828`) turns on it.

**If survival fails,** the design is wrong and this returns to `spec` rather than being
worked around.

## Documentation Sync

Evaluated against `tcw work docs`; run as one pass over the finished diff.

| Entry | Trigger | Fires | Task |
| --- | --- | --- | --- |
| `README.md` | `Public-API` | **yes** — a new shipped skill is public surface | Task 5 |
| `docs/release-notes/upcoming.md` | `Public-API` | **yes** | Task 7 |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **yes** | Task 7 |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **yes, narrowly** | Tasks 4, 5 |
| `docs/guide/jira.md` | `Tracker-Change` | no | — |
| `skills/configure/references/<document>.md` | `Configuration-Key-Change` | no | — |

- **`Skill-Driven-Component` fires narrowly.** The trigger is written for a component changing
  — CLI surface, model, lifecycle, guardrails — and nothing under `tcw/` moves. What changes
  are facts inside the `work` skill's own documents: its command-skill enumeration (Task 5)
  and its resume router (Task 4).
- **`Tracker-Change` does not fire.** No `tcw work tracker` command changes and no
  `work.tracker` key changes. The skill *mentions* `_started_by_someone_else`'s effect, but
  describing existing behaviour is not changing it — and `docs/guide/jira.md` is the Jira
  guide, not the place a pause skill's caveat belongs.
- **`Configuration-Key-Change` does not fire.** `dynamic_skill` is skill frontmatter, not a
  key in `tcw-config.yaml`, a component config file, `docs/work/dod.yaml`, or a
  `TCW_PROJECT_<ID>` variable.

### Task 7 — Write the entries, and fix two that are already stale

**Modifies:** `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`.

- **New entries.** Release note, plain language: a user can now tell an agent to pause; it
  asks whether to commit and push, writes down what resuming needs, and waits. Name
  `<stage-id>.handoff.md`, since a user will see it in their item folder and needs to know
  what it is and that resuming removes it. Changelog, `Added`: the skill, its taxonomy Feature
  and capability, the resume-side router step, the manifest and coverage registrations.
- **Two existing entries go stale with this change and must be corrected in the same pass** —
  both are unreleased, for the version this ships in:
    - `docs/changelogs/upcoming.md:92` — "in the frontmatter of all **sixteen**
      `skills/*/SKILL.md`" → seventeen.
    - `docs/release-notes/upcoming.md:64` — "`commands-` still marks the **four** everyday
      workflow skills" → five.

  No test reads these files, which is exactly why they need naming here.

**Proves it:** both files name the new skill; neither contains "sixteen" or "four" in those
two sentences; `tcw validate` exits 0.

**Commit:** on its own, after the suite is green.

## Task 8 — Flip the capability at completion

**Modifies:** `docs/capabilities/skills/commands-pause-work/meta.yaml`.

`tcw capabilities set skills/commands-pause-work --status Supported`, as the final pre-freeze
step. The completion gate blocks `tcw work complete` while a `new:` path still reads
`Missing`.

## Verification

Beyond the suite:

1. **Nothing under `tcw/` changed** — `git diff --stat main...HEAD -- tcw/` is empty. The
   request's hard constraint; no test enforces it.
2. **`pytest`** whole, and **`tcw validate`** exits 0.
3. **The skill is discoverable by its trigger.** Read `when_to_use`: fires on "pause", "stop
   for now", "I'm about to lose connection"; does not fire on "finish this" or "drop this".
   No test can check a description's triggering.
4. **The skill stands alone under Codex.** Read `SKILL.md` as a Codex agent would: no
   Claude-only mechanism carrying a requirement, every instruction executable with `tcw` and
   git. The harness-compatibility rule bound at `spec`; nothing automated checks it.
5. **`evals/EXCLUSIONS`' reason is this skill's own**, not a copy — read it (AC 5; the test
   cannot see this).
6. **The reworded `commands.md` sentence is true of all five skills** — checked by reading.
7. **End-to-end, once:** pause this very item mid-implementation — answer the commit question
   both ways in turn, write `implement.handoff.md`, then read it back as if resuming with no
   memory. It must answer where the work stood, on which branch, and what to do next. Follow
   the resume path as written in Task 4's edit and confirm it finds and deletes the file.
8. **The push actually happened.** After the end-to-end pause, `git log origin/<branch>` shows
   both the WIP commit and the handoff commit. This is the defect the first draft shipped;
   check it rather than trusting the prose.

## Notes

- Tasks 1 and 2 are **not** run at the `plan` stage; they are the first tasks of
  implementation, so a plan sent back for changes leaves no orphan term or `Missing`
  capability behind.
- No blockers. `2026-09-15-make-start-take-over-recover-an-interrupted-claim-…` does not block
  this: a pause runs no transition and never meets the take-over path.
  `2026-09-10-record-a-work-item-s-branch-…` does not either — the branch is written into the
  handoff as text precisely because `state.yaml` carries it only for worktree items.
- **Worktree items are a known soft spot, left to implementation.** Inside `.worktrees/<slug>`
  a default `docs/work` store resolves to the worktree's own copy
  (`anchor_configured_path`, `tcw/store/fs.py:1446`), so a handoff written there sits on the
  `work/<slug>` branch and an agent resuming from the primary checkout will not see it. The
  skill should say: when paused inside a worktree, name the worktree and its branch in the
  report, so the resumer knows where to stand. This is a documentation fix, not a mechanism.
- The obvious follow-up — registering `handoff` in `WORK_SIDECARS` so `tcw` can see, validate
  and display it — is deliberately not filed yet. It needs the Python change this item
  excludes, and is better judged after the convention has been used than before.
