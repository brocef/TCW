# Spec — Inherit work.tracker from parent nodes, key by key

## Capability changes

One new capability, added `Missing` when implementation starts and flipped to
`Supported` by this item's completion:

- `work/inherit-tracker-settings-from-parent-nodes` — "Inherit tracker settings
  from parent nodes", carrying `Feature=external-work-tracker` and
  `Planning doc` pointing here.

`work/inspect-external-tracker-work` keeps its status. Its description gains
one sentence saying the settings it describes may come from parent nodes.

A separate capability rather than a longer description, because this is a
different thing a developer can do: configure one tracker for a whole
workspace. Reading tickets was already possible without it.

## Problem

1. **Tracker settings are read from the node's own file only.**
   `FsWorkStore.tracker_config` and `tracker_problems` (`tcw/store/fs.py:5284`,
   `:5290`) both parse `self._work_config().get("tracker")`, and
   `_work_config` (`tcw/store/fs.py:5052-5059`) reads only this node's
   `tcw-config.yaml`. A workspace whose nodes read one Jira project repeats
   the whole block in every node.
2. **A forgotten copy goes unnoticed.** Each copy is checked alone, so a node
   left holding an old transition name or site still parses and still runs.
3. **A damaged copy disables that node entirely.** The parser fails closed:
   any problem returns no config at all (`tcw/store/base.py:907-921`, `:994`).
   That rule is right and stays. It just means every copy is another chance
   to break a node.
4. **Nothing to build on.** No setting under `work:` inherits between nodes
   today. A sweep of the 14 `_work_config()` readers in `tcw/` found none that
   consults another node, and no other code reads `work.tracker` directly
   (`tcw/store/fs.py:5287` and `:5294` are the only two). The project graph can
   already walk upward: `ProjectRegistry.ancestors()` (`tcw/store/base.py:251`)
   returns the direct parent first, then the rest. The filesystem registry
   implements it at `tcw/store/project.py:207-215`, and it keeps the raw config
   of every node it loaded (`_Config.raw`, `tcw/store/project.py:124-129`).

## Goals

1. A node's tracker settings are its own `work.tracker` keys merged over those
   of every ancestor. The nearest node that sets a key wins that key.
2. Ancestors without a work store of their own still contribute their settings.
3. Nested mappings (`credentials`, `transitions`) merge key by key in the same
   way.
4. `tracker: none` switches the tracker off for the node that writes it.
5. `tcw validate` and `tcw work tracker list|show` all use the merged settings.
   Each problem names the file the offending value came from.
6. Keys added under `work.tracker` later (claim, sync and strict mode) inherit
   with no change to the merge.

## Non-goals

- **Other `work:` settings.** Tags, lifecycle bindings, documentation entries,
  retention, commit policy, `path` and `repository` stay per node. The
  requester scoped this to the tracker, and several of those are lists with
  no obvious key-by-key merge.
- **Inheriting from connections other than parents.** Children, siblings and
  taxonomy `extends` sources contribute nothing.
- **A shared block held by a node that has a board but tracks nothing
  itself.** A node with a work store is checked on its merged settings the
  same as today, so shared settings missing `candidate-query` are reported
  there. Put shared settings in a node without a board (such as a workspace
  root), or give the holding node a query of its own. See Risks.
- **Showing where each setting came from.** No command prints the merged
  settings with their source files. Only problems name them.
- **Any network call.** Nothing here contacts the tracker.
- **The two `tracker show` notes from the issue's side notes.** Those were
  fixed on the configure item.

## Design

### The merge

Blocks are read nearest first: the node itself, then each entry of
`ancestors()` in order. Starting from the farthest, each nearer block is laid
over the result:

- **A mapping over a mapping merges key by key**, recursively. This is what
  covers `credentials` and `transitions` today, and any mapping key added later.
- **Any other value replaces what is below it wholesale**: a string, a number,
  a list, or a mapping laid over a non-mapping and the reverse. Lists replace
  rather than concatenate, because no list-valued key exists yet and replacing
  is the rule a reader can predict.
- **A key set to null, or left blank, is treated as not set**, so the value
  from further up shows through. That matches how a blank `tracker:` already
  means "no block" (`tcw/store/base.py:922`).

The merged mapping then goes through the existing `parse_tracker_config`
unchanged. Required keys, unknown keys, types and failing closed all apply to
the merged result, exactly as they apply to a single block today.

