# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

<changes starting-hash="37ea512" ending-hash="37ea512">

### Fixed

- `.claude-plugin/plugin.json` no longer declares `"agents": "./agents/"`. Claude
  Code's manifest schema validates `agents` as a `./….md` file path or an array of
  them — `skills` takes a directory and `commands` takes either, but `agents` has no
  directory branch — so the value matched neither union member and installing the
  plugin failed with `Validation errors: agents: Invalid input`. Dropping the key
  restores the default `agents/` scan, which loads `tcw-post-mortem.md` and
  `tcw-verifier.md` exactly as intended. The key was introduced in 494eec9.

### Internal

- `tests/test_plugin_manifests.py::test_claude_agents_key_is_md_files_not_a_directory`
  — asserts any `agents` value in the Claude manifest is `.md` file paths, so a
  directory can't be reintroduced.

</changes>
