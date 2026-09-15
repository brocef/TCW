# Spec — Fail fast with clear errors on non-Git writes

## Capability changes

**Three entries change; none is added, removed, or restatused.** Recorded in this
item's `capabilities.yaml` sidecar under `changed:`. The test applied was not "is
this user-observable" — every write command is — but "does a ledger **body** state
something this change makes newly true or newly false":

| Entry | The sentence in its body | Why it changes |
| --- | --- | --- |
| `taxonomy/add-a-term` | "A refused add exits non-zero and **writes nothing**" | False today outside git: `tcw taxonomy add` leaves the term folder behind (Problem §1). The promise becomes unconditional. |
| `work/start-a-work-item` | "**Starting work is an atomic claim.**" | False today outside git: the claim's `os.replace` lands and the command dies, so the item is in `active/` while the user sees a traceback (Reproduction). Becomes atomic in outcome. |
| `web/editing` | "Every saved object is immediately checked with TCW's standard validation rules, with any findings shown as post-save warnings" | The editor's write failure changes from HTTP 500 carrying a raw `git add …` command line, after a partial write, to a 4xx carrying the refusal, with nothing written. |

**Deliberately not listed**, with reasons from the ledger rather than from README:

- `cli/scaffold-the-doc-trees` — `tcw init`'s message, exit code and behavior are
  byte-identical after this change; it is the entry the others are aligned *to*.
- `capabilities/add-a-capability`, `capabilities/set-a-capabilitys-status`, and
  the other ~20 write entries — their bodies describe *what* the write does and
  which refusals it already has; none promises anything about a failed write's
  filesystem residue, so none becomes true or false here. Listing all of them
  would record the diff, not the ledger delta.
- `cli/run-from-a-git-worktree` — its "nothing changes for a project that is not
  in a git repository at all" is scoped to that item's re-anchoring change, not a
  standing guarantee about writes. Judged out; a reviewer who disagrees should add
  it to the sidecar rather than reword the body.

No status flips (all three stay `Supported`), no capability is added or removed,
and no taxonomy Vocabulary or Feature entry changes.

## Reproduction

Measured at `aff0cbb`, `tcw 1.0.0` (editable install), macOS, Python 3.14.6.
Fixture: a node scaffolded and committed inside a repository, then `rm -rf .git`,
under a scratch tree with no repository anywhere above it (`git rev-parse
--show-toplevel` → `fatal: not a git repository`). This is the reachable shape:
`tcw init` refuses outside a repository, so a node outside one arrives by the
repository being removed, by an export/tarball copy, or by a `docs/` tree
vendored into a non-git directory.

**Reads are fine** — all exit 0, as pinned:

```
$ tcw work list; tcw work show <slug>; tcw work nodes; tcw validate
$ tcw taxonomy list; tcw taxonomy show widget
$ tcw capabilities list; tcw capabilities show doing/a-thing
   → rc=0 for every one
```

**`tcw init` refuses cleanly** (`tcw/cli.py:30-32`):

```
$ tcw init
tcw init: not inside a git repository. Run `git init` first.
rc=1
```

**`tcw work new` dies with a traceback and leaves a half-item behind:**

```
$ tcw work new "Try a thing"
Traceback (most recent call last):
  ...
  File "tcw/store/fs.py", line 3367, in create_work
    self._stage(*(d / name for name in written))
  File "tcw/store/fs.py", line 2021, in _stage
    git_stage(self.store_git_root, *paths)
  File "tcw/store/fs.py", line 306, in git_stage
    _git(["git", "-C", str(node_root), "add", "--", *live], check=True)
subprocess.CalledProcessError: Command '[... 'git', 'add', '--', '.../state.yaml']'
  returned non-zero exit status 128.
rc=1
$ find docs/work/backlog/2026-08-19-try-a-thing
docs/work/backlog/2026-08-19-try-a-thing/state.yaml     # left on disk
```

**`tcw work start` is the worst case — the item moves, then the traceback:**

```
$ tcw work start 2026-08-19-second-item     # traceback, rc=1
$ ls docs/work/active/
2026-08-19-second-item                       # moved. Nothing said so.
```

