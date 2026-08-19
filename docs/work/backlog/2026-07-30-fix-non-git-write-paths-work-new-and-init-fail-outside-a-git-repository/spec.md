# Spec — Fail fast with clear errors on non-Git writes

## Capability changes

**None.** No capability gains, loses, or changes status. The Git-required write
contract already stands and is documented in prose, not in the ledger:
`README.md:186` ("It refuses outside a git repo (write transitions need git)")
and `README.md:1076` ("a **node** is a git repo with a usable work store").
`cli/scaffold-the-doc-trees` already says "scaffold component trees in the
current git work tree". Nothing in the ledger asserts that a write outside a
repository works, so nothing there becomes false or newly true — only the
failure's shape changes. No taxonomy Vocabulary or Feature entry changes either.

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
| `tcw work submit <slug>` | **traceback**, rc 1 | no (`git_mv` stages first, `tcw/store/fs.py:345`) |
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
comments at `fs.py:3143-3146` that "`CalledProcessError` is not in the CLI's
handled set and would exit as a traceback", and works around it locally for one
case by re-raising as `TransitionCommitError`.

`git_ignored` (`fs.py:314-319`) returns `False` outside a repository by design,
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

1. **Every** filesystem-backed write entry point — CLI and `tcw serve` alike —
   refuses outside a git repository **before its first filesystem mutation**.
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
  `ValueError` → 422 mapping (`serve/__init__.py:194-217`); no new exception type
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
def _write_git_root(self) -> Path:
    return self.node_root

def _require_repository(self) -> None:
    if not self._repo_ok:                       # memoized: git_root costs ~6.6 ms
        require_repository(self._write_git_root())
        self._repo_ok = True

# FsWorkStore — the work store's git root can be a different repository
def _write_git_root(self) -> Path:
    return self.store_git_root
