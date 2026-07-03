# Bring plugin skills into full agentskills/Claude spec compliance

Two independent spec audits (agentskills.io/specification.md and
code.claude.com/docs/en/skills.md) found **zero hard violations** in the four
plugin skills (`tcw-work`, `tcw-taxonomy`, `tcw-capabilities`, `tcw-plugin`) but
a consistent set of underutilized spec capabilities and a couple of convention
deviations. This item closes those gaps. Command-layer skills under `commands/`
(`tcw-plan-work`, `tcw-drive-work-to-completion`, `tcw-init`, `tcw-doctor`,
etc.) are in scope where the change belongs at the command layer (dynamic
injection, `disable-model-invocation`).

## Product changes

None (no user-facing capability delta). These are packaging/metadata and
authoring-quality changes to the skill files themselves. The one adjacent
user-visible effect: after `allowed-tools`, a fresh plugin install runs `tcw`
without a permission prompt per command.

## Technical changes

1. **`allowed-tools` on all four skills** — the headline gap. The skills are
   pure `tcw`-CLI drivers; the friction-free behavior on this machine comes from
   machine-local `.claude/settings.local.json` allowlisting that does **not**
   ship with the plugin. Start from `Bash(tcw *)`; also evaluate `Bash(git *)`
   and `Read`/`Edit` where skills read/edit work artifacts. `tcw-plugin`
   additionally needs `Bash(pipx *)` (and whatever `docs/setup.md` /
   `docs/doctor.md` actually invoke — `pip`, `python3`). Decide per-skill scope
   rather than blanket-pasting.

2. **Reduce reference chains to 1 level.** `tcw-work/SKILL.md → docs/lifecycle.md
   → {task,epic}-lifecycle.md` is two hops. Either link the leaves directly from
   SKILL.md (fold the epic/task dispatch inline) or document the two-hop as
   intentional. Also check the `decompose.md ↔ cross-node-epic.md` lateral
   cross-links.

3. **`disable-model-invocation: true` for install/side-effecting actions.**
   `tcw-plugin`'s install/repair actions run `pipx install`/`--force`. Keep the
   orientation skill model-invocable, but gate the install actions behind the
   existing `/tcw-init` and `/tcw-doctor` commands with
   `disable-model-invocation: true`. Sweep all skills/commands for any other
   entry point that should not be model-invoked.

4. **Rename `skills/*/docs/` → `skills/*/references/`** in every skill, updating
   all in-SKILL.md links. **Scoped to the skill-local `docs/` dirs only** — the
   repo-level `docs/` tree (`docs/work/`, `docs/changelogs/`,
   `docs/release-notes/`) is unrelated and stays untouched. Matches the spec's
   named optional directory. Cosmetic but cheap. **Verification step:** grep the
   repo for the old `skills/*/docs/` paths (SKILL.md links, `.claude-plugin/`
   manifests, any tests) and confirm every link resolves after the move.

5. **Dynamic context injection at the command layer.** For arg-taking commands,
   inline live state — e.g. `tcw-drive-work-to-completion` opens with
   `` !`tcw work show {first arg}` ``; Resume/board commands can open with
   `` !`tcw work list --status active` ``. Command layer only — never in the
   always-on router skills (would run `tcw` on every auto-load even when it's
   not installed). Verify the exact arg-substitution syntax the harness supports.

## Meta changes

6. **`metadata` version + author** on each skill. Wire `version` into
   `scripts/cut_version.py` so it stays in lockstep with the existing 5 files
   (don't add a 6th hand-maintained copy). `author` = project author. Note:
   `tests/test_plugin_manifests.py` currently guards that the 5 known version
   files agree — wiring skill versions in means **extending that test** to cover
   the skill files too. If that's more machinery than it's worth, drop skill
   `version` and keep only `author` (see open questions).

7. **`compatibility` on `tcw-plugin`** — requires **Python 3.11+**
   (`pyproject.toml` `requires-python = ">=3.11"`), installs via pipx from the
   plugin clone. The three axis skills don't need `compatibility`.

8. **`when_to_use` field** — split the trigger-phrase enumeration out of
   `description` into the dedicated `when_to_use` field (shares the same
   1,536-char cap). Keep the "what it is" sentence in `description`, lead with
   the key use case.

9. **`license: Apache-2.0`** (SPDX id) on each skill — matches the repo's
   existing Apache-2.0 `LICENSE`.

## Documentation sync (expected to fire)

- `skills/*/SKILL.md` [Skill-Driven-Component] — this item *is* the skill change.
- `scripts/cut_version.py` — if `metadata.version` is wired into the release bump.
- `CLAUDE.md` skill-authoring note + versioning section — may need updates if the
  version-bearing file count changes or the `references/` convention is adopted.
- `docs/changelogs/upcoming.md` [Any-Code-Change].
- Release notes only if any user-visible effect ships.

## Open questions for planning

- Exact `allowed-tools` scope per skill (writes gated or pre-approved?).
- Does wiring skill `metadata.version` into `cut_version.py` create a 6th
  version file the manifest test must guard, or is it derived at build time?
- Confirm harness syntax for command arg substitution in `!`...`` injection.