`FsWorkStore.start` publishes the claim with `os.replace` (`tcw/store/fs.py:2074`,
and the non-takeover path's `git_stage` at `:2145`) and stages afterwards, so the
rename lands and only the staging fails.

## Problem

### 1. Every filesystem-backed write entry point, measured

The repro fixture above, one command per row, each from a restored copy of the
node. "Mutated" is a recursive file-level `diff -rq` against the pre-command tree.

| Entry point | Today | Filesystem mutated before failing |
| --- | --- | --- |
| `tcw init` (`tcw/cli.py:30`) | clean, rc 1 | no |
| `tcw work init` / `taxonomy init` / `capabilities init` (same `run_init`) | clean, rc 1 | no |
| `tcw work new` | **traceback**, rc 1 | **yes** — `backlog/<slug>/state.yaml` |
| `tcw work start <slug>` | **traceback**, rc 1 | **yes** — item moved `backlog/` → `active/` |
| `tcw work start <slug> --worktree` | **traceback**, rc 1 | **yes** — same move |
| `tcw work edit <slug> --title` | **traceback**, rc 1 | **yes** — `state.yaml` rewritten |
| `tcw work tags add` / `tags rm` | **traceback**, rc 1 | **yes** — `tcw-config.yaml` rewritten |
| `tcw work scaffold spec <backlog-slug>` | **traceback**, rc 1 | **yes** — `spec.draft.md` written |
| `tcw work reconcile <epic>` | **traceback**, rc 1 | **yes** |
| `tcw work submit <slug>` | **traceback**, rc 1 | no (`git_mv` runs `git add` at `tcw/store/fs.py:345` before the `git mv` at `:346`, so it fails before moving) |
| `tcw work complete <slug> --resolution done --confirm` | **traceback**, rc 1 | no |
| `tcw work complete <slug> --resolution wontfix --confirm` | **traceback**, rc 1 | no |
| `tcw work drop <slug> --confirm` | **traceback**, rc 1 | no (`_delete` → `_rm`) |
| `tcw work inbox accept <ref>` | **traceback**, rc 1 | no |
| `tcw work delegate` / `escalate` | refused earlier in this fixture (no child/parent node); both write another node's inbox through the same store writes, so same class | — |
| `tcw taxonomy add` | **traceback**, rc 1 | **yes** — term folder written |
| `tcw taxonomy rm <slug>` | **traceback**, rc 1 | no (`_rm`) |
| `tcw taxonomy extends add` / `rm` | refused earlier (project not registered); reaches `dump_yaml` + `_stage` (`fs.py:1059-1061`, `:1072-1074`) once it is | — |
| `tcw capabilities add` | **traceback**, rc 1 | **yes** — capability folder written |
| `tcw capabilities set --status` | **traceback**, rc 1 | **yes** — `meta.yaml` rewritten |
| `tcw capabilities reset` | refused earlier (local, not an override); reaches `_rm` otherwise | — |
| `tcw capabilities extends add` / `rm` | same as taxonomy's | — |
| `tcw serve` write handlers (`POST /api/work`, `/actions/<a>`, `/api/taxonomy`, `/api/capabilities`, the `PATCH`/`PUT`/`DELETE` routes) | no traceback — every verb handler blanket-catches (`tcw/serve/__init__.py:462-491`) — but HTTP 500 with a raw `git add …` command line as the body | **same partial writes**, via the same store methods |

Every `rc` above is 1 — the traceback exits 1 because Python's uncaught-exception
exit status is 1, so the exit code is already right; only the message is wrong.

### 2. Why the traceback happens

`main()` (`tcw/cli.py:176-182`) catches `ValueError` and nothing else:

```python
try:
    return args.func(args)
except ValueError as error:
    print(f"tcw: {error}", file=sys.stderr)
    return 1
```

Every filesystem-store write ends at `git_stage` (`fs.py:299-306`), `git_rm`
(`:309-311`) or `git_mv` (`:321-346`), all of which run `git` with `check=True`.
Outside a repository `git add` exits 128 and `subprocess.CalledProcessError`
propagates uncaught. The adapter already knows this: `_effect_transition`
comments at `fs.py:3143-3147` that "`CalledProcessError` is not in the CLI's
handled set and would exit as a traceback", and works around it locally for one
case by re-raising as `TransitionCommitError`.

`git_ignored` (`fs.py:314-318`) returns `False` outside a repository by design,
so `git_stage` builds a non-empty pathspec and then fails — there is no accidental
no-op that would save the caller.

### 3. Why files are left behind

The adapter is careful about partial writes and says so: `taxonomy.add` fails
closed "*before* the first mkdir" (`fs.py:1022-1024`), `create_work` rolls back
its directory on a write failure (`fs.py:3360-3366`), `capabilities.set` and
`update_capability` roll back a freshly materialized override (`fs.py:1651-1659`,
`:1948-1963`). But **staging is deliberately outside every one of those
rollbacks** — `_write_node`'s comment (`fs.py:869-871`): "a git failure after
both files landed leaves a fully valid object on disk, and deleting it would
destroy content the caller just wrote." That reasoning is correct and must stay.
The consequence is that a `git add` failure is structurally un-rollbackable, so
the only way to satisfy "no partial write" is to **not reach the write at all**.

### 4. `tcw init` is the odd one out for a reason worth keeping

`run_init` checks `git_root(root)` before scaffolding (`tcw/cli.py:30-32`) and
returns 1 with a one-line message. Its wording is the only phrasing a user has
ever seen for this condition, and it is the natural single source for the rest.

## Goals

1. **Every public write entry point** — every CLI subcommand and every `tcw serve`
   HTTP write route, enumerated in Problem §1 — refuses outside a git repository
   **before its first filesystem mutation**. Scope is the *store operations* those
   surfaces call. Module-level adapter helpers reached only by a direct in-process
   caller (`write_sentinel`, `init`, `ensure_worktree_ignored`) are **excluded by
   name**, with the reasoning in Design; the CLI guard already covers their public
   route, and giving them their own guard would refuse `tcw init` twice.
2. **One wording and one exit code** across every write, `tcw init` included, and
   `tcw init`'s current message and exit code are what the others adopt.
3. **No Python traceback from any `git` subprocess failure** reaches a user, not
   only the missing-repository case — a generic `subprocess.CalledProcessError`
   handler at the CLI boundary that names no component and no subcommand.
4. **Reads keep working outside a repository**, byte-identically to today.
5. The precondition lives in the **filesystem adapter**, so a non-filesystem
   store is untouched by it and the CLI carries no work-command-specific policy.

## Non-goals

- **Making writes work without git.** The contract stands (`README.md:186`,
  `:1076`); this item changes only how the refusal is delivered.
- **Retrofitting rollback around staging.** `_write_node` (`fs.py:869-871`),
  `create_work` (`:3359`, `:3364-3367`), `capabilities.set` (`:1651-1659`) and
  `update_capability` (`:1948-1963`) keep staging outside their rollbacks on
  purpose. Unchanged.
- **Repositories that exist but refuse the write** — corrupt `.git`, a held
  `index.lock`, a rejecting hook, a `safe.directory` ownership refusal, a
  read-only filesystem. Those still fail at `git add`, now with the generic
  concise message instead of a traceback, and possibly after a partial write.
  The generic handler *is* the whole mitigation; classifying git's failure modes
  is not this item.
- **The symlink-containment escape** —
  `2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically`. Git
  refuses to stage anything past a symlink, so its write paths raise the same
  `CalledProcessError` class; the generic handler here removes the traceback its
  spec records as Problem §6, but the containment guards are that item's and
  neither item blocks the other. Its plan (task 5) states the same split.
- **The external-work-store open-time check.** `FsWorkStore.open`
  (`fs.py:2015-2017`) already refuses a configured `work.path` outside a
  repository — for reads as well as writes. Pre-existing, differently scoped,
  untouched.
- **`tcw serve`'s HTTP status taxonomy.** The refusal rides the existing
  `ValueError` → 422 mapping (`serve/__init__.py:196-217`); no new exception type
  and no new status code.
- **The abstract store interfaces** (`tcw/store/base.py`). Nothing there changes.
- **Lifecycle hooks** (`tcw/work/hooks.py:61`) — user shell, no `check=True`,
  failures already surface as hook errors.
- **`git` not installed at all.** `git_root` already catches `FileNotFoundError`
  (`fs.py:101`) and returns `None`, so this change happens to convert that
  traceback into the (slightly misleading) repository message. Improving the
  wording for a missing binary is not in scope; see Risks.

## Design

There is **no single chokepoint that gives both properties**, and the spec says
so rather than pretending otherwise: the adapter writes files *before* it stages
them, so a guard at the staging funnel is too late for "no partial write", and a
guard early enough for that has to sit in each public write method. Two tiers,
each with one job.

### The precondition itself

In `tcw/store/fs.py`, beside `git_stage`/`git_rm` (~`:299`):

```python
NOT_A_REPOSITORY = "not inside a git repository. Run `git init` first."

def require_repository(root: Path) -> None:
    """Refuse a filesystem-store write outside git. Adapter precondition only."""
    if git_root(root) is None:
        raise ValueError(NOT_A_REPOSITORY)
```

`ValueError` because it is already the store interface's idiom for a refused
write (`base.py` `add`/`remove`/`set`/`create`), which means every existing
handler works unchanged: `tcw work new`'s `except _ERRORS` (`work/cli.py:41`,
`:234-235`), taxonomy's and capabilities' per-command `except ValueError`
(`taxonomy/cli.py:72`, `:119`, `:158`, `:172`; `capabilities/cli.py:92`, `:117`,
`:130`, `:157`), `main()`'s backstop (`cli.py:181`), and serve's
`_map_store_error`. **No new plumbing anywhere.**

