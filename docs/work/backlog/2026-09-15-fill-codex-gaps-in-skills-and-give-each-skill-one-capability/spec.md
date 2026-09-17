# Spec: Fill the Codex gaps in the setup and stage skills, and give each skill one capability

## Capability changes

- **changed:** `work/run-a-lifecycle-stage` — loses its two paragraphs about the
  `work-stage` skill; it describes the three CLI verbs only.
- **changed:** `skills/work-stage` — gains what those paragraphs said that it did
  not: the skill is an ergonomic over `prompt` with no gate of its own, the work
  item is optional for every stage, and without one `<slug>` stands in its place.
- **changed:** `work/complete-a-work-item` — becomes the one home of the
  issue-closing rules, including why `superseded` closes only an absorbed request.
- **changed:** `skills/extras-triage-issues` — links to that home instead of
  restating the rules.

## Problem

1. `skills/setup/references/install.md:9` ends "Under Codex there is no hook, and
   you run it." It never says what "it" is invoked with. The script's header
   (`scripts/session_bootstrap.sh:4-10`) documents `[plugin-root] [sentinel-path]`
   and says the arguments exist "so the setup skill can run this under Codex".
   `README.md:89-90` tells Codex users the skill "runs the same install script".
2. `skills/work-stage/SKILL.md:47`, the manual fallback for a harness that does not
   inject commands, reads `cat <plugin>/skills/work/references/lifecycle/stage-$stage.md`
   and never says what `<plugin>` is.
3. `docs/capabilities/work/run-a-lifecycle-stage/description.md` ends with two
   paragraphs ("Under Claude I can take both halves in one read." and "And I can
   ask for any stage by name.") describing the `work-stage` skill, which has its own
   capability, `docs/capabilities/skills/work-stage/description.md`.
4. The issue-closing rules (`done`, `duplicate`, `wontfix` close; `superseded` only
   when absorbed; a discard prints no checklist) are stated in both
   `docs/capabilities/work/complete-a-work-item/description.md:22` and
   `docs/capabilities/skills/extras-triage-issues/description.md:4`.

Sibling sweep, repo-wide: `grep -rn "<plugin>" skills` also finds
`skills/documentation-sync/SKILL.md:69`, whose fallback reads
`<plugin>/tcw/work/procedures/documentation-sync.md` with the same undefined
placeholder. It is included; nothing else matches.

## Goals

- A Codex user following `install.md` can run the bootstrap script from the text
  alone.
- A reader of `work-stage`'s or `documentation-sync`'s fallback can locate
  `<plugin>` under any harness.
- Each of the two skills is described by one capability, and the issue-closing
  rules live in one capability with a link from the other.

## Non-goals

- The script itself, and any test coverage or eval changes (tracked in the two
  items the request names).
- Skills other than `setup`, `work-stage` and `documentation-sync`.

## Design

1. In `install.md`, replace the last sentence with: under Codex, run
   `bash <plugin>/scripts/session_bootstrap.sh <plugin>`, where `<plugin>` is the
   plugin's root folder — the folder that holds `skills/`, three levels above this
   file. The sentinel argument is left off: the check below already stops when
   `tcw` is present, so the script is only run when it is missing, and the
   sentinel only saves a reinstall on a later run. Say that the script prints
   nothing on success or when it declines, so `tcw --version` afterwards is the
   check.
2. In `work-stage/SKILL.md`, add one sentence after the block: `<plugin>` is the
   plugin's root folder, two levels above the folder this `SKILL.md` is in. The
   same sentence goes after `documentation-sync/SKILL.md`'s `<plugin>` line.
3. Move the missing facts from `run-a-lifecycle-stage` into `skills/work-stage`
   and delete the two paragraphs; `run-a-lifecycle-stage` keeps its `validate`
   paragraph, which is about the CLI verb.
4. `complete-a-work-item` keeps its paragraph and gains the reason `superseded` is
   conditional (a postponed request is never reported to its author as a refusal).
   `extras-triage-issues`' fourth paragraph keeps "The loop closes when the work item
   does" and links to `complete-a-work-item` for which resolutions close the issue,
   plus the one fact specific to the skill: on a closure other than `done` it is the
   only reminder.

## Acceptance criteria

1. `install.md` contains `scripts/session_bootstrap.sh` and says what `<plugin>` is.
2. In a scratch copy of the plugin root, with `tcw` absent from `PATH`, the command
   as written exits 0; the script's own logic decides the rest (not re-tested here).
3. `skills/work-stage/SKILL.md` and `skills/documentation-sync/SKILL.md` say what
   `<plugin>` is, and that location resolves:
   two levels above `skills/work-stage/` is the repository root, which holds
   `skills/work/references/lifecycle/stage-spec.md` and
   `tcw/work/procedures/documentation-sync.md`.
4. `grep -n "work-stage" docs/capabilities/work/run-a-lifecycle-stage/description.md`
   finds only the `validate` paragraph.
5. `skills/work-stage`'s description states the optional item, `<slug>` stand-in,
   and that the skill runs no gate.
6. The phrase "only when the superseding item absorbed" appears in exactly one
   capability description; `extras-triage-issues` links `tcw://C/work/complete-a-work-item`.
7. `tcw capabilities check` passes; the full suite passes.

## Risks

- Tests that read skill text (`tests/test_skill_lifecycle_parity.py`,
  `tests/test_shipped_procedures.py`) may pin the exact fallback block. The added
  sentence goes after the block, not inside it.