```

Memoized because `git_root` shells out: measured **6.6 ms** per call on this
machine, in-repo and out. A store instance is per-command, so one call per
command is the right budget; a multi-write command (`reconcile`, `inbox accept`)
would otherwise pay it per staged path. Only success is cached.

### Tier 1 — the guarantee: no traceback, ever

`self._require_repository()` as the first line of all six staging helpers:
`FsTreeStore._stage`/`_rm`/`_mv` (`fs.py:798`, `:801`, `:804`) and
`FsWorkStore._stage`/`_rm`/`_mv` (`fs.py:2020`, `:2023`, `:2026`).

Every filesystem-store write in the codebase funnels through these three names,
so this is structural: a write method added tomorrow that forgets Tier 2 still
fails with the right message rather than a traceback. It also makes the guard
sufficient on its own for the delete-shaped methods, whose only mutation *is* the
`_rm`/`_mv` — taxonomy `remove` (`:1033`), capabilities `remove` (`:1551`) and
`reset` (`:1560`), work `_delete` (`:3199`), `delete_artifact` (`:3586`),
`delete_plan_stage` (`:2426`). Those need nothing else.

### Tier 2 — fail closed: no partial write

`self._require_repository()` at the top of each public write method whose first
filesystem mutation precedes its staging call, placed where that method's
existing "validate before touching disk" checks already live:

| Method | First mutation it must precede | Covers |
| --- | --- | --- |
| `FsTreeStore._write_node` (`:836`) | `d.mkdir` (`:846`) | taxonomy `add` (`:1006`), `update_term` (`:1232`), capabilities `add` (`:1538`) |
| `FsTaxonomyStore.extends_add` (`:1042`) / `extends_remove` (`:1063`) | `dump_yaml` (`:1060`, `:1073`) | — |
| `FsCapabilitiesStore.set` (`:1644`) | `d.mkdir` (`:1648`) | — |
| `FsCapabilitiesStore.update_capability` (`:1915`) | its own `mkdir` ahead of `_write_node`/`_write_meta` | — |
| `FsCapabilitiesStore.extends_add` (`:1664`) / `extends_remove` (`:1683`) | `dump_yaml` | — |
| `FsWorkStore.start` (`:2054`) | `os.replace` (`:2074`) and the main claim path (`:2145`) | — |
| `FsWorkStore.write_plan_stage` (`:2412`) | `path.parent.mkdir` (`:2421`) | — |
| `FsWorkStore._write_tags` (`:2734`) | `dump_yaml` (`:2745`) | `register_tags` (`:2749`), `unregister_tags` (`:2753`) |
| `FsWorkStore.inbox_accept` (`:2995`) | its destination writes | — |
| `FsWorkStore._set_fields_at` (`:3091`) | `dump_yaml` (`:3102`) | `set_field` (`:3088`) |
| `FsWorkStore._effect_transition` (`:3105`) | `mkdir` (`:3131`) | `submit`/`rework`/`complete`/`drop` via `WorkStore.transition` |
| `FsWorkStore.create_work` (`:3259`) | `d.mkdir` (`:3360`) | `create` (`:3069`), which delegates |
| `FsWorkStore.update_work` (`:3371`) | its state/body writes | — |
| `FsWorkStore.write_artifact` (`:3533`) / `write_draft` (`:3567`) / `write_sidecar` (`:3615`) | `_atomic_write` | `tcw work scaffold`, artifact PUTs |

Eighteen one-line insertions in one file. Six of them (`extends_add` ×2,
`extends_remove` ×2, `_write_tags`, `_set_fields_at`) are the identical
`dump_yaml(p, x); self._stage(p)` shape; folding those into one
`FsTreeStore._write_yaml(path, data)` helper that carries the guard is a net
deletion and the plan's call, not a requirement.

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
the existing `ValueError` branch of `_map_store_error` (`serve/__init__.py:213-216`).

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
no repository above it.

1. **One wording, one code.** Each of these exits **1**, prints exactly one line
   on stderr matching `^tcw[a-z ]*: not inside a git repository\. Run `git init`
   first\.$`, and prints no line containing `Traceback`:
   `tcw init` · `tcw work init` · `tcw work new "T"` · `tcw work start <slug>` ·
   `tcw work start <slug> --worktree` · `tcw work edit <slug> --title X` ·
   `tcw work submit <slug>` · `tcw work complete <slug> --resolution done --confirm` ·
   `tcw work drop <slug> --confirm` · `tcw work tags add t` ·
   `tcw work scaffold spec <backlog-slug>` · `tcw work inbox accept <ref>` ·
   `tcw taxonomy add N --slug s` · `tcw taxonomy rm <existing-slug>` ·
   `tcw capabilities add p/q N` · `tcw capabilities set p/q --status Supported`.
2. **No partial mutation.** A recursive `path → sha256` manifest of the node
   (excluding `.git`, which is absent) taken before each command in criterion 1 is
   byte-identical to the manifest taken after it. (Eight of those commands fail
   this today — measured: `work new`, `work start`, `work start --worktree`,
   `work edit`, `work tags add`, `work scaffold`, `taxonomy add`,
   `capabilities add`, `capabilities set`.)
3. **The `start` regression specifically.** After `tcw work start <slug>` fails,
   `docs/work/backlog/<slug>/` exists and `docs/work/active/<slug>/` does not.
   (Today the item is in `active/` after the traceback.)
4. **Reads unaffected.** In the same tree, each of `tcw work list`,
   `tcw work show <slug>`, `tcw work nodes`, `tcw validate`, `tcw taxonomy list`,
   `tcw taxonomy show <slug>`, `tcw capabilities list`,
   `tcw capabilities show <path>` exits **0**, and each one's stdout is
   byte-identical to the same command run before the guard landed.
5. `tests/test_environment_hardness.py::TestWorktreeNode::test_non_git_graph_is_unaffected`
   passes **unmodified**.
6. `tests/test_smoke.py::test_init_refuses_outside_git` passes **unmodified**, and
   `tcw init`'s stderr outside a repository is byte-identical to today's.
7. `tests/test_work_autocommit.py::test_a_transition_outside_a_repository_fails_in_git_mv_as_it_always_has`
   (`:311-326`) is **rewritten**, not deleted: it expects `ValueError` from
   `st.create("Task", …)` instead of `subprocess.CalledProcessError`, additionally
   asserts `docs/work/backlog/` gained no folder, and its docstring records that
   this item deliberately reverses the behavior its old docstring pinned.
8. **The generic handler.** With a `subprocess.CalledProcessError` injected from
   inside a command (monkeypatch a git helper to raise it), `main([...])` returns
   nonzero, stderr is one line beginning `tcw: git command failed`, and no
   traceback is printed. The handler's source in `tcw/cli.py` contains no
   component name (`work`, `taxonomy`, `capabilities`) and no subcommand name.
9. **`tcw serve`.** `POST /api/work` against a node whose repository has been
   removed returns a 4xx (not 500) whose JSON body contains
   `not inside a git repository`, and the node's file manifest is unchanged by the
   request.
10. **Memoization holds.** With `tcw.store.fs.git_root` counted by monkeypatch, a
    single `FsWorkStore` instance performing several writes calls it at most once
    from `_require_repository`.
11. `pytest` is green in full.

## Risks

- **A missed Tier-2 site** leaves a clean message but a surviving partial write.
  Tier 1 caps the damage (never a traceback), but the plan must discharge this by
  walking every `mkdir`, `_atomic_write`, `dump_yaml`, `os.replace` and
  `shutil.move` in `tcw/store/fs.py` and naming the guard that precedes each one,
  rather than trusting this spec's table. The sibling symlink item's plan found
  two sites its spec had missed by doing exactly that walk — treat 18 as a floor.
- **Overturning a deliberately pinned test.** `test_a_transition_outside_a_
  repository_fails_in_git_mv_as_it_always_has` says in its docstring "worth
  pinning so nobody 'fixes' it." This item *is* that fix, sanctioned by the
  request. The rewrite must say so in the docstring; silently deleting the test
  would erase the reasoning.
- **`git` absent from `PATH`** produces "not inside a git repository. Run `git
  init` first.", which is misleading. It is strictly better than today's
  `FileNotFoundError` traceback, and detecting the binary separately costs a
  second probe on every write. Named rather than fixed.
- **Stale memoization** if a long-lived process holds a store across a `git init`.
  `tcw serve` builds its stores per request (`self._stores()`); the plan must
  confirm that before keeping the cache, or scope the cache to the store instance
  serve actually discards.
- **Serve's 422** for what is really an environment fault. Accepted: the operator
  reading the message is the person who can act on it, and minting an exception
  type to earn a different status code buys nothing.
- **Per-write cost** if memoization is dropped or missed: 6.6 ms × every staged
  path. `tcw work reconcile` and `tcw work inbox accept` are the commands where
  that would show.
- **`git rev-parse` in an enormous or network-mounted repository** could exceed
  the measured 6.6 ms. Same call `git_root` already makes at store open, so the
  guard adds at most one more per command, not a new class of cost.

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
guard: staging sits outside four documented rollbacks (`_write_node` `:869`,
`create_work` `:3359`, `capabilities.set` `:1651`, `update_capability` `:1948`),
and `FsWorkStore.start` renames before staging (`:2074`, `:2145`). Non-git
triggers for those (held `index.lock`, hooks) remain and are out of scope by
design — `_effect_transition` already handles its own instance by re-raising as
`TransitionCommitError` (`fs.py:3140-3151`), which is the pattern to leave alone.

**No second defect of the reported class was found.** The scope stayed at "every
filesystem-backed write entry point", which the request already set and which
§1 above discharges by enumeration.

### Documentation touched by this change (for the plan)

- `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` — user-facing
  error behavior, as the request's Meta section says.
- `tests/cli/scenarios/01-bootstrap-and-node-identity.md:42-45` currently reads
  "Explicitly not covered here: Behaviour outside a git repository — that is a
  known open backlog item (`2026-07-30-fix-non-git-write-paths-…`)". That
  exclusion, and the pointer to this item, must be replaced with assertions once
  the item lands.
- `skills/tcw-work/SKILL.md` — the driving skill, per the request.

### Assumptions

- `FsWorkStore.__init__` (`fs.py:1980`) chains to `FsTreeStore.__init__`
  (`fs.py:789`), so a `_repo_ok` attribute initialized in the base is present on
  every store. Read as true from the code but not executed; the plan should
  confirm before relying on it.
- `tcw work delegate` and `tcw work escalate` were not reachable in the fixture
  (they need a child or parent node) and are inferred from their store calls
  (`work/cli.py:173-201`) rather than measured. Everything else in §1's table was
  run.