On the stores, mirroring the existing `_stage`/`_rm`/`_mv` override triple
(`FsTreeStore` `fs.py:798-805`, `FsWorkStore` `fs.py:2020-2027`):

```python
# FsTreeStore
def _require_repository(self) -> None:
    require_repository(self._write_git_root())

def _write_git_root(self) -> Path:
    return self.node_root

# FsWorkStore — the work store's git root can be a different repository
def _write_git_root(self) -> Path:
    return self.store_git_root
```

**Not memoized, deliberately**, though `git_root` shells out at a measured
**6.6 ms** per call. Two reasons, both fatal to a cache:

1. **There is nowhere correct to initialize it.** `FsWorkStore.__init__`
   (`fs.py:1980-1985`) does **not** call `super().__init__()` — it assigns
   `root`, `node_root`, `store_git_root` and `config` itself — so a `_repo_ok`
   attribute added to `FsTreeStore.__init__` (`fs.py:789-792`) would be absent on
   every work store and the first work write would raise `AttributeError`.
2. **A store is not per-command.** `tcw serve` opens stores through `_stores()`
   (`serve/__init__.py:396`) *and* reopens work stores through `_resolve_work()`
   (`:404`), and tests routinely hold one instance across several writes
   (`tests/test_environment_hardness.py:832` does `create` → `start` → `complete`
   on one store). Caching only success misses the dangerous direction: a
   repository removed *after* a cached success would let a retained store mutate
   files and reach `git add` without re-checking. Caching both directions is
   worse — it freezes repository membership for the store's lifetime.

