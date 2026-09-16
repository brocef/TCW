# Drop the `tcw-` prefix from the plugin's skill and agent names

Every skill this plugin ships is already scoped by the plugin name when it is
invoked, so the `tcw-` on the front of the skill's own name is a second copy of
information the namespace has already supplied. Under Claude the plan-work skill
is `/tcw:tcw-commands-plan-work`; under Codex it is
`$tcw:tcw-commands-plan-work`. The doubled `tcw` reads as a stutter, it is more
to type, and it makes the names harder to scan in a list — it costs the user time
and gives nothing back.

Drop the prefix, so the same skill is `/tcw:commands-plan-work` and
`$tcw:commands-plan-work`.

## What the requester decided

Asked about three questions the request leaves open, the requester chose:

1. **Strip `tcw-` only.** The `commands-` and `extras-` groupings introduced by
   the recent skill restructure stay: `tcw:work`, `tcw:capabilities`,
   `tcw:work-stage`, `tcw:commands-plan-work`, `tcw:extras-report`. They still
   sort and read as families in a skill listing, which the bare names would lose.
2. **Rename the three subagents too.** `agents/tcw-backlog-auditor.md`,
   `tcw-verifier.md` and `tcw-post-mortem.md` are invoked as
   `tcw:tcw-backlog-auditor` and carry exactly the same stutter. Leaving them
   would also put `tcw:tcw-post-mortem` (the agent) beside `tcw:post-mortem`
   (the skill), which is the confusion this request is trying to remove.
3. **Rename the matching taxonomy Features and capability entries to match.**
   TCW's own ledgers name each skill twice more — a Feature `tcw-work-skill` and
   a capability folder `docs/capabilities/skills/tcw-work/`. Both should end up
   naming the skill that actually ships.

## Constraints

- **`documentation-sync` is already prefix-free** and is the shape the rest
  should match. It is evidence the prefix was never load-bearing, and it should
  not change.
- **Historical records are not renamed.** Past changelogs, release notes, and
  the lifecycle artifacts of completed and backlog work items say `tcw-work`
  because that is what the skill was called when they were written. Rewriting
  them would falsify the record.
- **This is a breaking change for anyone who types the old names**, and for any
  project that has bound one in `tcw-config.yaml`. How much that matters, and
  whether anything should soften it, is for the spec to judge.

## Notes

- The requester was asked for reference material and had none of their own to
  add; the references below are what this stage found in the repository.
- No deadline was given.
- Nothing was declared out of scope beyond the constraints above.

## References

- `skills/` — the fifteen shipped skills. Fourteen carry the prefix in both the
  directory name and the `name:` frontmatter; `documentation-sync` does not.
  This is the thing being renamed.
- `agents/tcw-backlog-auditor.md`, `agents/tcw-verifier.md`,
  `agents/tcw-post-mortem.md` — the three subagents decision 2 brings in.
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` — the four
  manifests. The Codex one enumerates every skill by name in its prose
  `longDescription`, so it names all fifteen and cannot be missed.
- `tests/test_plugin_manifests.py` — already guards that the Codex description
  counts and names every shipped skill, reading the names from the `skills/`
  directory. It will fail the moment a directory is renamed and the prose is
  not, which makes it the rename's first safety net rather than an obstacle.
- `tests/test_skill_flow.py`, `test_skill_lifecycle_parity.py`,
  `test_skill_path_pointers.py`, `test_documentation_sync_wiring.py`,
  `test_shipped_prompts.py`, `test_repo_lifecycle.py` and others — the suites
  that reference skill names directly. They say how much of the rename is
  mechanical and how much is asserted somewhere.
- `evals/coverage.py` and `evals/evals.json` — the eval harness keys coverage
  and eval cases by skill name, so the rename reaches the instrument that
  measures the skill layer, not only the skills.
- `tcw-config.yaml` — its `work.documentation` block both names skills in a
  description (`tcw-work`, `tcw-capabilities`, `tcw-configure`) and carries a
  documentation entry whose `path` is `skills/tcw-configure/references/…`. The
  rename changes a configured path, not only prose.
- `docs/capabilities/skills/` and `tcw taxonomy list` — the capability folder
  and Feature per skill that decision 3 covers. Relevant because neither
  `tcw capabilities` nor `tcw taxonomy` has a rename or move verb today: only
  `add` and `rm`. The spec has to pick a route through that.
- `tcw/` — the Python CLI. Notable for what it does *not* contain: one
  docstring in `tcw/work/templates.py` mentions a skill path, and skill names
  are otherwise opaque `skill:` binding refs. The rename is a plugin, docs and
  test change, not a CLI behavior change.
- The `proposit-orchestration`, `proposit-app` and `proposit-core` repositories
  in this workspace — downstream consumers. They name TCW skills in prose in
  their `AGENTS.md` and in `tcw-config.yaml` documentation descriptions, but
  none of them binds a skill in a lifecycle `skill:` hook, so their
  configuration does not break. Their prose pointers do go stale.
