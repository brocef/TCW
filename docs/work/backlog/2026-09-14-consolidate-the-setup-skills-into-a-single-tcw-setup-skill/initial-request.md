# Consolidate the setup skills into a single tcw-setup skill

> **Still being shaped.** This request is being refined during a brainstorming
> conversation. Sections marked _open_ are not yet decided.

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

The requester's proposed shape:

```
tcw-setup/
  references/
    plugin.md        # general plugin setup
    taxonomy.md      # taxonomy-specific setup
    capabilities.md
    work.md
```

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

Suggestions raised in discussion — _open_, not yet agreed by the requester:

- **Add `docs-sync.md`** so documentation-entry setup lives with the rest;
  `documentation-sync` keeps a one-line pointer, since it also serves projects
  that do not use TCW.
- **Split `plugin.md` in two**: `install.md` (the CLI and plugin, once per
  machine, including a missing or stale CLI) and `project.md` (`tcw init`,
  `tcw provision`, first `tcw validate`, once per repository).
- **Keep the broken-CLI trigger.** `tcw-plugin` is mostly opened when the CLI is
  missing or stale after the `SessionStart` hook failed, not at first setup. The
  `tcw-setup` description must name those situations or it will not be found.
- **Delete the skill map rather than move it.** Each usage skill's description
  already names its siblings; the router needs only a short list of parts.
- **Remove the three setup commands** (`tcw-taxonomy-init`,
  `tcw-capabilities-init`, `tcw-docs-sync-setup`) in favour of invoking the skill
  with an argument (`/tcw:tcw-setup taxonomy`), which also works under Codex. This
  renames things users may already type or name in their own `CLAUDE.md` or
  `tcw-config.yaml`, so it needs a changelog entry and possibly a one-release stub
  under the old names.

Other open questions:

- Does "setup" also cover changing configuration later (adding a lifecycle
  binding months in), or only first-time setup?
- Is `documentation-sync` in scope, given it is not `tcw-` prefixed and serves
  non-TCW projects too?

Constraints: none stated beyond the above. No deadline.

Reference material: asked in this conversation, not yet answered.

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