The cost is a handful of `git rev-parse` calls per command on top of the one
`git_root` already makes at store open. Accepted; if a real command ever shows
this in a profile, the fix is to make the *check* cheaper, not to remember its
answer.

### Tier 1 — the guarantee: no traceback, ever

`self._require_repository()` as the first line of all six staging helpers:
`FsTreeStore._stage`/`_rm`/`_mv` (`fs.py:798`, `:801`, `:804`) and
`FsWorkStore._stage`/`_rm`/`_mv` (`fs.py:2020`, `:2023`, `:2026`).

Nearly every filesystem-store write funnels through these three names, so this is
structural: a write method added tomorrow that forgets Tier 2 still fails with
the right message rather than a traceback. It also makes the guard sufficient on
its own for the delete-shaped methods, whose only mutation *is* the `_rm` call —
taxonomy `remove` (`_rm` at `:1040`), capabilities `remove` (`:1558`) and `reset`
(`:1575`), work `_delete` (`:3201`), `delete_artifact` (`:3593`),
`delete_plan_stage` (`:2433`), and `inbox_accept`'s consumption of the source
entry (`:3055`). Those need nothing else.

**Three calls bypass the methods and must be named, not assumed away** — a
`grep -n '^\s*git_\(stage\|rm\|mv\)(' tcw/store/fs.py` finds every one:

- `FsWorkStore.start` calls the module-level `git_stage` directly at `fs.py:2076`
  (take-over branch) and `:2145` (main claim path), because both stage a
  `src`/`dst` pair the claim already renamed. **Tier 1 therefore does not reach
  either.** The guard must be the literal first statement of `start` (`:2054`),
  ahead of the take-over branch's `dump_yaml` (`:2072`) and `os.replace`
  (`:2074`) — not merely "early in the method". This is the one place where the
  two tiers do not overlap, so the plan owns a test that exercises `--take-over`
  outside a repository, not only the ordinary path.
- `ensure_worktree_ignored` (`fs.py:460-468`) is the only filesystem-store write
  outside the store classes: it writes `.gitignore` and then stages it.
  **Corrected at rework:** this said it was unreachable outside a repository
  because its single caller runs it *after* `st.start(...)`, which Tier 2 has
  already refused. That reasoning assumes the node and the work store are the
  same repository. They are not when `work.path` is external, and then the store
  guard passes while the node has no repository at all. The guard belongs in
  `_start`, ahead of the store call, because `--worktree` needs the *node's*
  repository. Same correction applies to `merge_worktree` on the completion side,
  which reads a failed branch lookup as "branch already gone" and so skips the
  merge-back silently. See `rework.md` §1 and §2.

### Tier 2 — fail closed: no partial write

`self._require_repository()` at the top of each public write method whose first
filesystem mutation precedes its staging call, placed where that method's
existing "validate before touching disk" checks already live:

