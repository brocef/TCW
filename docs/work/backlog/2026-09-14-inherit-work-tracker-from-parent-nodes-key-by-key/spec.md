# Spec — Inherit work.tracker from parent nodes, key by key

**Revised 2026-09-14 after an adversarial review.** The main change: inheritance
is now opt-in. A node gets tracker settings from its parents only if its own
file has a `work.tracker` block, so a node that writes nothing behaves exactly
as it does today, and `tracker: none` is dropped. See `## Notes` for the
review findings and how each was handled.

## Capability changes

One new capability, added `Missing` when implementation starts and flipped to
`Supported` by this item's completion:

- `work/inherit-tracker-settings-from-parent-nodes` — "Inherit tracker settings
  from parent nodes", carrying `Feature=external-work-tracker` and
  `Planning doc` pointing here.

`work/inspect-external-tracker-work` keeps its status. Its description gains
one sentence saying the settings it describes may come partly from parent
nodes.

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
   any problem returns no config at all (`tcw/store/base.py:907-921`,
   `:994-995`). That rule is right and stays. It just means every copy is
   another chance to break a node.
4. **Nothing to build on.** No setting under `work:` inherits between nodes
   today. A sweep of the 14 `_work_config()` readers in `tcw/` found none that
   consults another node, and no other code reads `work.tracker` directly
   (`tcw/store/fs.py:5287` and `:5294` are the only two). The project graph can
   already walk upward: `ProjectRegistry.ancestors()` (`tcw/store/base.py:251`)
   returns the direct parent first, then the rest. The filesystem registry
   implements it at `tcw/store/project.py:207-215`, and
   `FsProjectRegistry.config(project_id)` (`tcw/store/project.py:333-335`)
   returns any loaded node's whole config as a shallow copy.

## Goals

1. **Opt-in.** A node whose own `work.tracker` is a non-empty mapping gets
   those keys merged over the `work.tracker` keys of every ancestor. The
   nearest node that sets a key wins that key.
2. **No change for a node that writes nothing.** A node whose own
   `work.tracker` is absent, blank or `{}` has no tracker and no tracker
   problems, whatever its ancestors set. That is today's behavior.
3. Ancestors without a work store of their own still contribute their settings.
4. Nested mappings (`credentials`, `transitions`) merge key by key in the same
   way.
5. `tcw validate` and `tcw work tracker list|show` all use the merged settings.
   Each problem names the file the offending value came from.
6. A token is never sent to a site its node did not choose: `credentials` must
   come from the same node as `base-url` or a nearer one.
7. Keys added under `work.tracker` later (claim, sync and strict mode) inherit
   with no change to the merge.

## Non-goals

- **Other `work:` settings.** Tags, lifecycle bindings, documentation entries,
  retention, commit policy, `path` and `repository` stay per node. The
  requester scoped this to the tracker, and several of those are lists with
  no obvious key-by-key merge.
- **Inheriting from connections other than parents.** Children, siblings and
  taxonomy `extends` sources contribute nothing.
- **A shared block held by a node that has a board but tracks nothing
  itself.** Holding a block is opting in, so such a node is checked on its
  merged settings like any other, and shared settings missing
  `candidate-query` are reported there. Put shared settings in a node without
  a board (a workspace root, for example), or give the holding node a query of
  its own. See Risks.
- **Removing an inherited optional key.** A child cannot unset a key a parent
  set. Today the only optional key is `timeout-seconds`, whose value always
  has an effect. If the sync item adds optional transition mappings that a
  child's workflow lacks, that item decides how to unset one.
- **Showing where each setting came from.** No command prints the merged
  settings with their source files. Only problems name them.
- **Any network call.** Nothing here contacts the tracker.
- **The two `tracker show` notes from the issue's side notes.** Those were
  fixed on the configure item.

## Design

### Which blocks take part

The node's own `work.tracker` is read first.

- **Absent, null, or `{}`:** no tracker and no problems. Ancestors are not
  consulted.
- **Not a mapping** (`tracker: none`, `tracker: 5`): the existing "expected a
  mapping" problem, as today. Ancestors are not consulted.
- **A non-empty mapping:** it is merged with its ancestors' blocks.

Ancestors are `ancestors()` in order, direct parent first. An ancestor whose
`work.tracker` is absent, null or `{}` contributes nothing. An ancestor whose
`work.tracker` is present but not a mapping cannot be merged, so the merge
stops there. The result is that problem, attributed to that ancestor (see
"Naming the file a problem came from"). Every node that opts in beneath it
has no tracker until it is fixed, the same fail-closed rule the parser already
applies within one block.

