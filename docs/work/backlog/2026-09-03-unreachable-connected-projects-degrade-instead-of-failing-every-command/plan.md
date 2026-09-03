# Plan — Unreachable connected projects degrade instead of failing every command

## Tasks

### 1. Split the registry's problem list into errors and unreachable edges

**Modifies** `tcw/store/project.py`.

Give `FsProjectRegistry` a second accumulator beside `_problems` — an ordered
list of unreachable edges, each carrying the config that declared the locator,
the declared id, and the locator string. Add `_unreachable(...)` beside
`_problem(...)` (`tcw/store/project.py:419`), deduplicating the same way.

`check()` keeps returning every problem, errors first, so no existing caller
loses information at this step. Add `unreachable()` returning the new list, and
leave `require_valid()` (`:187`) raising on `_problems` only.

Nothing calls `_unreachable` yet, so behavior is unchanged.

**Proves it:** `tests/test_project_registry.py` — a new test asserting a fresh
registry reports an empty `unreachable()`, and that an existing malformed-config
case still raises from `require_valid()`. Full suite green.

### 2. Reclassify the absent-target case

**Modifies** `tcw/store/project.py`.

In `_read_config` (`:246`), route the `not path.is_file()` branch to
`_unreachable` instead of `_problem`, still returning `None`. Every other branch
in that method — unparseable YAML, non-mapping config, missing or invalid `id`,
declared-key/id mismatch — stays an error.

`_visit` already handles a `None` config by returning early, so the id is absent
from `_by_id` and the graph holds one fewer node.

**Proves it:** `tests/test_project_registry.py` — a parent locator pointing at a
directory with no sentinel yields a registry that `require_valid()` accepts,
whose `parent()` is `None` and whose `unreachable()` names the declared id and
locator; a locator pointing at a directory whose `tcw-config.yaml` is malformed
still raises.

### 3. Stop an absent counterpart from disproving reciprocity

**Modifies** `tcw/store/project.py`.

In `_validate_reciprocity` (`:349`), both mismatch branches (`:365`, `:386`)
currently compare `_target_path(...)` against a config path. Before reporting,
check whether the counterpart's resolved path is present. When it is not, the
two nodes agree by id and the check passes; when it is, today's message stands
unchanged.

**Proves it:** `tests/test_project_registry.py` — three cases. A child whose
parent's child-locator resolves to an absent path validates clean. A child whose
parent's child-locator resolves to a *present* different node still reports
`child locator for '<id>' does not point back to <path>`. A parent and child
naming each other correctly still validates clean.

### 4. Name the absent node where a command needs it

**Modifies** `tcw/store/fs.py`.

Three call sites resolve a project id and currently cannot distinguish "never
declared" from "declared, not here":

- `_extended_component_roots` (`:966-974`) — the `extends` failure.
- `resolve_qualified_work_ref` / `qualified_work_ref_problem` (`:281`, `:366`) —
  a `<project-id>/<slug>` reference.
- `registered_project_id` (`:268`) — a target that is not registered.

Each consults `registry.unreachable()` when `registry.get(...)` returns `None`,
and when the id is there reports that it is declared in `<locator>` but not
reachable in this checkout. When the id is in neither, today's message stands.

**Proves it:** `tests/test_capabilities_federation.py` for the `extends` message
and `tests/test_qualified_ref.py` for the work-ref message — each asserting the
new wording names both the project id and the locator, and that an id that was
never declared still gets the old wording.

### 5. Decide each graph-enumerating caller

**Modifies** `tcw/store/fs.py`, `tcw/validate.py`.

The spec's second risk is that a smaller graph silently produces a smaller
answer. Read each enumerating caller and record the decision in a comment at the
call site:

- `child_nodes` / `parent_node` / `descendant_nodes` (`tcw/store/fs.py:221-247`)
  — a smaller topology is the correct answer; they already filter by work-store
  presence.
- `tcw/validate.py:154`'s duplicate-work-root scan — a smaller set cannot produce
  a false positive, only miss a collision that a complete checkout would catch.