| Method | First mutation it must precede | Covers |
| --- | --- | --- |
| `FsTreeStore._write_node` (`:836`) | `d.mkdir` (`:846`) | taxonomy `add` (`:1006`), `update_term` (`:1232`), capabilities `add` (`:1538`) |
| `FsTaxonomyStore.extends_add` (`:1042`) / `extends_remove` (`:1063`) | `dump_yaml` (`:1060`, `:1073`) | — |
| `FsCapabilitiesStore._write_meta` (`:1591`) | `_atomic_write` (`:1593`) | the second write-before-stage funnel; guarded so Tier 1's structural claim holds for future callers |
| `FsCapabilitiesStore.set` (`:1644`) | `d.mkdir` (`:1648`) | — |
| `FsCapabilitiesStore.update_capability` (`:1915`) | its own `mkdir` (`:1933`) ahead of `_write_node`/`_write_meta` | — |
| `FsCapabilitiesStore.extends_add` (`:1664`) / `extends_remove` (`:1683`) | `dump_yaml` | — |
| `FsWorkStore.start` (`:2054`) — **first statement**, see below | take-over `dump_yaml` (`:2072`), `os.replace` (`:2074`), `git_stage` (`:2076`); main path `:2145` | — |
| `FsWorkStore.write_plan_stage` (`:2412`) | `path.parent.mkdir` (`:2421`) | — |
| `FsWorkStore._write_tags` (`:2734`) | `dump_yaml` (`:2745`) | `register_tags` (`:2749`), `unregister_tags` (`:2753`) |
| `FsWorkStore.inbox_accept` (`:2995`) | `dump_yaml`, attachment `mkdir`, `shutil.copy2`, `os.replace` (`:3042-3048`) | — |
| `FsWorkStore._set_fields_at` (`:3091`) | `dump_yaml` (`:3102`) | `set_field` (`:3088`) |
| `FsWorkStore._effect_transition` (`:3105`) | `mkdir` (`:3131`) | `submit`/`rework`/`complete`/`drop` via `WorkStore.transition` |
| `FsWorkStore.create_work` (`:3259`) | `d.mkdir` (`:3360`) | `create` (`:3069`), which delegates |
| `FsWorkStore.update_work` (`:3371`) — **not at the top**, see below | `_atomic_write_all` (`:3494`) and the reparent `move_to.parent.mkdir` (`:3504`) | — |
| `FsWorkStore.write_artifact` (`:3533`) / `write_draft` (`:3567`) / `write_sidecar` (`:3615`) | `_atomic_write` (`:3557`, `:3582`, `:3655`) | `tcw work scaffold`, artifact and sidecar PUTs |

Nineteen one-line insertions in one file. Six of them (`extends_add` ×2,
`extends_remove` ×2, `_write_tags`, `_set_fields_at`) are the identical
`dump_yaml(p, x); self._stage(p)` shape; folding those into one
`FsTreeStore._write_yaml(path, data)` helper that carries the guard is a net
deletion and the plan's call, not a requirement.

**Two rows are placement-sensitive and must not be read as "at the top":**

- **`update_work`** returns early without writing anything when nothing changed
  (`fs.py:3484-3485`). A guard at the top would make that no-op fail outside git,
  turning a read-shaped call into a refusal. The guard belongs **after** the
  no-change decision and immediately before `_atomic_write_all` (`:3494`), and
  the reparent branch's `mkdir` (`:3504`) is downstream of that point.
- **`start`**, for the opposite reason — see the bypass note below.

Any other Tier-2 method with a "nothing to do" path needs the same treatment.
Walking the list, the only other one is `delete_artifact` (`:3592-3593` skips
`_rm` when the file is absent), and it is Tier-1-only anyway; the remaining
seventeen mutate unconditionally once they pass validation.

**Excluded module-level helpers, named rather than silently skipped** (Goal 1's
narrowing):

| Helper | Writes | Why no guard |
| --- | --- | --- |
| `write_sentinel` (`:107`) | `dump_yaml` (`:127`), never stages | Reached from `init`, itself reached from `run_init`, which already refuses. No independent public route. |
| `init` (`:548`) | `shutil.rmtree` (`:580`), `dump_yaml` (`:585`), `mkdir`/`.gitkeep` (`:592-593`) | `run_init` (`cli.py:30-32`) guards its only public route for the *node's* repository. **Corrected at rework:** that is not the only repository `init` writes to. With `--work-path`, it scaffolds the external tree and rewrites `tcw-config.yaml` before its own `git_root(base)` check refuses, so the refusal leaves total residue. The check has to move above every mutation, resolved against the nearest **existing** ancestor of the target — `git_root` shells out to `git -C <path>` and fails on a path that does not exist yet, which is why it was written late. See `rework.md` §3. |
| `ensure_worktree_ignored` (`:460`) | `.gitignore` via `ensure_ignored` (`:455-456`) before staging (`:467`) | **Corrected at rework — this row was wrong.** It said "unreachable outside a repository, because its single caller runs it *after* `st.start(...)`, which Tier 2 has already refused". That holds only when the node and the work store share a repository. With an external `work.path`, `st.start` is guarded against the *store's* repository and passes while the *node's* is absent, so `ensure_worktree_ignored` runs and writes `.gitignore` after the item has already moved. `_start` requires the node's repository before it touches the store; see `rework.md` §1. |

A direct in-process caller of any of the three bypasses the guarantee. That is the
scope Goal 1 states, and it is honest: these three are adapter scaffolding, not
store operations, and the CLI is the only shipped caller of each.

### The CLI boundary

`run_init` (`cli.py:30-32`) keeps its early check — it must, because it runs
before any store exists — but prints `NOT_A_REPOSITORY` instead of an inline
literal, so the wording has exactly one definition. **Its message and exit code
do not change**, and `tests/test_smoke.py::test_init_refuses_outside_git` keeps
passing unmodified.

