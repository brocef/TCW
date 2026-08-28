# Spec — Declare and provision the work store's home repository

Child A of
[the store-home-repository epic](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it).
The epic's spec owns the initiative-level criteria; this one owns the work
store's half and settles the names and rules the other two children consume.

## Capability changes

**New** — declared and seeded `Missing` at this item's `plan` stage, recorded in
its `capabilities.yaml`:

- `work/declare-the-work-stores-home-repository`
- `cli/provision-declared-stores`

**Changed**

- `work/configure-the-work-store-location` — the body currently promises "an
  absolute path or a path relative to the owning project's primary checkout" as
  the only way to name the store. It gains the repository declaration and the
  precedence rule.
- `cli/locate-tcw-storage-folders` — `tcw work path` must answer for a declared
  store that is not here yet.
- `cli/validate-a-node` — `tcw validate` reports the new condition distinctly.

**Taxonomy** — registered *before* the capabilities that name them, because
`tcw capabilities set` refuses a `Feature=` that does not resolve:

- Vocabulary `home-repository`, child of the existing `store` term.
- Feature `provisioned-component-stores`, linked from both new capabilities.
  The existing `configurable-work-store-location` Feature stays as it is; whether
  it is renamed or absorbed is child B's call, not this item's.

## Problem

`FsWorkStore.open` accepts one way to name a store that is not `docs/work`: a
`work.path` string, absolute or resolved against the node (`tcw/store/fs.py:2436-2447`).
When that path does not exist the store cannot open (`tcw/store/fs.py:2450-2451`).

That is correct as far as it goes, and it is fatal in an environment that clones
only the code repository. Nothing in the config records where the store *comes
from*, so nothing can fix it.

The reason then gets lost. `find_node` catches every `ValueError` from
`FsWorkStore.open` and returns `None` (`tcw/store/fs.py:157-160`), and
`_has_work_store` does the same (`tcw/store/fs.py:198-202`). `tcw work`'s six
node-resolution sites all render that `None` as one sentence
(`tcw/work/cli.py:73`, `:89`, `:144`, `:162`, `:177`, `:192`). Reproduced on a
node whose `work.path` names an absent folder:

```
$ tcw work list
tcw work: no tcw work node here — run `tcw init` in the project folder.
```

The advice is wrong in the most expensive way available: `tcw init` would
scaffold a second, empty store beside the real one. Only `tcw validate` still
reports the truth, via a path (`work.path is not a directory: …`) that the
environment cannot act on.

## Goals

1. `tcw-config.yaml` can record the repository a work store lives in, portably.
2. An explicit command materializes it, and is idempotent.
3. A checkout that already has the store keeps using it, untouched.
4. Every surface that currently swallows the reason reports *declared but not
   provisioned* and names the command that fixes it.
5. A node with no declaration performs no network I/O, ever.
6. The mechanism is component-generic at the seam, so child B extends it rather
   than rewriting it.

## Non-goals

- Taxonomy and capabilities stores (child B). `FsTreeStore.open`
  (`tcw/store/fs.py:1023-1025`) is not touched here.
- Writing to a remote (child C). This item fetches; it never pushes.
- Credential management, and any interactive prompt. Git is invoked with stdin
  closed, per the package-wide invariant in `tcw/store/fs.py::_git`.
- Provisioning a whole connected project. A registered node that is absent stays
  absent.
- Migrating an existing store into a repository. Declaring is not moving.

## Design

### 1. The declaration

A `repository` mapping beside the existing `work.path`:

```yaml
id: my-project
work:
    path: ../orchestrator/docs/work/my-project   # optional, unchanged meaning
    repository:
        url: https://github.com/me/orchestrator.git   # required
        ref: main                                      # optional (default: remote HEAD)
        path: docs/work/my-project                     # optional (default: repo root)
        checkout: ~/src/orchestrator                   # optional (default: cache)
```

- `url` — any string Git accepts as a remote. Required; a `repository` without
  one is a config error.
- `ref` — branch, tag, or commit. Absent means the remote's default branch.
- `path` — the store's location *within* the repository. Relative, no `..`, no
  absolute; a traversal is a config error, matching the containment rule the
  stores already enforce.
- `checkout` — where the working copy lives on this machine. `~` expands;
  relative resolves against the node root. Absent means the cache (§3).

`tcw validate` checks the shape. An unknown key under `repository` is a problem,
not silently ignored — the existing `connected-projects` reader sets that
precedent (`tcw/store/project.py`, `unknown connected-projects keys`).

### 2. Resolution precedence