- `tcw work reconcile`'s ancestor walk (`tcw/work/cli.py:420`) — an epic in an
  absent node cannot be found, and the rollup must say so rather than omit the
  slice silently.

Only the third needs code: `reconcile` reports the unreachable owner rather than
treating the item as unowned.

**Proves it:** `tests/test_epic_completable.py` — a slice whose initiative names
an id in an unreachable node is reported as such, and a slice whose epic is
present is unaffected.

### 6. Label unreachable edges in `tcw validate`

**Modifies** `tcw/validate.py`.

`_check` returns early on any graph problem (`tcw/validate.py:145-151`). Split
that: errors return early as they do now; unreachable edges are collected and
emitted with the rest of the report, prefixed so they read as "declared, not
reachable in this checkout" rather than as failures, and they do not on their own
make the run non-zero. Keep them in the JSON output under their own key so a
caller can tell them apart without parsing prose.

**Proves it:** `tests/test_validate.py` — a node with one absent parent exits 0
and names the parent; the same node with an additional real error exits non-zero
and reports both.

### 7. Documentation Sync

One pass over the finished diff, answering every entry whose trigger fired.

- **`README.md`** — [Public-API]. Fires. The Connected projects section
  (`README.md:330-345`) says cross-project operations "use only reciprocal
  registrations"; that sentence is now true only among nodes that are present.
  State the rule the way the store section already states its own: a locator is a
  fact about one machine, a store that is here always wins, and a node that is
  not here drops out rather than failing the command.
- **`docs/release-notes/upcoming.md`** — [Public-API]. Fires. Plain language: a
  checkout that has only some of the repositories in a project graph now works,
  and `tcw validate` tells you which connections it could not follow.
- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires. Changed: the
  registry's problem classification, the reciprocity rule, the three message
  sites, `tcw validate` exit behavior.
- **`skills/<component>/SKILL.md`** — [Skill-Driven-Component]. Fires for
  `tcw-work`: `references/cross-node-deltas.md:6` states connections "must be
  reciprocal", and `references/commands.md` § Addressing describes resolution
  across the graph. Both need the absent-node case. Check `tcw-capabilities` and
  `tcw-taxonomy` for federation wording in the same pass and update only what
  actually asserts the old rule.
- **`docs/capabilities/cli/host-multiple-projects-in-one-repo/description.md`** —
  the changed capability recorded in `capabilities.yaml`. Its "fail closed when
  either side is missing or inconsistent" sentence is the contract this item
  changes; reword it to separate missing from inconsistent. Drive it with the
  `tcw-capabilities` skill, not by hand.

## Verification

What the suite cannot check:

- **The real cloud case.** The reproductions in `intake.md` were run against a
  `proposit-app` checkout with no orchestration repository. Re-run
  `tcw work list`, `tcw work nodes` and `tcw validate` in `apps/server` of such a
  checkout and paste the output into `outcome.md`. A fixture cannot stand in for
  this: the fixtures are built by TCW and agree with themselves, while the
  proposit configs were written months ago by someone with a different directory
  layout, which is the whole point.
- **That a typo is still findable.** Introduce a deliberately misspelled locator
  in a scratch node and confirm `tcw validate` names it clearly enough that a
  user would notice. This is the spec's first risk and it is a judgment call
  about wording, not an assertion.
- **No message regressions.** Read the diff for every string this item touches
  and confirm none of them now says "no tcw node here" for a node whose config is
  present.

## Notes

Task order keeps the suite green at every boundary: 1 adds an unused
accumulator, 2 switches one branch onto it, 3 relaxes a check that 2 makes
reachable, 4-6 improve reporting on top of a graph that already degrades. The
riskiest change is 3, and it lands after 1-2 have given it tests to sit on.

The sibling defect in `_extended_component_roots` (`tcw/store/fs.py:977`,
recorded in the spec's Notes) is deliberately untouched by task 4, which changes
only the message that call site emits and not how it composes the path. File it
separately.
