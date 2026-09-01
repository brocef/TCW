# Spec: Re-anchor a relative work.path at the node's counterpart inside the main worktree

## Capability changes

No new capability. Two existing entries are **amended** to say what they will
then be true of; no records are written at this stage.

- `cli/run-from-a-git-worktree` (cap-b47597, Supported) — amend. It already
  states the rule this item restores ("re-anchors … but only when the target
  leaves the worktree"; "the node I operate on is the **worktree**: its
  `docs/work/` … are the checked-out ones"), but states it only of
  `connected-projects` locators. After this change the same rule holds for
  `work.path`, so the entry should say so rather than leaving the reader to
  assume a promise the store resolver did not keep.
- `work/configure-the-work-store-location` (cap-46e036, Supported) — amend. It
  says `work.path` may be "a path relative to the owning project's primary
  checkout" without qualification. That is true only of a path that leaves the
  checkout; one that stays inside belongs to the worktree, like the default.

Neither status changes: both remain Supported. This item makes them accurate,
which is the point — today `cli/run-from-a-git-worktree` documents behaviour
the code does not have.

## Problem

`FsWorkStore._local_root` (`tcw/store/fs.py:2778-2795`) is the only place a
configured relative `work.path` is resolved. Inside a linked git worktree it
re-anchors that path with `base = anchors[1]` (line 2794) — the **main worktree
root** — and `worktree_anchors` (`tcw/store/project.py:56`) returns
`(current worktree top, main worktree root)`, so the first element, the node's
own position, is discarded.

Two defects follow from that one line.

**1. The node's sub-path is dropped.** For a node nested at `apps/server`,
`base` becomes the repository root rather than the node's counterpart, so the
configured path is applied from the wrong directory. Reproduced: a node at
`apps/server` with `work.path: ../../../external/work` resolves to
`external/work` from the primary checkout and to a directory three levels above
the repository from the worktree — `tcw work` then reports `no tcw work node
here — run tcw init in the project folder`. This is the reported bug.

**2. Re-anchoring is unconditional.** Every relative path is re-anchored, not
only one that leaves the checkout. The sibling resolver does not do this.
`FsProjectRegistry._target_path` (`tcw/store/project.py:313-347`) re-anchors a
locator only when it escapes, and says why at lines 322-328: "A target that
stays inside the worktree is a sibling node on the same branch and belongs to
the worktree." Its counterpart expression at line 334 —
`counterpart = main / source_dir.relative_to(top)` — is exactly what
`_local_root` is missing, and `FsProjectRegistry.__init__` (lines 121-125) and
`tcw work complete` (`tcw/work/cli.py:1197-1199`) both compute it the same way.
`_local_root` is the sole outlier of the three consumers of `worktree_anchors`.

Defect 2 is why an explicit `work.path: docs/work` sends a worktree user to the
primary checkout's store while the *identical* default (`configured is None`,
line 2789) gives the worktree its own. It breaks a promise
`cli/run-from-a-git-worktree` already makes in the ledger.

### Sweep

Repo-wide, for defects sibling to the reported one:

- Three call sites consume `worktree_anchors`: `tcw/store/project.py:118-125`,
  `tcw/work/cli.py:1197`, and `tcw/store/fs.py:2792`. The first two compute the
  node counterpart correctly. Only the third does not.
- No other component resolves a configured relative path. `work` is the only
  component with a `path` key; `FsTaxonomyStore` and `FsCapabilitiesStore`
  inherit `FsTreeStore.open`, which is `node_root / "docs" / COMPONENT` with no
  configuration and no re-anchoring.
- `tcw init` resolves `work_path` against the node root without consulting
  worktree anchors (`tcw/store/fs.py:700`). That is correct — `init` acts where
  you stand — and is left alone.
- The report states there is an "identical tree-store copy" of `_local_root` at
  roughly line 3021. **Corrected after rebasing onto main mid-implementation:
  the reporter was right and this spec was wrong.** The sweep above was run
  against v1.1.0, where `_local_root` was defined once and the tree stores had
  no configured path. The reporter filed against 1.2.0, which had already
  generalized store resolution into a shared `resolve_store` ladder — so
  `FsTreeStore._local_root` (`tcw/store/fs.py:1112`) exists, serves taxonomy and
  capabilities, and carried a character-identical copy of both defects. Both
  hooks are in scope. See `outcome.md`.

## Goals

1. A nested node resolves a relative, checkout-escaping `work.path` to the same
   store from a linked worktree as from its primary checkout.
2. A relative `work.path` that stays inside the checkout resolves to the
   **worktree's own** copy, exactly as the default does for the same node.
3. `_local_root` follows the rule `_target_path` already implements and
   `cli/run-from-a-git-worktree` already documents.

## Non-goals

- Changing behaviour outside a linked worktree, or for a node that is not in a
  git repository. `worktree_anchors` returns `None` in both cases and the
  re-anchoring branch does not run.
- Changing behaviour for an **absolute** `work.path`, or for the **default**
  (no `work.path`). Neither reaches the re-anchoring branch.
- Changing `connected-projects` locator resolution. `_target_path` is correct;
  this item makes the work store agree with it, not the reverse.
- Changing `tcw init`, `tcw provision`, or the store-declaration ladder.
- Deduplicating the counterpart expression across all three call sites. Two of
  them are correct and untouched; a refactor of working code is not this item's
  risk to take. See Notes.

## Design

In `FsWorkStore._local_root`, replace the unconditional `base = anchors[1]`
with the escape-gated counterpart the sibling resolver uses:

