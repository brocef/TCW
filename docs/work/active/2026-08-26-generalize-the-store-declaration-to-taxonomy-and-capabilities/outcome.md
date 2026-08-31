# Outcome — Generalize the store declaration to taxonomy and capabilities

All ten planned tasks landed, each as its own commit, with the suite green at
every boundary. A checkout that cloned only the code repository can now obtain a
declared taxonomy or capabilities tree and read from it.

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1 | `0b4c7c0` | `configurable-work-store-location` → `configurable-component-store-location` |
| 2 | `594a0bc` | a per-component store-layout predicate; the provisioner stops naming the work store's |
| 3 | `9204045` | `resolve_store` — the ladder extracted from `FsWorkStore.open`, pure refactor |
| 4 | `bac809f` | `FsTreeStore.open` on the ladder; the `node_root` / `store_git_root` split |
| 5 | `d234988` | `find_node` asks the resolved store; `_run_check` guards all three components |
| 6 | `c6441e5` | `PROVISION_COMPONENTS` widened; the precedence check made per-component |
| 7 | `54adaaa` | `tcw init --taxonomy-path` / `--capabilities-path` |
| 8 | `a0178d6` | four new capabilities; five `changed:` bodies actually updated |
| 9 | `87a39ab` | README, changelog, release notes, three skill documents |
| 10 | `a99592f` | the verification finding below, fixed before the suite run |

## Acceptance criteria

Every criterion was walked from a bare shell against a real two-repository
fixture, not read off test names.

| # | Criterion | Evidence |
| - | --------- | -------- |
| 1 | a declared unprovisioned tree is never "absent component" | 8 commands parametrized, plus the no-local-folder case below |
| 2 | provisioned is indistinguishable from local | `tcw taxonomy list/show/path` against a provisioned tree, by hand and in tests |
| 3 | idempotent, contacts nothing | `GIT_TRACE=1` shows no clone/fetch; "already available", exit 0 |
| 4 | a local store always wins, per component | parametrized over all three, with the adapter's Git call intercepted |
| 5 | components provisioned independently | two declarations, one good and one bad; the good one lands, the bad one is reported |
| 6 | nothing configured behaves exactly as today | rule 4 tests incl. a node with no `docs/taxonomy` at all; no test outside this module rewritten |
| 7 | failure leaves nothing behind, per component | a tree `repository.path` naming nothing is refused with no checkout published |
| 8 | only `tcw provision` reaches the network | `tests/test_subprocess_stdin.py`, unchanged |
| 9 | a malformed declaration names the line, per component | 16 cases: both config shapes × the command surface — see below |
| 10 | the Feature rename leaves nothing dangling | `tcw validate`, `tcw capabilities check`, and a repository-wide grep |
| 11 | reproducible from a bare shell | every row above was a plain shell; no hook, no slash command |

### Verified by hand

A bare orchestrator remote holding a taxonomy tree with one term, and a separate
code repository declaring it — **with no `docs/taxonomy/` of its own**, which is
the requester's actual shape. `tcw taxonomy list` reported the declared remote
and `tcw provision`; `tcw provision --dry-run` printed the plan and fetched
nothing; `tcw provision` obtained the tree; `tcw taxonomy list` and
`tcw taxonomy show some-term` then printed the term; `tcw taxonomy path` printed
the provisioned location; a second `tcw provision` reported *already available*
with no Git subprocess.

## Suite

The full run passed **2123 tests** with no failures and no skips, outside the
restricted sandbox — the server suites bind loopback sockets, and the sandboxed
run's `PermissionError` cluster is an artefact of that rather than a result.
`tests/test_store_provisioning.py` holds 138 cases, up from the 74 child A left.

## What the plan and spec got wrong

**Criterion 9 was written as a property and tested as an enumeration.** Every
test written for it set `<component>.path`, and all of them passed. The bare-shell
walk found that without a path the same config answered
`no tcw taxonomy node here — run \`tcw init\``.

The cause is specific and was not anticipated anywhere in the spec: a malformed
declaration parses to `(None, problems)`, so the ladder sees *no declaration*,
takes rule 4, and a tree store's rule 4 validates nothing and therefore cannot
raise — so the problems were dropped on a code path that never fails. The work
store never had this hole because its rule 4 always validates.

`a99592f` makes `declaration_problems` count toward `must_exist`: a candidate
allowed to mask a configuration error has to be a real store, not a directory
that might not exist. The inverse is tested too — a tree that really is present
still masks an unused malformed declaration, which is why the fix is not "always
raise".

This is the same defect shape the spec's own Acceptance-criteria preamble was
written to prevent, one item after child A found it three times. Stating a
criterion as a property is evidently not sufficient; the enumeration reappears in
the *test fixtures* even when the criterion text is general. What would have
caught it here is asking, for each criterion, which configuration shapes exist —
`path` alone, `repository` alone, both, neither — and covering the grid.

**Task 7's first attempt broke criterion 6.** Generalizing `init`'s `work_path`
parameter into a `paths` mapping made seven `tests/test_external_work_store.py`
tests fail with `TypeError: init() got an unexpected keyword argument
'work_path'`. Criterion 6 forbids rewriting tests outside this module to
accommodate the work, so the signature was changed back: `work_path` keeps its
name and fourth position, and `paths` joins it. The criterion did its job — this
would otherwise have been "update the tests" without a second thought.

**The plan underestimated task 4.** It described putting `FsTreeStore.open` on
the ladder as a single move, but `FsTreeStore.node_root` turned out to carry two
different meanings — the node whose config this is and whose `extends` federation
resolves, *and* the repository a write commits in. They are the same directory
only while the store sits inside its node. Conflating them broke federation for a
provisioned tree; the store now carries `node_root` and `store_git_root`
separately, exactly as `FsWorkStore` has since `work.path` existed. The plan
should have found this, because the precedent was already in the file.

**One message improvement fell out of task 2.** A provisioning refusal for a
declared path naming nothing in the repository said `missing: inbox, backlog, …`,
which reads as an incomplete store when in fact the whole directory is absent. It
now says so, and the enumeration is kept for the present-but-incomplete case it
actually describes. The pre-existing test asserting `missing:` for the absent-path
case was corrected rather than preserved — it was asserting an enumeration where
nothing is missing.

## Process

The item was started before its spec was written. `spec` and `plan` run in
`backlog`, and `rework` is the machine's only reverse edge, so this could not be
undone; the artifacts were written in order regardless. Worth noting because the
`request` stage ran first and legitimately, which is what made `start` look
reasonable.

## Decisions worth carrying forward

- **A tree store cannot identify itself, and the docs say so.** No marker file was
  invented, because requiring one would break rule 4 for every project that has a
  taxonomy tree today. The weaker guarantee is written into the two
  `declare-…-home-repository` capability bodies and the README, where a user meets
  it, not only in this item's folder.
- **Widen a value's legal set in the same change as the adapter behind it.** Child
  A narrowed `--component` to `work` after review found it accepting values it
  could not serve; this item reversed that narrowing and added the adapters in one
  task, never in two.
- **`node_root` is not one concept.** Any future component store needs the
  node/store-repository split from the start.
