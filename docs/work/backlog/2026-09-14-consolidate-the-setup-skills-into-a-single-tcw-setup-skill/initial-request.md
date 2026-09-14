# Consolidate the setup skills into a single tcw-setup skill

> Shaped during a brainstorming conversation on 2026-09-14.
>
> **Revised by the requester during `spec` (2026-09-14)** — these override the
> single-skill shape described below wherever the two disagree:
>
> 1. **Two skills, not one.** `tcw-setup` instructs agents how to set up TCW for
>    a project that does not use it yet. `tcw-config` instructs agents how to
>    change an existing project's TCW configuration.
> 2. **A taxonomy Feature for every top-level skill, in this item.** Each skill
>    shipped in `skills/` gets a Feature (examples given: `TCW Initialization
>    Skill`, `TCW Configuration Skill`), and capabilities map neatly onto those
>    Features — e.g. "Offer a skill dedicated to instructing agents how to set up
>    TCW for a project that does not currently use TCW". This covers all the
>    skills, not only the setup ones.
> 3. **Eval coverage is rebuilt.** Old eval cases tied to removed skills are
>    removed and new ones created. *Which* setup and configuration routes get
>    cases is left as an open question for the spec's reviewers.
>
> **Revised again after the first spec review (2026-09-14):**
>
> 4. **The configuration skill is named `tcw-configure`**, not `tcw-config`, so
>    its name never collides with the file `tcw-config.yaml`.
> 5. **One capability per skill, replacing the existing ones.** Each skill gets a
>    single capability, and the existing capabilities that describe what a skill
>    does are folded into it rather than kept beside it — even though that retires
>    stable capability paths.
> 6. **All configuration moves into `tcw-configure` now**, including keys
>    documented elsewhere today (`work.tracker`, `work.retain`,
>    `work.auto-commit-transitions`, `work.trunk-branch`, `connected-projects`),
>    not left for a follow-up.
> 7. **The reviewer's eval recommendation is accepted:** a configuration case
>    phrased with "set up", a project-initialization case on a fresh repository,
>    "did not open `tcw-setup`" checks added to cases B4 and B8, and B5 retargeted
>    to test routing across the axis skills rather than deleted.
> 8. **A large change is acceptable.** The goal is to clean up and simplify, so a
>    wide footprint is not a reason to hold back.
>
> **Revised after the second spec review (2026-09-14):**
>
> 9. **Replaced capabilities are deleted, not marked `Omitted`.** A separate item,
>    `2026-09-14-delete-a-capability-with-tcw-capabilities-rm`, adds the delete
>    command and lands first; this item is blocked by it.
> 10. **Declaring inheritance (`extends`) moves to `tcw-configure`** alongside
>     connected projects, even though it is stored in each component's own config
>     file rather than `tcw-config.yaml`.
> 11. **The broken `files_changed_exactly` eval check is fixed in this item.**
> 12. **Only capabilities whose main subject is a skill are folded in.**
>     Capabilities mainly about CLI behavior or the install hook stay, and just
>     mention the skill.
>
> **Revised after the plan was written (2026-09-14):**
>
> 13. **Delete the five per-stage skills** (`tcw-work-stage-request`,
>     `tcw-work-stage-spec`, `tcw-work-stage-plan`, `tcw-work-stage-implement`,
>     `tcw-work-stage-verify`) in this item as well. `tcw-work-stage` is sufficient
>     for every stage.
> 14. **Personal extras get a `tcw-extras-` prefix.** `autonomous-work` is not a
>     core skill but one the requester made for themself, so it becomes
>     `tcw-extras-autonomous-work`. `tcw-triage-issues` moves to extras too, as
>     `tcw-extras-triage-issues`, and its slash command is renamed to match
>     (`/tcw-extras-triage-issues`). Future skills of that kind use the same
>     prefix.

## What is being asked for

The plugin's skills serve two different moments, and today nothing about them
makes that visible:

1. **Setting up and configuring TCW for a project** — installing the CLI and
   plugin, starting a taxonomy, starting capabilities, binding a project's own
   instructions to lifecycle stages, declaring documentation entries.
2. **Using TCW once it is set up** — `tcw-work`, `tcw-taxonomy`,
   `tcw-capabilities`, and the stage skills.

A few skills fit neither (`tcw-report` is the example given); they are out of
scope for this item.

The usage skills should be the easiest to reach, so they keep their short names.
All setup material moves into **one skill, `tcw-setup`**, whose `SKILL.md` is
only a routing file: it says which reference document covers which part of TCW,
and the reference documents carry the actual setup instructions.