### Opting out: `tracker: none`

The exact string `none` as the value of `work.tracker` means this node has no
tracker, whatever its ancestors set. `tracker_config()` returns `None` and
`tracker_problems()` returns nothing.

**It applies only to the node that writes it.** That node contributes nothing
to its descendants' merge, and they keep inheriting from the nodes above it.
This is the rule that fits the requester's shape. A repository root with its
own board and no tracker sits between a workspace root that holds the shared
settings and packages that track tickets. If `none` also cut off everything
below it, the packages would lose the workspace root's settings. A subtree
that tracks nothing writes `none` in each of its nodes that has a board.

Any other non-mapping value (`tracker: off`, `tracker: false`) is still the
existing "expected a mapping" problem.

### Where the code lives (abstraction test)

Could a store that isn't a filesystem do this? Yes. The merge is a pure
function over an ordered list of blocks, each labeled with its source. It sits
in `tcw/store/base.py` beside `parse_tracker_config`, and it reads no files.
Each store gathers its blocks from its own project graph through
`ProjectRegistry.ancestors()`, which is already storage-neutral. The abstract
`WorkStore.tracker_config()` and `tracker_problems()` keep their signatures and
their `None` / empty defaults. No new store operation is added. The filesystem
adapter gathers the ancestors' `work.tracker` values from the project registry
as a private detail.

The graph can have problems (a cycle, a malformed `connected-projects`). In
that case `tracker_config()` still never raises, and it falls back to the
node's own block. `tcw validate` already stops early and reports the graph
problems (`tcw/validate.py`, the `graph_problems` return in `validate`).

### Naming the file a problem came from

A problem about a value written in the node's own file keeps today's prefix
exactly (`tcw-config.yaml: work.tracker.…`), so existing messages and tests do
not change. A problem about a value that came from an ancestor names that
ancestor's project id and the location of its config file. Examples are an
unknown key, a wrong type, or `provider` not being supported. A missing
required key is blamed on the node being checked, since no file wrote it.

### Ancestors this checkout does not have

`ancestors()` stops at a declared parent the registry cannot reach, because
`parent()` returns `None` for a project it does not hold
(`tcw/store/project.py:180-185`). The merge uses whatever ancestors are
reachable. If the merged result then has problems, one more problem is added.
It names the unreachable declared parent and says settings it may hold were
not read. That way a "required" complaint on a partial checkout points at the
real cause. `unreachable_parent` (`tcw/store/fs.py:281`) already answers the
question.

### Validation across child nodes

`tcw validate` checks the current node and each descendant separately
(`tcw/cli.py:438-443`). A bad value in a parent is reported once for each node
that inherits it, each line naming the parent's file. That is accurate, since
every one of those nodes has no tracker until the value is fixed. No
de-duplication.

## Acceptance criteria

Fixtures are connected-project graphs built on disk in tests, the way
existing registry tests build them. "Root → repo → pkg" means pkg's parent is
repo and repo's parent is root.

1. Root sets a complete block, and repo and pkg set nothing. `tracker_config()`
   at pkg equals root's parsed config.
2. Root sets `provider`, `base-url`, `credentials` and `transitions`. Repo sets
   nothing. Pkg sets only `candidate-query`. Pkg's config has pkg's query and
   root's other values, and `tracker_problems()` at pkg is empty.
3. Root sets `credentials: {email-env: A, token-env: B}` and pkg sets
   `credentials: {token-env: C}`. Pkg's config has `email_env == "A"` and
   `token_env == "C"`.
4. Root has no work store and holds a complete block. A child with a work store
   and no block of its own inherits it (criterion 1 holds with root board-less).
5. Pkg sets `base-url` to one URL, and repo and root each set a different
   one. Pkg's config has pkg's URL, and repo's config has repo's URL.
6. Pkg sets `timeout-seconds: null` and root sets `timeout-seconds: 30`. Pkg's
   `timeout_seconds == 30`.
7. Repo sets `tracker: none`, root sets a complete block, and pkg sets only
   `candidate-query`. `tracker_config()` at repo is `None` and
   `tracker_problems()` at repo is empty. Pkg's config uses root's values.
8. A node with no ancestors and `tracker: none` has no config and no problems.
   `tracker: off` still reports the "expected a mapping" problem.