`FsWorkStore.open` gains one rule, ahead of everything it does today:

1. If `work.path` is set **and resolves to a usable store**, use it. Unchanged.
2. Otherwise, if `work.repository` is declared, the store is
   `<checkout-or-cache>/<repository.path>`. If that resolves to a usable store,
   use it.
3. Otherwise, if `work.repository` is declared, raise `StoreNotProvisioned`.
4. Otherwise, today's behavior exactly — including today's error messages for a
   `work.path` that is broken, not a directory, missing status folders, or
   outside a repository.

Rule 1 before rule 2 is what keeps the requester's laptop working: a machine that
already has the orchestrator folder never consults the declaration, and nothing
about that checkout changes.

Rule 4 is the compatibility guarantee. With no `repository` declared, not one
byte of behavior moves.

### 3. Where a provisioned store lands

`checkout` when declared. Otherwise
`${XDG_CACHE_HOME:-~/.cache}/tcw/stores/<key>`, where `<key>` is
`<host>-<owner>-<repo>-<12 hex of sha256(normalized-url + "\n" + ref)>`: readable
enough to recognize, unique enough that two projects sharing one repository at
one ref share one working copy, and two refs do not collide.

Not the node root. A store nested there is caught by the resolved-work ignore
rules (`tcw/store/fs.py:631-641`), which already refuse a store the repository's
own ignore rules would hide.

### 4. The command

`tcw provision [--component <c>]... [--refresh] [--dry-run]` — a top-level verb
beside `init` and `validate` (`tcw/cli.py:139`, `:146`), because it is
node-scoped and spans components. This item implements `work`; the argument
exists from the start so child B adds a value, not a flag.

1. Read each component's declaration. Nothing declared → say so, exit 0, touch
   no network.
2. Store already resolves and no `--refresh` → report *already available* with
   its path. Exit 0. This is what makes a second run a no-op.
3. Otherwise print the remote about to be contacted, **then** contact it: clone
   into a temporary directory beside the target and rename into place on success,
   or fetch and check out the ref if the checkout already exists.
4. Verify the store layout at `repository.path` — the same `inbox` + status
   folders check `open` already makes (`tcw/store/fs.py:2453-2455`) — and report
   the resolved path.

`--dry-run` prints the plan and contacts nothing. A failure at any step exits
non-zero, names the cause, and leaves nothing behind: the rename is what makes
that true, so a half-clone is never visible as a store.

### 5. The abstract operation

In `tcw/store/base.py`, a storage-neutral provisioning protocol:

```python
class StoreNotProvisioned(ValueError):
    """The store is declared but not available here."""

class StoreProvisioner(ABC):
    def describe(self) -> str: ...                 # presentation only
    def is_available(self) -> bool: ...
    def ensure_available(self, *, refresh: bool = False,
                         dry_run: bool = False) -> ProvisionResult: ...
```

No signature names a URL, a ref, or a directory. The FS adapter's implementation
reads `repository` and shells out to Git; a tracker adapter would check
credentials and reachability and return the same result shape, and an adapter
that needs nothing implements `ensure_available` as a no-op — a legitimate
implementation, not a stub.

`StoreNotProvisioned` subclasses `ValueError` on purpose: every existing
`except ValueError` around `FsWorkStore.open` keeps working unchanged, and the
call sites that should now say more are updated deliberately rather than by
accident.

### 6. Error surfaces

- `find_node` (`tcw/store/fs.py:157-160`) lets `StoreNotProvisioned` propagate
  instead of flattening it to `None`. This is what fixes the reported symptom:
  `find_node` resolves *this* node, and every `tcw work` command goes through it.
- `_has_work_store` (`tcw/store/fs.py:198-202`) keeps returning `False`.
  **Corrected during implementation** — an earlier draft of this section had it
  propagate too, which is wrong: it asks about *other* nodes, so a parent's
  `tcw work nodes` would raise because one child happened to be unprovisioned,
  turning a legible listing into a hard failure. "No usable store here" is a true
  and useful answer for a node that is not the one being operated on. Reporting a
  *child* as unprovisioned rather than omitting it is a listing-format change,
  and it belongs to the epic's criterion 3 with child B, not here.
- `tcw/work/cli.py`'s six sites move onto one helper that prints either today's
  sentence or, for `StoreNotProvisioned`, the declared remote and
  `run \`tcw provision\``. Six copies of one string become one.
- `tcw validate` (`tcw/validate.py:145-148`) reports the node as declared but not
  provisioned, in its own words, and names the command.