### The merge

Starting from the farthest contributing block, each nearer block is laid over
the result:

- **A mapping over a mapping merges key by key**, recursively. This covers
  `credentials` and `transitions` today, and any mapping key added later.
- **Any other value replaces what is below it wholesale.** That covers a
  string, a number, a list, or a mapping laid over a non-mapping and the
  reverse. Lists replace rather than concatenate, because no list-valued key
  exists yet and replacing is the rule a reader can predict.
- **Null laid over a value from farther up is skipped**, so the farther value
  shows through. A null that nothing farther up replaces stays in the merged
  result, and the parser reports it exactly as it does today (for example
  `timeout-seconds: null` → "expected a positive number, got NoneType",
  `tests/test_tracker_config.py:114`). An empty string is a value, not null,
  and is reported as today.

The merge also records, for every key path in the result, which block
supplied it. For example, `credentials.token-env` came from pkg.

The merged mapping then goes through the existing `parse_tracker_config`
unchanged. Required keys, unknown keys, types and failing closed all apply to
the merged result, exactly as they apply to a single block today.

### Credentials stay with their site

After merging, compare the block that supplied `base-url` with the block that
supplied `credentials`. If `credentials` came from a block farther up than
`base-url`'s, the result is a problem and no config. Credentials that are
partly inherited count by the farthest block among their keys. The problem
reads:

```
tcw-config.yaml: work.tracker.credentials: inherited from a parent node, but base-url is set nearer, in tcw-config.yaml; set credentials in the same file as base-url
```

The first `tcw-config.yaml` is the prefix for the node being checked. The one
at the end is the `base-url` block's label. Without this rule, a child that
changes `base-url` and forgets `credentials` would send its parent's token to
the new site. Today `JiraClient` builds the `Authorization` header from
whatever variables the config names and sends it to whatever `base-url` it
names (`tcw/tracker/jira.py:131-145`). Setting only `credentials` nearer than
`base-url`, meaning a different account on the same site, is allowed.

### Where the code lives (abstraction test)

Could a store that isn't a filesystem do this? Yes. The merge is a pure
function over an ordered list of `(source label, raw block)` pairs. It returns
the merged mapping and the key-path → source record. It sits in
`tcw/store/base.py` beside `parse_tracker_config` and reads no files. The
credential check and problem attribution are pure too. Each store gathers its
blocks from its own project graph through `ProjectRegistry.ancestors()`, which
is already storage-neutral. The abstract `WorkStore.tracker_config()` and
`tracker_problems()` keep their signatures and their `None` / empty defaults.
No new store operation is added. The filesystem adapter gathers the ancestors'
blocks through `FsProjectRegistry.config()` as a private detail. It copies
before merging, because `config()` returns a shallow copy and nested mappings
would otherwise be shared.

Both commands that read tracker settings already refuse on graph problems
before a store is opened. `find_node` calls
`FsProjectRegistry.open(nr).require_valid()` (`tcw/store/fs.py:205`), and
`validate` returns its graph problems first. So registry problems reach
`tracker_config()` only from direct Python callers. For those it still never
raises, and falls back to the node's own block alone.

### Naming the file a problem came from

The node's own file keeps today's prefix exactly, so existing messages and
tests do not change. An ancestor's file is named by the absolute path of its
config, as the registry located it, followed by its project id:

```
tcw-config.yaml: work.tracker.candidate-query: required
/work/ex/tcw-config.yaml (project 'ex-root'): work.tracker.base-url: expected a non-empty string, got int
```

A problem goes to the block that supplied the value it is about: an unknown
key, a wrong type, an unsupported `provider`, or an ancestor block that is not
a mapping. A problem about a key nobody set, such as a missing required key,
goes to the node being checked. Problems are sorted by the parser's message
before the prefix is added, so their order does not depend on where a value
came from.

### Ancestors this checkout does not have

`ancestors()` stops at the first declared parent the registry cannot reach,
because `parent()` returns `None` for a project it does not hold
(`tcw/store/project.py:180-185`). That parent may be the direct parent or one
farther up. The store takes the last ancestor it reached (or the node itself,
if none) and asks `declared_parent_id()` for that project's parent. If one is
declared and `get()` cannot find it, that is the unreachable project. The
existing `unreachable_parent` helper (`tcw/store/fs.py:281`) is not used: it
checks only the current node's direct parent, and it raises on graph problems.

If the merged result has problems, one more problem is added:

