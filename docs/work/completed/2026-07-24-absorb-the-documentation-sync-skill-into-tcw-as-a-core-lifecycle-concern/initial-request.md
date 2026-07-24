# Absorb the documentation-sync skill into TCW as a core lifecycle concern

## Requested outcome

TCW currently **delegates** its documentation-sync behavior to an external plugin: `AGENTS.md`'s
`## Documentation Sync` section tells agents to invoke the `skill-cefailures:documentation-sync`
skill, and the `tcw-work` lifecycle references say only "evaluate Documentation Sync triggers"
without owning what those triggers mean.

Move that behavior **into TCW** so the TCW plugin owns and manages it, and make it a first-class
part of the TCW work lifecycle. After this change, a project driving TCW's work lifecycle gets
doc-sync trigger evaluation from a TCW-owned skill, with no dependency on `skill-cefailures`.

## Shape (decided)

- **Home:** a new dedicated skill `skills/documentation-sync/` (SKILL.md router + `references/*.md`),
  following TCW's progressive-disclosure skill convention (thin router, rare detail in references).
- **Lifecycle integration:** the `tcw-work` lifecycle references invoke the new skill at two gates —
  **plan-time** (surface predicted doc-update tasks in `plan.md`) and **completion-time** (evaluate
  triggers before `tcw work complete`) — mirroring how `tcw-work` already hands off to `tcw-capabilities`.
- **Enforcement:** **instruction-only.** No change to the `tcw` CLI or the storage model; `tcw work
  complete` is unchanged. The skill + lifecycle prose carry the behavior. (This keeps the
  storage-abstraction model clean — doc-sync is agent behavior, not a store operation.)

## Scope — what to absorb

Bring across, adapted to TCW:

- **Core trigger evaluation** — the trigger reference (`Public-API`, `Public-{Name}-API`,
  `Any-Code-Change`, `Only-Breaking`), the partition rule, the public-surface judgment call, the
  evaluation loop, and the plan-integration guidance (named-file tasks vs. one re-evaluation gate).
- **Release-notes/changelogs guidance** — RN-vs-changelog distinction, entry/hash-range format,
  version cross-check, existing-project migration offers. TCW already *uses* this structure
  (`docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`) but has no owned guidance doc for it.
- **Setup guidance** — how to scaffold a `## Documentation Sync` section into a project's CLAUDE.md
  (so other projects installing the TCW plugin can adopt it), as a reference and/or command.

Deliberately **out of scope / dropped**:

- **FOLLOWUPS.md** — dropped. TCW already tracks deferred work as `tcw work` backlog items; the
  absorbed guidance should encourage `tcw work new` for follow-ups instead of a `docs/FOLLOWUPS.md`
  standing log. Remove FOLLOWUPS references rather than porting them.
- **Cut-version** — already TCW-native via `scripts/cut_version.py` and `AGENTS.md` `## Versioning`.
  Do **not** port the external `:cut-version` command; the absorbed skill's "when to offer version
  options" guidance must defer to `scripts/cut_version.py`, not the external command.

## Rewiring TCW itself

- `AGENTS.md` `## Documentation Sync`: point the directive at the TCW-owned skill instead of
  `skill-cefailures:documentation-sync`.
- `tcw-work` lifecycle references (`task-lifecycle.md`, `epic-lifecycle.md`): tighten the loose
  "evaluate Documentation Sync triggers" pointers into explicit invocations of the new skill at the
  plan and completion gates.

## Constraints & non-goals

- No new `tcw` subcommand and no store-interface method (instruction-only; passes the abstraction
  litmus test by not touching the model at all).
- Keep the skill a thin router per TCW's skill-authoring rule; only split detail into references when
  it earns the indirection.
- Not a product/user-facing capability change to the `tcw` CLI — this is agent-facing tooling +
  process docs. (Confirm "no capability/taxonomy delta" during spec.)

## Related action (separate repo — NOT a TCW work item)

The user wants the original removed from the source plugin. `skill-cefailures`
(`github.com/brocef/skill-cefailures`) is **not** a TCW node, so this can't be a `tcw work` item in
this repo. Track it as a follow-up to open there (e.g. a GitHub issue) to remove/deprecate its
`documentation-sync` skill once TCW's copy lands. Decide at closeout whether to file it.

## Open questions for spec

- Setup guidance shape: a `references/setup.md` read on demand, a `commands/*.md` slash command, or both?
- Exactly how tightly to bind the lifecycle gates — inline the trigger loop into lifecycle prose, or
  keep a one-line "invoke documentation-sync" handoff (preferred, matches tcw-capabilities pattern)?
- Does the absorbed skill keep the generic "Documentation Sync section in any project's CLAUDE.md"
  framing (portable to other TCW-using projects), or narrow to TCW's own AGENTS.md only? (Lean portable.)

## Tags

`skills`, `docs`.
