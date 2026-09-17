# Plan: Fill the Codex gaps in the setup and stage skills, and give each skill one capability

Documentation only, sequential, on `main`. Skill files are edited only while no
suite run is in progress, because tests read them.

## Task 1 — `<plugin>` and the install command

- Modify `skills/setup/references/install.md:9`: replace "Under Codex there is no
  hook, and you run it." with a sentence giving
  `bash <plugin>/scripts/session_bootstrap.sh <plugin>`, defining `<plugin>` as the
  plugin's root folder (the one holding `skills/`, three levels above this file),
  saying the second (sentinel) argument can be left off because the check below runs
  it only when `tcw` is missing, and that it prints nothing on success or when it
  declines, so `tcw --version` afterwards is the check.
- Modify `skills/work-stage/SKILL.md` after its command block, and
  `skills/documentation-sync/SKILL.md` after its `<plugin>` sentence: `<plugin>` is
  the plugin's root folder, two levels above the folder this `SKILL.md` is in.
- Proof: criteria 1 and 3 by reading; criterion 2 by running the command against a
  scratch copy (`cp -R` of `skills/`, `scripts/`, `tcw/__init__.py`) with a `PATH`
  that has no `tcw` and no `pipx` — exit 0, nothing installed; the targeted skill
  tests `pytest tests/test_skill_lifecycle_parity.py tests/test_shipped_procedures.py
  tests/test_plugin_manifests.py`.

## Task 2 — one capability per skill

- Modify `docs/capabilities/work/run-a-lifecycle-stage/description.md`: delete the
  last two paragraphs.
- Modify `docs/capabilities/skills/work-stage/description.md`: add a paragraph with
  what they said that it does not — an ergonomic over `tcw work stage prompt` and
  nothing more, running no gate, the header in `prompt`'s output carrying that
  warning under either harness; the work item optional for every stage, with
  `<slug>` standing where a reference would go.
- Modify `docs/capabilities/work/complete-a-work-item/description.md:22`: add that
  `superseded` is conditional so a postponed request is never reported to its author
  as a refusal.
- Modify `docs/capabilities/skills/extras-triage-issues/description.md:4`: keep "The
  loop closes when the work item does", link
  [Complete a work item](tcw://C/work/complete-a-work-item) for which resolutions
  close the issue, and keep that a discard prints no checklist, so on a closure other
  than `done` the skill is the only reminder.
- Proof: criteria 4-6 by grep; `tcw capabilities check`.
- Create `capabilities.yaml` for this item with the four `changed:` paths.

## Task 3 — full suite (`pytest -q`).

## Documentation Sync

- `README.md` [Public-API] — `:89-90` already says the skill runs the install
  script, which is now true to its text; no change.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — fires on skill text: a
  `Changed` line.
- `docs/release-notes/upcoming.md` [Public-API] — fires lightly: Codex users are
  told how to run the install.
- `skills/<component>/SKILL.md` [Skill-Driven-Component] — this item edits skills
  directly; nothing further.
- `docs/guide/jira.md`, `skills/configure/references/*` — do not fire.

## Verification

The suite checks skill structure, not whether a Codex user can follow the text;
Task 1's scratch run is that check.