```
tcw-config.yaml: work.tracker: declared parent 'ex-root' is not available in this checkout, so any tracker settings it holds were not read (run tcw provision)
```

With no problems, nothing is added. Whether that is enough for a key that
must not silently disappear on a partial checkout, such as a future `strict`
flag, is the strict-mode item's decision.

### Validation across child nodes

`tcw validate` checks the current node and each descendant separately
(`tcw/cli.py:438-443`). A bad value in a parent is reported once for each node
that opts in beneath it, each line naming the parent's file. That is accurate,
since every one of those nodes has no tracker until the value is fixed. No
de-duplication.

## Acceptance criteria

Fixtures are connected-project graphs built on disk in tests, the way
`tests/test_store_nodes.py:15-31` builds them. "Root → repo → pkg" means pkg's
parent is repo and repo's parent is root. "Complete block" means one that
parses with no problems by itself. Unless a criterion says otherwise, root has
no work store, and repo and pkg each have one.

1. Root has a complete block. Pkg's block is only `candidate-query`. Repo
   writes nothing. `tracker_config()` at pkg equals root's parsed config except
   `candidate_query`, which is pkg's. `tracker_problems()` at pkg is empty.
2. In criterion 1's graph, `tracker_config()` at repo is `None` and
   `tracker_problems()` at repo is empty.
3. Root has `provider`, `base-url`, `credentials` and `transitions`, but no
   `candidate-query`. Repo writes nothing. Pkg's block is only
   `candidate-query`. Pkg's config combines them with no problems. Repo, which
   has a work store and writes nothing, has no config and no problems, and
   `tcw validate` run at root prints `validate OK`.
4. Root has `credentials: {email-env: A, token-env: B}` along with the rest of
   a complete block. Pkg's block is `candidate-query` and
   `credentials: {token-env: C}`. Pkg's config has `email_env == "A"` and
   `token_env == "C"`.
5. Root and repo each have a complete block with different `base-url`s. Pkg's
   block is `base-url` and `credentials` of its own plus `candidate-query`.
   Pkg's config has pkg's URL, repo's has repo's, and root's has root's (root
   is given a work store for this one).
6. Root's block is complete and sets `timeout-seconds: 30`. Pkg's block is
   `candidate-query` and `timeout-seconds: null`. Pkg's `timeout_seconds == 30`.
7. A node with no ancestors whose block is complete except
   `timeout-seconds: null` still reports the `timeout-seconds` problem.
8. `tracker: none` in pkg's own file, under a root with a complete block,
   reports `work.tracker: expected a mapping, got str`.
9. Root's block is complete but has `base-url: 42`. Pkg's block is only
   `candidate-query`. `tracker_config()` at pkg is `None`, and
   `tracker_problems()` at pkg includes exactly
   `<root config absolute path> (project 'root'): work.tracker.base-url: expected a non-empty string, got int`.
10. Root's block is complete plus an unknown key `colour`. The problem at pkg
    is `<root config absolute path> (project 'root'): work.tracker.colour: unknown key`.
11. Root's `work.tracker` is the string `off`, and pkg's block is complete.
    `tracker_config()` at pkg is `None`, and the problem at pkg is
    `<root config absolute path> (project 'root'): work.tracker: expected a mapping, got str`.
12. A problem about a value in pkg's own file starts with `tcw-config.yaml: `.
    All existing tests in `tests/test_tracker_config.py`,
    `tests/test_tracker_validate.py`, `tests/test_tracker_absent.py` and
    `tests/test_tracker_cli.py` pass unchanged.
13. Root → repo → pkg where repo is present and root's locator does not exist.
    Pkg's block is only `candidate-query`, and repo writes nothing. Pkg's
    problems include `tcw-config.yaml: work.tracker.base-url: required` and
    `tcw-config.yaml: work.tracker: declared parent 'root' is not available in this checkout, so any tracker settings it holds were not read (run tcw provision)`.
14. The same as 13 but with repo missing instead. The notice names `repo`.
15. Root's block is complete. Pkg's block is `candidate-query` and a different
    `base-url`, with no `credentials`. `tracker_config()` at pkg is `None`,
    and its problems include the credentials message in Design, "Credentials
    stay with their site".
16. With no `work.tracker` anywhere in the graph, `tracker_config()` is `None`
    and `tracker_problems()` is empty at every node.
17. `tcw work tracker list`, run at pkg from criterion 1 with
    `JiraClient._request` replaced by a fake (as `tests/test_tracker_cli.py`
    does), exits 0. It builds its client with root's `base-url` and sends
    pkg's query.