The agreed shape — all of these are documents inside the one skill, not
separate skills:

```
tcw-setup/
  SKILL.md           # routing only: which document covers which part
  references/
    install.md       # the CLI and plugin — once per machine, incl. a missing or stale CLI
    project.md       # tcw init / provision / first validate — once per repository
    taxonomy.md
    capabilities.md
    work.md
    docs-sync.md
```

The requester first proposed a single `plugin.md`; splitting it into
`install.md` and `project.md` was suggested in discussion and accepted, because
the two happen at different times and the model then reads only the one it needs.

### Decided by the requester

- **The skill map is deleted, not moved.** The first half of
  `skills/tcw-plugin/SKILL.md` (`# TCW skill map`) is usage orientation, not
  setup. Each usage skill's description already names its siblings, so it goes
  when `tcw-plugin` does. `spec` should confirm nothing in it is said nowhere
  else, and remove the "`tcw-plugin` maps the skills" line in
  `skills/tcw-work/SKILL.md`.
- **Documentation-entry setup is in scope.** `documentation-sync`'s setup
  material moves into `tcw-setup` alongside the rest.
- **The setup commands are replaced, not kept alongside.** `tcw-taxonomy-init`,
  `tcw-capabilities-init`, and `tcw-docs-sync-setup` go away in favour of the new
  skill. The point is simplification; two parallel ways to set things up would
  work against it. They are deleted outright with a changelog entry and **no**
  stub under the old names: nobody but the requester uses TCW yet, so there is
  no one to redirect.
- **Changing configuration later belongs here only if it stays small.** Include
  it in `tcw-setup` if that does not greatly increase the skill's size. If two
  skills make more sense, split into `tcw-setup` (first-time setup) and
  `tcw-config` (changing configuration afterwards) — still short, still
  predictable. Which of the two is for `spec` to decide against that size test.

### How this request got here

The first idea was a predictable suffix (`-setup` and/or `-config`) on a
separate setup skill for each part, e.g. `tcw-work-setup`. That was replaced by
the single routing skill above, because setup happens rarely, one entry point
means one name nobody has to guess, and it adds one skill description at session
start instead of several.

## Where setup material lives today

Recorded so `spec` can check nothing is missed, not as a decision about where
each piece ends up.

| Setup material                           | Current location                                                                   |
| ---------------------------------------- | ---------------------------------------------------------------------------------- |
| Installing / repairing the `tcw` CLI     | `skills/tcw-plugin/SKILL.md` (second half)                                         |
| Map of which skill does what             | `skills/tcw-plugin/SKILL.md` (first half) — usage orientation, not setup           |
| Starting a taxonomy                      | `commands/tcw-taxonomy-init.md` → `skills/tcw-taxonomy/references/init.md`         |
| Starting capabilities                    | `commands/tcw-capabilities-init.md` → `skills/tcw-capabilities/references/init.md` |
| Declaring documentation entries          | `commands/tcw-docs-sync-setup.md` → `skills/documentation-sync/references/setup.md` |
| Binding instructions to lifecycle stages | `skills/tcw-work/references/hooks.md`                                              |
| `tcw init` / `tcw provision` / first `tcw validate` | not covered by any skill today                                          |

## Notes

Points raised in discussion for `spec` to carry, not separately confirmed by the
requester:

- **Keep the broken-CLI trigger.** `tcw-plugin` is mostly opened when the CLI is
  missing or stale after the `SessionStart` hook failed, not at first setup. The
  `tcw-setup` description must name those situations or it will not be found.
- **`documentation-sync` keeps a one-line pointer** to its setup document once
  that moves, since the skill also serves projects that do not use TCW.

Constraints: none stated beyond the above. No deadline.

Reference material: asked; none provided.

## References

- `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source` — also
  reshapes what the plugin contains and names `skills/tcw-plugin` files; the two
  items touch the same install documentation and should not be done blind to
  each other.
- `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`
  — changes the same skills, and is meant to be driven by eval evidence; a
  restructure landing first changes what those evals measure.
- `evals/coverage.py`, `evals/evals.json` — name the current setup skills, so the
  eval harness moves with any rename.
- `tests/test_plugin_manifests.py`, `tests/test_documentation_sync_wiring.py` —
  hard-code current skill and command paths.
- `scripts/session_bootstrap.sh`, `.codex-plugin/plugin.json`, `README.md` — name
  `tcw-plugin` or the setup commands.
