# Personal configuration: user identity and per-user overrides

TCW 3.0 (epic [TCW-68](https://proposit.atlassian.net/browse/TCW-68)) has one shared
configuration file per project, `tcw-config.yaml`, tracked in git and read the same
way by everyone on the team. That leaves no place for a fact about one person: who
they are, or how they personally like an agent to work a stage. This slice adds that
place without letting it change anything the team relies on.

## What is wanted

1. **Untracked personal configuration, in layers.** Configuration is read from four
   layers, lowest first: TCW's built-in defaults, `tcw-config.yaml`, a user-wide file
   (`~/.config/tcw/config.yaml`, honouring `XDG_CONFIG_HOME`), and a per-project
   `tcw-config.local.yaml` next to `tcw-config.yaml` that is never tracked. A higher
   layer wins. `TCW_NO_PERSONAL_CONFIG=1` skips both personal layers, for tests and CI.
   Personal layers apply only to the project a command acts on; other projects
   (upstreams, delegation targets) are read from their tracked file alone.
2. **Predictable merging.** Mappings merge key by key. The `prompt`, `pre`, `post`
   and `procedures` lists resolve through an `inherit` chain: a layer that does not set
   the list keeps what the layer below resolved; a layer that sets it replaces it,
   unless the list contains one `inherit: true` entry, which stands for the list the
   layer below resolved, at that position. `builtin: true` goes: at the team layer,
   `inherit: true` *is* the built-in content. Other lists are replaced whole.
3. **A fixed list of what a person may override.** One allowlist of key paths. Stage
   `prompt` and `post`, `procedures`, credential variable names and `user.*` are on
   it. Everything else is shared, including any key added later unless it is added to
   the list. `user.*` is personal only. A personal file that sets a shared key makes
   every command that loads config exit 1, naming the file and the key, except
   `tcw config show --origin`, which still runs so the problem can be found.
4. **A way to see the result.** `tcw config show [--origin]` prints the effective
   configuration, and with `--origin` the layer each value and each list entry came
   from. `tcw work stage prompt` says on stderr when personal layers changed the
   prompt, and `advance` names the layer of a `post` hook that failed.
5. **One identity, with no guessing.** Jira mode uses the Jira credentials. Filesystem
   mode uses `user.name` from personal configuration, matched exactly (case-sensitive)
   against an item's `assignee`. `TCW_WORK_OWNER` and the git `user.name` /
   `user.email` fallback are removed. Commands that need an identity (`list --mine`,
   `--assign-me` on `new` and `edit`) say how to set one when there is none.
6. **House rules.** Secrets never go in config files; config names environment
   variables. Commands that edit config write only `tcw-config.yaml`; personal files
   are edited by hand. `tcw init` adds `tcw-config.local.yaml` to the `.gitignore`
   next to `tcw-config.yaml`, or skips with a notice outside a git repository, and
   `tcw validate` warns if the file is tracked. Relative paths in a personal file
   resolve from that file's own directory.

## Constraints

- **Simplicity first.** One loader, one allowlist, one merge rule. This ships in
  3.0.0, so breaking changes are expected and there is no 2.x compatibility code.
- **TCW-69's model is fixed.** This slice builds on TCW-69's finished spec (stage
  table, `work.*` configuration shape, `advance`, exit codes) and does not redefine
  it. Where it needs TCW-69 to change, it says so.
- **Abstraction litmus test** ([`docs/lifecycle/abstraction.md`](../../../lifecycle/abstraction.md))
  and **harness compatibility** ([`docs/lifecycle/harness.md`](../../../lifecycle/harness.md)):
  everything that must happen is done by the `tcw` CLI, the same under Claude and
  Codex, and works in both work backends.
- **TCW never changes git state.** It may read git (for example, to see whether the
  local file is tracked) and may write `.gitignore` as a file.

## Out of scope

- Display preferences and any personal setting not listed above (the original
  decision record mentioned display preferences; the ticket dropped them).
- The final command surface and exit-code table (TCW-73), the Jira backend's own
  credential handling (TCW-71), the stage prompt text (TCW-74), the user guides
  (TCW-75), and the migration guide (TCW-76).

## Notes

- **No user to ask.** This request was written by an agent from the ticket and the
  epic's reference pack on 2026-10-01; nobody was available to question. Everything
  under "What is wanted" restates the ticket ([TCW-72](https://proposit.atlassian.net/browse/TCW-72),
  held in `intake.md`), including its "Update from TCW-69's spec" section. Reference
  material was not asked for; the references below are the ones the epic's pack
  supplies.
- **Open question the ticket hands to `spec`:** whether "where project X lives on
  this machine" moves from the `TCW_PROJECT_<ID>` environment variable into personal
  configuration, or both stay.
- **Assumption:** this slice lands after TCW-70 has wired TCW-69's model into the
  CLI, because `list --mine`, `--assign-me`, `stage prompt` and `advance` must exist
  as 3.0 commands for the identity and override rules to reach a user.
- **Assumption:** `tcw config show` is a top-level command whose name TCW-73 fixes
  and whose behavior this slice owns, as TCW-73's ticket says.
- **Assumption:** the `work.hooks.timeout` and `work.hooks.output-cap` keys that
  TCW-69 added are not named by the ticket either way, so `spec` must classify them.
- **Self-hosting.** This changes `tcw/` itself, so from implementation onwards the
  repository's own board is driven by editing files, not through the CLI, as
  `CLAUDE.md` requires.

## References

- [TCW-72](https://proposit.atlassian.net/browse/TCW-72) (`intake.md`): the ticket;
  the agreed decisions for this slice.
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68) and its attached
  `TCW-68-design-decisions-2026-09-30.md`: the epic's vision ("room for each person")
  and the original personal-configuration record, which the ticket refines.
- TCW-69's `spec.md` and `plan.md` (in this board, item
  `2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance`):
  the `work.*` parser, binding lists and `advance` outcome this slice extends.
- [TCW-71](https://proposit.atlassian.net/browse/TCW-71): Jira identity and
  credential variable names, which personal configuration must be able to override.
- [TCW-73](https://proposit.atlassian.net/browse/TCW-73): owns the names of
  `tcw config show`, `list --mine` and `--assign-me`, and the exit-code table.
- [TCW-75](https://proposit.atlassian.net/browse/TCW-75): links to the
  shared/overridable table this slice writes in the configure skill's references.
- [TCW-76](https://proposit.atlassian.net/browse/TCW-76): the migration guide, which
  turns `builtin: true` into `inherit: true`.
- `tcw/store/project.py`: today's project registry and the `TCW_PROJECT_<ID>`
  override that the open question is about.
- `tcw/work/cli.py` (`_local_owner`): today's `TCW_WORK_OWNER` and git identity
  fallback, which this slice removes.