9. Root sets `base-url: 42`. `tracker_problems()` at pkg (which sets its own
   query) includes a problem naming root's project id and root's config file.
   Pkg's `tracker_config()` is `None`.
10. Root sets an unknown key `colour`. The unknown-key problem at pkg names
    root's project id and root's config file.
11. A problem about a value in pkg's own file starts with `tcw-config.yaml: `,
    exactly as today. All existing tests in `tests/test_tracker_config.py` and
    `tests/test_tracker_validate.py` pass unchanged.
12. Pkg's declared parent is not checked out, and pkg sets only
    `candidate-query`. `tracker_problems()` at pkg includes the usual
    "required" problems and one more naming the unreachable parent's id.
13. With no `work.tracker` anywhere in the graph, `tracker_config()` is `None`
    and `tracker_problems()` is empty at every node, and `tcw validate` output
    is unchanged.
14. `tcw work tracker list`, run at pkg from criterion 2 with
    `JiraClient._request` replaced by a fake (as `tests/test_tracker_cli.py`
    does), builds its client with root's `base-url` and sends pkg's query.
15. The merge function in `tcw/store/base.py` takes plain mappings and source
    labels. A test calls it with no node on disk, from an empty temporary
    directory, and gets the merged result of criteria 2, 3 and 6.
16. The full test suite passes.
17. `docs/guide/work.md`, `skills/tcw-work/references/commands.md` and
    `README.md` describe inheritance, `tracker: none` and the per-node rule.
    `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` have
    entries, and the release note states the behavior change in Risks 1.
18. The capability ledger matches Capability changes, and `tcw capabilities
    check` and `tcw validate` pass.

## Risks

1. **Nodes that have no tracker today can start having one.** A child with no
   block, under a parent with a complete block, inherits the parent's block
   including its `candidate-query`. Then `tcw work tracker list` at the child
   lists the parent's tickets instead of refusing. Everything involved is
   read-only and the tracker commands shipped in v2.1.0, so few projects can
   be affected. The release note must say so and name `tracker: none` as the
   way back.
2. **A board-holding parent cannot hold shared settings without tracking.**
   It is checked on its merged settings like any node, so a shared block with
   no `candidate-query` is reported there, and `none` would stop it being
   used. It is listed as a non-goal. The way around it is to keep the shared
   block in a node without a board, or give the holding node its own query. If
   it proves common, a later item can add a rule for it.
3. **A future key that must not inherit.** The merge inherits every key. If
   the claim, sync or strict-mode items add a key that is meaningful only
   per node, that item has to add an exception. The claim item is being
   planned at the same time as this one. Its new keys only need adding to the
   parser to inherit.
4. **Mixed versions.** A `tcw-config.yaml` containing `tracker: none`, read by
   v2.1.x, reports "expected a mapping". Acceptable, because a workspace runs
   one TCW version, but it goes in the changelog.
5. **Partial checkouts can differ silently.** When an unreachable ancestor
   holds only optional keys (today, `timeout-seconds`), the merged result is
   complete without it and no problem is raised, so the timeout differs from
   a full checkout. The effect is small.
6. **Cost.** Reading ancestors means opening the project registry each time
   tracker settings are read, which is once per `tcw work tracker` command and
   once per node in `tcw validate`. `tcw validate` already opens it, and
   `tcw work tracker` does not (`_store`, `tcw/work/cli.py:120-124`). The plan
   should reuse an open registry where one exists.

## Notes

- **Decisions this spec made that the requester was not asked about.** `none`
  affects only the node that writes it (see Design for why). Null means not
  set. Lists replace. A parent that isn't checked out is reported only when
  the merged result has problems. There is no de-duplication across child
  nodes.
- **Rejected: `none` hides everything above it from the whole subtree.** It is
  simpler to describe, but it breaks the three-level shape described under
  "Opting out".
- **Rejected: reading only the direct parent.** The requester chose every
  ancestor. That also matches taxonomy `extends`, which resolves through every
  ancestor since `2026-07-01-transitive-taxonomy-inheritance`.
- **Rejected: extending the `inspect-external-tracker-work` description
  instead of a new capability.** See Capability changes.
- **Sibling sweep, repo-wide.** Every `work:` setting is read node-only
  through `_work_config()`. All except `tracker` are out of scope by the
  requester's choice, not overlooked. No other code reads `work.tracker`.