- `tcw work path` exits non-zero with the same message rather than printing a
  path that does not exist.

## Abstraction litmus test

| Operation                                                | Verdict                                                                                                                               |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `is_available()`                                         | **Store interface.** Every adapter can answer "can I be used here"; a tracker checks credentials and reachability.                     |
| `ensure_available(refresh, dry_run)`                     | **Store interface.** The abstract verb is "make yourself usable", not "clone". A no-op is a valid implementation.                      |
| `describe()`                                             | **Store interface**, presentation only — like the existing `locate()`, which is documented as "do not parse it".                       |
| `StoreNotProvisioned`                                    | **Model.** "Declared but not available" is a state any adapter can be in.                                                              |
| Clone / fetch / checkout-a-ref / temp-dir-then-rename    | **Filesystem-adapter private detail.** No abstract analog, and nothing above the adapter may name them.                                 |
| The cache key and XDG layout                             | **Filesystem-adapter private detail.**                                                                                                  |
| The `repository` block in `tcw-config.yaml`              | **Adapter locator**, not a store operation — the same status the project registry already gives paths ("filesystem paths are adapter locators only"). |

The failure mode to watch: a store-interface signature that mentions a URL, a
ref, or a directory. If one appears, the seam moved into the wrong layer.

## Acceptance criteria

1. A node whose config declares `work.repository` and whose store is absent:
   `tcw work list` exits non-zero and its stderr names both the declared remote
   and `tcw provision`. It does **not** say "no tcw work node here".
2. After `tcw provision` on that node, `tcw work list` prints the board and
   `tcw work path` prints the provisioned store's absolute path.
3. Running `tcw provision` a second time exits 0, reports the store as already
   available, and runs no `git fetch` or `git clone` (asserted by intercepting
   the adapter's Git invocation, not by timing).
4. `tcw validate` on the unprovisioned node reports "declared but not
   provisioned" and names `tcw provision`; on a node whose `work.path` is merely
   wrong and which declares no repository, it still reports
   `work.path is not a directory: …` verbatim.
5. A node that declares `work.repository` **and** has a valid `work.path` store
   present resolves to the `work.path` store, and `tcw provision` reports it
   already available without contacting the remote.
6. `tcw provision --dry-run` prints the remote and target and makes no Git
   invocation.
7. A provision that fails — unknown ref, unreachable remote — exits non-zero,
   prints the cause, and leaves no directory at the target path.
8. Git is invoked with stdin closed, so a remote demanding credentials fails
   rather than hanging; enforced by the existing package-wide rule in
   `tests/test_subprocess_stdin.py`.
9. `tests/test_external_work_store.py` passes unmodified.
10. A config with a `repository` that has no `url`, an absolute or `..`-bearing
    `repository.path`, or an unknown key under `repository`, is reported by
    `tcw validate` as a config problem and does not open the store.
11. Every criterion is reproducible from a bare shell, with no Claude hook or
    slash command involved.

## Risks

- **Precedence is where a subtle bug would live.** Rule 1 must consult
  `work.path` exactly as today, including the linked-worktree re-anchoring
  (`tcw/store/fs.py:2444-2446`), or a worktree user's store silently becomes a
  cache clone. Criterion 9 is the guard.
- **`find_node` no longer returning `None` is a behavior change for every caller,**
  including `tcw serve` and the recursion helpers. Each call site has to be
  visited, not just the six in `tcw/work/cli.py`.
- **A config-supplied URL is a supply-chain surface.** The explicit verb is the
  mitigation; printing the remote before contacting it is the second. Neither
  helps if some other command later grows an implicit call — criterion 3's
  interception hook is where a regression would be caught.
- **Cache-key collisions or churn.** A key too specific re-clones the same
  repository per project; too loose, and two refs fight over one checkout.
- **`git clone` of a large orchestrator repository is slow.** Out of scope to
  optimize here, but the command should not look hung: it reports before it
  starts.

## Notes

- The four constraints this design obeys — explicit provisioning, configurable
  checkout defaulting to a cache, all three trees eventually, publication in
  child C — came from the requester at the epic's `request` stage and are not
  reopened here.
- The sibling-defect sweep was scoped to store-location resolution and the
  surfaces that report it (`FsWorkStore.open`, `find_node`, `_has_work_store`,
  `tcw/work/cli.py`'s node resolution, `tcw/validate.py`). One genuine sibling
  defect turned up inside that scope and is fixed here rather than filed: the six
  duplicated "no tcw work node here" strings, which is why the reason could not
  be improved in one place.