`main()` (`cli.py:176-182`) gains one generic handler beside the `ValueError` one:

```python
except subprocess.CalledProcessError as error:
    print(f"tcw: git command failed (exit {error.returncode}): "
          f"{shlex.join(str(a) for a in error.cmd)}", file=sys.stderr)
    return 1
```

It names no component and no subcommand — the only policy it encodes is "a git
subprocess failed", which is true of every component. It deliberately does **not**
re-print `error.stderr`: no `check=True` git call in the adapter captures output
(`fs.py:306`, `:311`, `:342`, `:345`, `:346`, `:365`, `:476` — only `git_root` at
`:99` captures, and it swallows the error), so git's own diagnostic has already
reached the terminal and printing it again would double it.

### How `tcw serve` gets the same treatment

**By construction, with no serve change.** The write handlers call the same store
methods, so Tier 2 refuses them at the same point with the same message and the
same no-partial-write property. The already-present blanket handlers
(`serve/__init__.py:462-491`) mean serve never showed a traceback; what improves
is the response — from `500 server error: Command '[…git add…]' returned non-zero
exit status 128` to a `422` whose JSON body is the one-line message, routed by
the existing `ValueError` branch of `_map_store_error` (`serve/__init__.py:211-215`).

## Abstraction litmus test

- **`require_repository` / `_require_repository` / `_write_git_root`** — *"could a
  non-filesystem store implement this operation?"* **No**, and it should not: a
  Jira or graph-DB adapter has no repository to require. Verdict:
  **filesystem-adapter private detail**, exactly like the `_stage`/`_rm`/`_mv`
  triple it sits beside. `tcw/store/base.py` gains nothing; a remote adapter's
  write methods simply never call it.
- **No new model or store-interface operation.** Every method listed in Tier 2
  already exists with its current signature and contract; each gains a
  precondition, not a capability.
- **The exception type is the one abstract-facing choice**, and it reuses
  existing vocabulary: `ValueError` is already how the abstract interface says
  "this write is refused", so no caller learns a new type and the CLI needs no
  new `except`.
- **The `CalledProcessError` handler in `main()`** is CLI plumbing for a
  subprocess this adapter happens to spawn. It stays generic; against a remote
  store it is simply never reached.

## Acceptance criteria

Criteria 1-4 are checked against the Reproduction fixture: a node scaffolded and
committed inside a repository, then `.git` removed, under a directory tree with
no repository above it. A **manifest** below means a recursive `path → sha256`
map of the node, `.git` excluded.

1. **One wording, one code, on every public write.** Each command below exits
   **1**, prints exactly one line on stderr matching
   ``^tcw[a-z ]*: not inside a git repository\. Run `git init` first\.$``, and
   prints no line containing `Traceback`. The list is Problem §1's table with no
   row omitted, which is what makes it evidence for Goal 1:

   `tcw init` · `tcw work init` · `tcw taxonomy init` · `tcw capabilities init` ·
   `tcw work new "T"` · `tcw work start <slug>` · `tcw work start <slug> --worktree` ·
   `tcw work start <slug> --take-over --owner me` · `tcw work edit <slug> --title X` ·
   `tcw work submit <slug>` · `tcw work rework <review-slug>` ·
   `tcw work complete <slug> --resolution done --confirm` ·
   `tcw work complete <slug> --resolution wontfix --confirm` ·
   `tcw work drop <backlog-slug> --confirm` · `tcw work tags add t` ·
   `tcw work tags rm demo` · `tcw work scaffold spec <backlog-slug>` ·
   `tcw work inbox accept <ref>` · `tcw work reconcile <epic-slug>` ·
   `tcw work delegate <child> "T"` · `tcw work escalate "T"` ·
   `tcw taxonomy add N --slug s` · `tcw taxonomy rm <existing-slug>` ·
   `tcw taxonomy extends add <registered-id>` · `tcw taxonomy extends rm <id>` ·
   `tcw capabilities add p/q N` · `tcw capabilities set p/q --status Supported` ·
   `tcw capabilities reset <override-path>` ·
   `tcw capabilities extends add <registered-id>` ·
   `tcw capabilities extends rm <id>`.

   The last eight rows and `delegate`/`escalate`/`reconcile` need fixture setup
   the Reproduction tree does not have (a registered sibling project, a parent and
   a child node, an epic, an inherited override); building it is the plan's job,
   and a row that cannot be set up is reported as such rather than dropped.
2. **No partial mutation.** For each command in criterion 1, the node's manifest
   before the command is byte-identical to the manifest after it. **Eleven** of
   those commands fail this today, measured one at a time: `work new`,
   `work start`, `work start --worktree`, `work edit`, `work tags add`,
   `work tags rm`, `work scaffold`, `work reconcile`, `taxonomy add`,
   `capabilities add`, `capabilities set`.