```python
value = Path(configured).expanduser()
if value.is_absolute():
    return value
base = node_root
anchors = worktree_anchors(node_root)
if anchors is not None:
    top, main = anchors
    resolved = (node_root / value).resolve()
    # Mirrors FsProjectRegistry._target_path rule 1: a relative path that stays
    # inside the worktree belongs to the worktree, like the default store does;
    # only one that leaves it was authored against the primary checkout, and it
    # re-anchors at this node's counterpart there — never at the repo root,
    # which would drop a nested node's own sub-path.
    if node_root.is_relative_to(top) and not resolved.is_relative_to(top):
        base = main / node_root.relative_to(top)
return base / value
```

Notes on the shape:

- The absolute case returns early rather than being tested twice, as today.
- `node_root` is already resolved by the caller (`tcw/store/fs.py:2735`), and
  `worktree_anchors` resolves both anchors, so `relative_to` is safe. The
  `node_root.is_relative_to(top)` guard is belt-and-braces against a future
  caller that does not resolve.
- Escape is decided on the **resolved** target, so `..` segments count.
  `_target_path` tests `resolved.parent` because its target is a config file;
  here the target is the store root itself.
- The docstring must be rewritten: it currently asserts the old behaviour
  ("resolves against the main worktree root") as deliberate.

## Acceptance criteria

Each is checkable by running the named command against a fixture with a repo, a
node at `apps/server`, and a linked worktree.

1. Node at `apps/server`, `work.path: ../../../external/work`: `tcw work path`
   prints the same absolute path from the primary checkout and from the
   worktree. **Fails today** (worktree resolves three levels above the repo).
2. Node at `apps/server`, `work.path: docs/work`: from the worktree,
   `tcw work path` prints `<worktree>/apps/server/docs/work` — the same path the
   default (no `work.path`) prints for that node. **Fails today** (prints
   `<main>/docs/work`, which is not the node's store at all).
3. Node at the repository root, `work.path: docs/work`: from the worktree,
   `tcw work path` prints `<worktree>/docs/work`, identical to the default.
   **Fails today** (prints `<main>/docs/work`).
4. Node at the repository root, `work.path: ../external/work`: unchanged from
   today — the same path from both checkouts.
5. An absolute `work.path` and a default (absent) `work.path` are unchanged
   from today in every position, inside a worktree and outside one.
6. `monorepo_worktree` in `tests/test_environment_hardness.py` still passes —
   the layout a naive "always re-anchor" fix breaks.
7. The full suite passes: `pytest`.

Criteria 1-5 were run against a prototype of the design before this spec was
committed; the results are the matrix in Notes.

## Risks

- **A store that exists only on the worktree's branch.** Under criterion 2 the
  path now points inside the worktree, so this gets *better*, not worse: the
  branch that added the node carries its store. The escaping case still needs
  the main checkout's counterpart to exist, which is inherent to the feature.
- **Someone depending on today's behaviour** — a nested node with an
  inside-staying relative `work.path` who wants the primary checkout's store
  from a worktree. They lose that. It is not a promise TCW made: the ledger says
  the opposite, and the default already behaves the new way. Low: the shape is
  unusable today for nested nodes, which is the report.
- **`is_relative_to` on Python < 3.9.** Not a risk — already used at
  `tcw/store/project.py:331-332` and the project requires a newer Python.
- **The escape test resolves a path that may not exist.** `Path.resolve()` is
  non-strict and normalizes `..` lexically for missing paths, which is what
  `_target_path` already relies on.

## Notes

Prototype matrix, run against a real repo + linked worktree fixture. "primary"
is the resolution from the main checkout; the last two columns are from inside
the worktree.

| case | primary | worktree today | worktree fixed |
| --- | --- | --- | --- |
| nested, escaping | `external/work` | **wrong** (outside the tree) | `external/work` |
| nested, inside | `repo/apps/server/docs/work` | **wrong** (`repo/docs/work`) | `wt/apps/server/docs/work` |
| nested, default | `repo/apps/server/docs/work` | `wt/apps/server/docs/work` | unchanged |
| root, inside | `repo/docs/work` | `repo/docs/work` | `wt/docs/work` |
| root, default | `repo/docs/work` | `wt/docs/work` | unchanged |
| root, escaping | `external/work` | `external/work` | unchanged |
| nested, absolute | `external/work` | `external/work` | unchanged |

"Matches the primary checkout" is the right yardstick only for an escaping
path. For an inside-staying one the yardstick is "matches what the default does
for this node", which is what rows 2 and 4 achieve.

**On the abstraction litmus test.** Worktrees are named in
`docs/lifecycle/abstraction.md` as a filesystem-adapter local detail with no
abstract analog, and this change stays entirely inside the adapter: a private
static method on `FsWorkStore`, reading a private helper in the adapter's own
`project` module. No store-interface operation is added or changed, and a
non-filesystem store simply has no counterpart question to answer. The litmus
test is passed by staying put.

**On harness compatibility.** The behaviour lives in the `tcw` CLI, which
behaves identically under Claude and Codex. No skill, hook, or command
surface changes.

**On the counterpart expression appearing three times.** After this change,
`main / <node>.relative_to(top)` is written at `tcw/store/project.py:123`,
`tcw/store/project.py:334`, `tcw/work/cli.py:1199`, and `tcw/store/fs.py`.
Extracting it is tempting and deliberately not done here: the three existing
sites are correct, and `fs.py` importing one more name from `project.py` is a
smaller change than moving code two other features depend on. Worth a
follow-up item if a fifth site appears.