18. The merge function in `tcw/store/base.py` is called in a test with plain
    mappings and labels, with no node on disk, from an empty temporary
    directory. It returns criterion 4's merged mapping, and a source record
    in which `credentials.token-env` maps to pkg's label and
    `credentials.email-env` to root's.
19. The full test suite passes, under both `python -m pytest` and bare
    `pytest`.
20. `docs/guide/work.md`, `skills/tcw-work/references/commands.md` and
    `README.md` describe opt-in inheritance, the credentials rule, and the
    board-holding-parent limit. `docs/changelogs/upcoming.md` and
    `docs/release-notes/upcoming.md` have entries.
21. The capability ledger matches Capability changes, and `tcw capabilities
    check` and `tcw validate` pass.

## Risks

1. **A board-holding parent cannot hold shared settings without tracking.**
   Holding a block opts it in, so a shared block with no `candidate-query` is
   reported there. This is listed as a non-goal. The way around it is to keep
   the shared block in a node without a board, or give the holding node its
   own query. If it proves common, a later item can add a rule for it.
2. **A future key that must not inherit.** The merge inherits every key. If
   the claim, sync or strict-mode items add a key that means something only
   per node, that item adds a set of keys read from the node's own block
   alone, and the merge skips them in ancestors. No such key exists today, so
   the set is not added now. The claim item is being planned at the same time
   as this one. Its spec should say that its keys inherit, and if both ship in
   one release, the combined change should be reviewed together.
3. **Mixed versions.** A child block holding only `candidate-query`, read by
   v2.1.x, reports the missing keys as required. Acceptable, because a
   workspace runs one TCW version. It goes in the changelog.
4. **Partial checkouts can differ silently.** When an unreachable ancestor
   holds only optional keys (today only `timeout-seconds`), the merged result
   is complete without it and no notice is shown. Today the only effect is a
   different timeout. See the strict-mode note under "Ancestors this checkout
   does not have".
5. **Null now inherits instead of failing, but only when an ancestor supplies
   the key.** A node's own `timeout-seconds: null` under a parent that sets
   `timeout-seconds` used to be a problem and now takes the parent's value.
   Without an ancestor value it is still reported (criterion 7). This goes in
   the changelog.

## Notes

- **Superseded request choice.** The requester first chose inheritance for
  every node, with `tracker: none` to opt out. After the review showed what
  that causes, they chose opt-in instead, on 2026-09-14. A node that writes no
  block no longer silently gains a tracker, whether it exists today or is
  added later. A node that tracks nothing no longer fails `tcw validate` (and
  so `complete`, which runs it as a `pre` hook in this repository,
  `tcw-config.yaml:65`) because a parent holds shared settings. And `none` is
  no longer needed.
- **Review findings, 2026-09-14 (adversarial spec reviewer, one round, not a
  multi review).**
  - *Accepted:* only a missing direct parent was detected
    (`unreachable_parent` checks one level); fixed in the unreachable-ancestor
    design, criterion 14.
  - *Accepted:* a board-holding descendant turned red under a board-less
    shared block; removed by opt-in, criterion 3.
  - *Accepted:* credentials could follow a changed `base-url`; the credentials
    rule, criterion 15.
  - *Accepted:* the cost risk was wrong, because both commands already open
    the registry; dropped.
  - *Accepted:* criteria two readers would check differently. Exact messages
    are given, and the source record is part of the merge's result.
  - *Narrowed:* null handling. A lone null is still reported, so existing
    behavior holds unless a parent supplies the key. Unsetting an inherited
    optional key is left to the sync item.
  - *Narrowed:* non-inheriting keys. The mechanism is named in Risks 2 but not
    built, since no such key exists.
  - *Narrowed:* whether the unreachable notice should fire without problems.
    Left to the strict-mode item.
  - *Rejected as moot:* the risk of a new node under `none`, and the
    "no tracker is configured" message at a `none` node. Both disappear with
    opt-in.
- **Rejected: reading only the direct parent.** The requester chose every
  ancestor. That also matches taxonomy `extends`, which resolves through every
  ancestor since `2026-07-01-transitive-taxonomy-inheritance`.
- **Rejected: extending the `inspect-external-tracker-work` description
  instead of a new capability.** See Capability changes.
- **Sibling sweep, repo-wide.** Every `work:` setting is read node-only
  through `_work_config()`. All except `tracker` are out of scope by the
  requester's choice, not overlooked. No other code reads `work.tracker`.