3. **The `start` regression specifically.** After `tcw work start <slug>` fails,
   `docs/work/backlog/<slug>/` exists and `docs/work/active/<slug>/` does not.
   Today the item is in `active/` after the traceback. Repeat for
   `--take-over`, which reaches `git_stage` by a different route (`fs.py:2076`).
4. **Reads unaffected, pinned literally.** In the same tree, each of
   `tcw work list`, `tcw work show <slug>`, `tcw work nodes`, `tcw validate`,
   `tcw taxonomy list`, `tcw taxonomy show <slug>`, `tcw capabilities list`,
   `tcw capabilities show <path>` exits **0**. Their stdout is compared against
   golden files captured from the **pre-change tree** by the plan and committed
   with the fixture — not against a remembered baseline. Concretely, the plan runs
   the eight commands at the merge-base commit, writes the outputs into the test
   fixture, and the test diffs against those files.
5. `tests/test_environment_hardness.py::TestWorktreeNode::test_non_git_graph_is_unaffected`
   passes **unmodified**. (Verified green at spec time.)
6. `tests/test_smoke.py::test_init_refuses_outside_git` passes **unmodified**
   (verified green at spec time), and `tcw init`'s stderr outside a repository is
   exactly the literal
   ``tcw init: not inside a git repository. Run `git init` first.`` — pinned as a
   string, not as a comparison against an earlier checkout.
7. `tests/test_work_autocommit.py::test_a_transition_outside_a_repository_fails_in_git_mv_as_it_always_has`
   (`:311-326`) is **rewritten**, not deleted: it expects `ValueError` from
   `st.create("Task", …)` instead of `subprocess.CalledProcessError`, additionally
   asserts `docs/work/backlog/` gained no folder, and its docstring records that
   this item deliberately reverses the behavior its old docstring pinned.
8. **The generic handler is generic — checked behaviorally.** With a
   `subprocess.CalledProcessError` injected by monkeypatching one git helper to
   raise it, `main([...])` returns nonzero, prints no traceback, and prints one
   line beginning `tcw: git command failed`. The **same** injected failure through
   three different components — a `work` write, a `taxonomy` write and a
   `capabilities` write — produces the identical message modulo the git argv it
   quotes. That is the checkable form of "carries no per-command policy"; no
   assertion is made about the handler's source text.
9. **`tcw serve`, every write route.** Against a served node whose repository has
   been removed, each of `POST /api/work`, `POST /api/work/<slug>/actions/start`,
   `POST /api/taxonomy`, `POST /api/capabilities`, `PATCH /api/work/<slug>`,
   `PUT` on a work artifact, and `DELETE` on a work artifact returns **4xx, not
   500**, with `not inside a git repository` in the JSON body, and the node's
   manifest is unchanged across the whole sequence.
10. **No frozen repository membership.** A single `FsWorkStore` instance performs
    one successful guarded write inside a repository; the repository is then
    removed; the next write on that **same instance** is refused with the
    criterion-1 message and mutates nothing. (This is the test the earlier
    memoized design would have failed.)
11. **`pytest` from the repository root is green** — the bare command CI runs
    (`.github/workflows/test.yml:37`, after `pip install -e .[dev]`), with
    `testpaths = ["tests"]` from `pyproject.toml:32`. Run outside any sandbox that
    restricts `git`, since the suite creates throwaway repositories.

## Risks

- **A missed Tier-2 site** leaves a clean message but a surviving partial write.
  Tier 1 caps the damage (never a traceback), but the plan must discharge this by
  walking every `mkdir`, `_atomic_write`, `dump_yaml`, `os.replace` and
  `shutil.move` in `tcw/store/fs.py` and naming the guard that precedes each one,
  rather than trusting this spec's table. The sibling symlink item's plan found
  two sites its spec had missed by doing exactly that walk, and an adversarial
  review of *this* spec found four more (`_write_meta`, `update_work`'s reparent
  `mkdir`, and the two module-level helpers now excluded by name) — treat 19 as a
  floor.
- **Overturning a deliberately pinned test.** `test_a_transition_outside_a_
  repository_fails_in_git_mv_as_it_always_has` says in its docstring "worth
  pinning so nobody 'fixes' it." This item *is* that fix, sanctioned by the
  request. The rewrite must say so in the docstring; silently deleting the test
  would erase the reasoning.
