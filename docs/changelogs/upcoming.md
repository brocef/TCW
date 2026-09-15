# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Changed

- **Every shipped skill and agent name drops the `tcw-` prefix.** The plugin id
  already qualifies a skill at the point of use (`/tcw:<skill>` under Claude,
  `$tcw:<skill>` under Codex), so the prefix was a second copy of information the
  namespace had already supplied. Breaking: the old names do not resolve, and
  neither harness has a skill-alias mechanism to soften it.
    - 15 skill directories under `skills/`, each with its `SKILL.md` frontmatter
      `name`: `tcw-work` → `work`, `tcw-work-stage` → `work-stage`,
      `tcw-work-create` → `work-create`, `tcw-capabilities` → `capabilities`,
      `tcw-taxonomy` → `taxonomy`, `tcw-setup` → `setup`, `tcw-configure` →
      `configure`, `tcw-post-mortem` → `post-mortem`, the four `tcw-commands-*`
      and the three `tcw-extras-*` to `commands-*` and `extras-*`.
      `documentation-sync` is unchanged; it never carried the prefix.
    - 3 agent files under `agents/`, each with its frontmatter `name`:
      `tcw-backlog-auditor` → `backlog-auditor`, `tcw-verifier` → `verifier`,
      `tcw-post-mortem` → `post-mortem`. No manifest lists them — the Claude
      manifest carries no `agents` key and the directory is auto-loaded — so only
      the files and their references changed.
- **15 taxonomy Feature slugs** lose the prefix (`tcw-work-skill` → `work-skill`,
  …). Display names are deliberately untouched: `TCW Work Skill` stays, matching
  `documentation-sync-skill`, which already paired a `TCW …` display name with an
  unprefixed slug. `relatesTo` and `vocabulary` are carried over verbatim, with
  `work-create-skill`'s reference to `work-skill` re-pointed.
- **15 capability paths** under `docs/capabilities/skills/` lose the prefix, each
  keeping its name, `Status`, `Subject`, `Planning doc` and body, and pointing at
  its renamed `Feature`.
- `tcw-config.yaml`'s `Configuration-Key-Change` documentation entry path is now
  `skills/configure/references/<document>.md`. This is the only place the rename
  changed configuration rather than prose.
- Live references followed throughout: the 16 `SKILL.md` bodies and everything
  under `skills/*/references/`, `README.md`, `docs/guide/`, `docs/lifecycle/`,
  `.codex-plugin/plugin.json`'s `longDescription`, `evals/` (`coverage.py`'s
  `EXCLUSIONS`/`PARTIAL` keys, `evals.json`, `grade.py`, `assets/gen_requirement.py`),
  `scripts/session_bootstrap.sh`, `tcw/work/templates.py`'s docstring, and `tests/`.

## Added

- `test_skill_frontmatter_name_matches_its_directory` and
  `test_agent_frontmatter_name_matches_its_file`
  (`tests/test_plugin_manifests.py`) assert a declared `name` equals the
  directory or file it sits in. The existing frontmatter test checked only that
  `name` was _present_, so a directory rename that left its frontmatter behind
  passed the whole suite.
- `test_no_shipped_name_repeats_the_plugin_id` asserts no skill directory or
  agent stem begins with the plugin id plus `-`, reading the id from
  `.claude-plugin/plugin.json` rather than hardcoding it, so the rule survives a
  plugin rename and refuses the prefix returning one skill at a time.
- `DELETED_NAMES` (`tests/test_skill_lifecycle_parity.py`) gains the 17 distinct
  old names, and `LIVE_ROUTES` gains `agents` and `tcw-config.yaml` — both
  shipped surfaces that name skills and neither previously in the guard's reach.

## Internal

- The frontmatter parse in `tests/test_plugin_manifests.py` is extracted to
  `_frontmatter` and shared by all three frontmatter tests.
- `test_a_shared_name_prefix_cannot_stand_in_for_the_shorter_name` demonstrated
  its discrimination against `tcw-work-stage-spec`, a retired skill. After the
  rename `work-stage` sits inside that name as an infix rather than a prefix, so
  the test now uses the live pair — `work` is a prefix of `work-stage` and
  `work-create` — which is the same collision class on names that still ship.
- Capability and Feature ids are regenerated. The CLI has no rename verb on
  either axis, so each entry was re-created with `add` + `set` and the old one
  removed with `rm`; an id does not survive that. Nothing reads these ids today.
  A `tcw capabilities mv` / `tcw taxonomy mv` would have made the migration two
  loops of one command and is filed as follow-up work.