- **`git` absent from `PATH`** produces "not inside a git repository. Run `git
  init` first.", which is misleading. It is strictly better than today's
  `FileNotFoundError` traceback, and detecting the binary separately costs a
  second probe on every write. Named rather than fixed.
- **Guard placement, not guard presence, is the subtle part.** Two of the
  nineteen Tier-2 sites are placement-sensitive in opposite directions
  (`update_work` must be after its no-change return, `start` must be the literal
  first statement). A mechanical "first line of every write method" pass gets one
  of them wrong and turns a no-op into a refusal. The plan must place each by
  reading the method, and criterion 1 must include `--take-over`.
- **The excluded module-level helpers** (`write_sentinel`, `init`,
  `ensure_worktree_ignored`) leave a real hole for a direct in-process caller —
  tests, and any future code that skips the CLI. Accepted and named in Goal 1
  rather than papered over; the mitigation is that all three are adapter
  scaffolding whose only shipped caller is already guarded.
- **Serve's 422** for what is really an environment fault. Accepted: the operator
  reading the message is the person who can act on it, and minting an exception
  type to earn a different status code buys nothing.
- **Per-write cost, accepted rather than cached:** 6.6 ms × one `git rev-parse`
  per guarded call. `tcw work reconcile` and `tcw work inbox accept` are the
  commands where it would show first, and the plan should record the measured
  before/after wall time for one of them rather than assuming it is noise. An
  enormous or network-mounted repository makes each call slower; the same call
  `git_root` already makes at store open, so this is more of a known cost, not a
  new class of one.

## Notes

### Repo-wide sibling sweep (stage-`spec` step 6)

Every `subprocess` use in `tcw/` was checked, not only the reported path:

- `tcw/store/fs.py` — the seven `check=True` git calls (`:306`, `:311`, `:342`,
  `:345`, `:346`, `:365`, `:476`) are the only raisers. `:476` (`git worktree
  add`) is already caught locally at `work/cli.py:602`. `:365` (`git_commit`) is
  reached only through `git_commit_result` (`:385`), which returns an error string
  rather than raising. The rest are the subject of this item.
- `tcw/store/project.py:73-83` — catches `CalledProcessError` **and** `OSError`
  ("OSError covers git absent"). Correct; the model to copy.
- `tcw/serve/runtime.py:46-50` — catches `OSError` and `SubprocessError`. Fine.
- `tcw/work/hooks.py:61-68` — user shell, no `check=True`, `TimeoutExpired`
  handled. Fine.
- `tcw/work/generate.py` — `Popen`, `TimeoutExpired` handled at `:163`, `:172`.
  Fine.
- `tcw/work/cli.py:534` — `git config --get`, no `check`. Fine.
- `tcw/serve/__init__.py:97` — `Popen` for the browser opener, fire-and-forget.

**Partial-write-then-fail paths** are all the same shape and all fixed by the same
guard: staging sits outside four documented rollbacks (`_write_node` `:869-872`,
`create_work` `:3364-3367`, `capabilities.set` `:1651-1659`,
`update_capability` `:1948-1963`), and `FsWorkStore.start` renames before staging
(`:2074`/`:2076` take-over, `:2145` main path). Non-git
triggers for those (held `index.lock`, hooks) remain and are out of scope by
design — `_effect_transition` already handles its own instance by re-raising as
`TransitionCommitError` (`fs.py:3140-3151`), which is the pattern to leave alone.

**No second defect of the reported class was found.** The scope stayed at "every
filesystem-backed write entry point", which the request already set and which
§1 above discharges by enumeration.

### Documentation touched by this change (for the plan)

- `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` — user-facing
  error behavior, as the request's Meta section says.
- `tests/cli/scenarios/01-bootstrap-and-node-identity.md:43-45` currently reads
  "Explicitly not covered here: Behaviour outside a git repository — that is a
  known open backlog item (`2026-07-30-fix-non-git-write-paths-…`)". That
  exclusion, and the pointer to this item, must be replaced with assertions once
  the item lands.
- `skills/tcw-work/SKILL.md` — the driving skill, per the request.

### Assumptions

- **Corrected from an earlier draft of this spec:** `FsWorkStore.__init__`
  (`fs.py:1980-1985`) does **not** call `super().__init__()` — it assigns `root`,
  `node_root`, `store_git_root` and `config` itself. Verified by reading it. Any
  design that adds state to `FsTreeStore.__init__` and expects work stores to
  inherit it is wrong; that is one of the two reasons the guard holds no state
  (see Design).
- `tcw work delegate` and `tcw work escalate` were not reachable in the fixture
  (they need a child or parent node) and are inferred from their store calls
  (`work/cli.py:173-201`) rather than measured. Same for `taxonomy`/`capabilities
  extends` (needs a registered sibling project) and `capabilities reset` (needs an
  inherited override). Everything else in §1's table was run. Criterion 1 requires
  the plan to build the fixtures and close these gaps.

### Review history

This spec was revised after an adversarial review found two critical defects in
its first version: the memoized guard would have raised `AttributeError` on every
`FsWorkStore` write (`FsWorkStore.__init__` does not chain to the base), and the
cache could go stale in the dangerous direction. The memoization is gone. The
review also added `_write_meta`, `update_work`'s reparent `mkdir`, `start`'s
take-over bypass, and the three excluded module-level helpers to the inventory,
and forced Goal 1 to state its scope instead of claiming "every".
