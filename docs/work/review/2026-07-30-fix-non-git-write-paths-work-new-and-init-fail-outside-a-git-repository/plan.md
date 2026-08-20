# Plan — Fail fast with clear errors on non-Git writes

## Mutation walk (the spec's first Risk, discharged)

The spec's Risks section required walking every filesystem mutation in
`tcw/store/fs.py` and naming the guard that precedes each, rather than trusting
the spec's Tier-2 table. Done, mechanically:

```
grep for: mkdir | _atomic_write | _atomic_write_all | dump_yaml | os.replace
        | shutil.move | shutil.copy2 | shutil.rmtree | write_text | touch
        | unlink | rename          →  57 hits in tcw/store/fs.py
```

Every hit, with the guard that precedes it. Line numbers are navigation hints
only — three sibling items land in this file after this one, so **locate by
symbol**.

| Line | Symbol | Mutation | Guard that precedes it |
| --- | --- | --- | --- |
| 127 | `write_sentinel` | `dump_yaml` | **none — excluded by Goal 1.** Reached only from `init`, itself reached from `run_init`, which refuses. |
| 343 | `git_mv` | `shutil.move` | Tier 1 on `_mv` (its only store caller) |
| 455 | `ensure_ignored` | `gi.write_text` | **none — excluded by Goal 1.** Reached from `ensure_worktree_ignored`, whose only caller runs it after `st.start(...)` (`work/cli.py:545` then `:557`). |
| 580, 585, 592, 593 | `init` | `rmtree`, `dump_yaml`, `mkdir`, `touch` | **none — excluded by Goal 1.** `run_init` (`cli.py:30-32`) guards its only public route. |
| 637 | `dump_yaml` | `write_text` | primitive; guarded at each caller below |
| 737, 740 | `_atomic_write` | `write_text`, `unlink` | primitive; guarded at each caller below |
| 763, 768 | `_atomic_write_all` | `write_text`, `unlink` | primitive; guarded at each caller below |
| 846, 848, 867 | `FsTreeStore._write_node` | `mkdir`, `_atomic_write_all`, `rmtree` | **Tier 2 on `_write_node`** |
| 1060 | `FsTaxonomyStore.extends_add` | `dump_yaml` | **Tier 2 on `extends_add`** |
| 1073 | `FsTaxonomyStore.extends_remove` | `dump_yaml` | **Tier 2 on `extends_remove`** |
| 1593 | `FsCapabilitiesStore._write_meta` | `_atomic_write` | **Tier 2 on `_write_meta`** |
| 1648, 1658 | `FsCapabilitiesStore.set` | `mkdir`, `rmtree` | **Tier 2 on `set`** (ahead of the `mkdir`; `_write_meta`'s own guard is redundant here and that is fine) |
| 1680 | `FsCapabilitiesStore.extends_add` | `dump_yaml` | **Tier 2 on `extends_add`** |
| 1693 | `FsCapabilitiesStore.extends_remove` | `dump_yaml` | **Tier 2 on `extends_remove`** |
| 1933, 1941, 1962 | `FsCapabilitiesStore.update_capability` | `mkdir`, `unlink`, `rmtree` | **Tier 2 on `update_capability`** |
| 2072, 2074 | `FsWorkStore.start` (take-over) | `dump_yaml`, `os.replace` | **Tier 2, first statement of `start`** |
| 2116 | `FsWorkStore.start` | `claiming.mkdir` | same |
| 2132, 2138, 2141, 2143 | `FsWorkStore.start` (main claim) | `os.replace` ×3, `dump_yaml` | same |
| 2421, 2422 | `FsWorkStore.write_plan_stage` | `mkdir`, `_atomic_write` | **Tier 2 on `write_plan_stage`** |
| 2745 | `FsWorkStore._write_tags` | `dump_yaml` | **Tier 2 on `_write_tags`** |
| 3042, 3043, 3046, 3047, 3048 | `FsWorkStore.inbox_accept` | `dump_yaml`, `write_text`, `mkdir`, `copy2`, `os.replace` | **Tier 2 on `inbox_accept`** |
| 3057, 3059, 3061, 3063 | `FsWorkStore.inbox_accept` (teardown) | `rmtree`, `unlink`, rollback `rmtree` ×2 | same guard; all downstream of `_stage(destination)` at `:3049` |
| 3102 | `FsWorkStore._set_fields_at` | `dump_yaml` | **Tier 2 on `_set_fields_at`** |
| 3131 | `FsWorkStore._effect_transition` | `mkdir` | **Tier 2 on `_effect_transition`** |
| 3360, 3363, 3365 | `FsWorkStore.create_work` | `mkdir`, `_atomic_write`, `rmtree` | **Tier 2 on `create_work`** |
| 3494, 3504 | `FsWorkStore.update_work` | `_atomic_write_all`, reparent `mkdir` | **Tier 2 on `update_work`, placed after the no-change return at `:3484-3485`** |
| 3557 | `FsWorkStore.write_artifact` | `_atomic_write` | **Tier 2 on `write_artifact`** |
| 3582 | `FsWorkStore.write_draft` | `_atomic_write` | **Tier 2 on `write_draft`** |
| 3655 | `FsWorkStore.write_sidecar` | `_atomic_write` | **Tier 2 on `write_sidecar`** |

**The walk found no method the spec's table missed** — the nineteen Tier-2 sites
stand, and the three excluded helpers are the three the spec already named. It
did find three things the spec did not predict; they change tests, not the guard
list, and are recorded in `## Notes`.

## Ordering rationale

**The two tiers are not split into separate commits.** The spec presents them as
two ideas, and the obvious reading is "Tier 1 first, it's smaller" — that is the
sequencing trap. The one test that has to be reversed
(`test_a_transition_outside_a_repository_fails_in_git_mv_as_it_always_has`)
asserts, in its rewritten form, both `ValueError` *and* that no folder was left
behind. Tier 1 alone gives the first and fails the second, so a Tier-1-first
commit would have to land the test half-asserted and edit it again one commit
later. So each store gets **both** tiers in one commit (tasks 2 and 3), and the
rewritten test lands with the work store — correct the moment it appears, which
is what "the rewrite ships with the change that reverses it" means.

The split that *does* pay is by store, not by tier.

Task 1 is a pure addition with no call sites, so tasks 2 and 3 are call-site
edits only. The stores are separate commits so a bisect names one, and because
the three sibling items in this batch all land in `tcw/store/fs.py` afterwards.
The CLI boundary (task 4) is last of the code tasks because it is the only one
that can be verified independently of the guard.

## Tasks

### 1. The precondition, with no call sites

**Modifies** `tcw/store/fs.py`:

- Module level, immediately after `git_rm` (currently `:311`):

```python
NOT_A_REPOSITORY = "not inside a git repository. Run `git init` first."


def require_repository(root: Path) -> None:
    """Refuse a filesystem-store write outside git.

    A filesystem-adapter precondition, not a model concept: a remote store has
    no repository to require. Raises `ValueError` because that is already the
    store interface's idiom for a refused write, so every existing CLI and
    HTTP handler reports it without new plumbing.
    """
    if git_root(root) is None:
        raise ValueError(NOT_A_REPOSITORY)
```

- On `FsTreeStore`, beside `_stage`/`_rm`/`_mv` (currently `:798-805`):

```python
def _write_git_root(self) -> Path:
    return self.node_root

def _require_repository(self) -> None:
    require_repository(self._write_git_root())
```

- On `FsWorkStore`, beside its `_stage`/`_rm`/`_mv` override triple (currently
  `:2020-2027`), the one-line override:

```python
def _write_git_root(self) -> Path:
    return self.store_git_root      # may be a different repository (work.path)
```

**No state, no memoization** — `FsWorkStore.__init__` does not call
`super().__init__()`, so anything added to `FsTreeStore.__init__` is absent on
work stores; and a store instance outlives a single write in `tcw serve` and in
tests, so a cached answer can go stale in the direction that matters.

**Creates** `tests/test_non_git_writes.py` with four unit tests of the helper:

1. `require_repository(<a git repo>)` returns `None`.
2. `require_repository(<a plain directory>)` raises `ValueError` whose `str()`
   is exactly `NOT_A_REPOSITORY`.
3. `FsWorkStore.open(root)._write_git_root() == FsWorkStore.open(root).store_git_root`
   and `FsTaxonomyStore.open(root)._write_git_root() == FsTaxonomyStore.open(root).node_root`.
4. **The no-cache pin.** `assert FsWorkStore.__init__ is not FsTreeStore.__init__`
   — a comment records why it matters: `FsWorkStore.__init__` does not call
   `super().__init__()`, so any state added to `FsTreeStore.__init__` would be
   missing on every work store. If a future change makes the guard stateful,
   this test is the one that has to be read before doing it.

**Proves:** `pytest tests/test_non_git_writes.py`. Nothing else changes, so the
full suite is green by construction.

### 2. Guard the work store (Tier 2 + Tier 1)

**Modifies** `tcw/store/fs.py`, `FsWorkStore` only. `self._require_repository()`
added to, in file order:

| Symbol | Placement |
| --- | --- |
| `_stage`, `_rm`, `_mv` (`:2020-2027`) | first line of each — Tier 1 |
| `start` (`:2054`) | **literal first statement**, ahead of the take-over branch and the `.claiming/` dance |
| `write_plan_stage` (`:2412`) | first line |
| `_write_tags` (`:2734`) | first line — covers `register_tags`, `unregister_tags` |
| `inbox_accept` (`:2995`) | first line |
| `_set_fields_at` (`:3091`) | first line — covers `set_field` |
| `_effect_transition` (`:3105`) | first line — covers `submit`/`rework`/`complete`/`drop` |
| `create_work` (`:3259`) | first line — covers `create` |
| `update_work` (`:3371`) | **after** the no-change early return (`:3484-3485`), immediately before `_atomic_write_all` (`:3494`) |
| `write_artifact` (`:3533`), `write_draft` (`:3567`), `write_sidecar` (`:3615`) | first line |

**Modifies** `tests/test_work_autocommit.py` —
`test_a_transition_outside_a_repository_fails_in_git_mv_as_it_always_has`
(`:311-326`) is rewritten in this commit, not deleted:

- rename to `test_a_write_outside_a_repository_is_refused_before_it_writes`;
- `pytest.raises(ValueError, match="not inside a git repository")` around
  `st.create("Task", created="2026-01-01")`;
- add `assert not any((root / "docs" / "work" / "backlog").iterdir())`;
- docstring records that this item deliberately reverses what the old docstring
  pinned ("worth pinning so nobody 'fixes' it" — this *is* that fix, sanctioned
  by the request), so the reversal is legible in `git log -p`.

**Adds** to `tests/test_non_git_writes.py`, all against a store whose `.git` was
removed after seeding: `create_work`, `update_work` (a real change), `start`,
`start(..., take_over=True)`, `_effect_transition` via `submit`, `set_field`,
`register_tags`, `inbox_accept`, `write_artifact`, `write_draft`,
`write_sidecar`, `write_plan_stage` each raise `ValueError` matching
`not inside a git repository`; `_delete` and `delete_artifact` too (Tier 1
only). Each assertion is paired with a **directory-inclusive** manifest compare
(see Verification) so `docs/work/.claiming/` cannot slip through.

**Plus two placement regressions**, the ones a mechanical "first line
everywhere" pass would break or miss:

- `update_work(slug)` with no changed field, **outside a repository**, returns
  the item's `WorkDetail` and does **not** raise.
- `start(slug, take_over=True)` outside a repository raises before
  `os.replace`, and `docs/work/.claiming/` does not exist afterwards.

**Plus the no-frozen-membership regression (criterion 10).** One store
instance, inside a repository: `st.create("First")` succeeds; then
`shutil.rmtree(root / ".git")`; then `st.create("Second")` on the **same
instance** raises `ValueError` matching `not inside a git repository`, and
`docs/work/backlog/` gained no second folder. This is the test a memoized guard
would have failed, and it is why the guard holds no state.

**Proves:** `pytest tests/test_non_git_writes.py tests/test_work_autocommit.py
tests/test_work.py tests/test_external_work_store.py`, then the full suite.
`tests/test_environment_hardness.py::TestWorktreeNode::test_non_git_graph_is_unaffected`
must pass **unmodified** at this commit (criterion 5) — this is the task that
could break it, since it is the first one to guard anything, and the guard must
not reach a read path.

### 3. Guard the taxonomy and capabilities stores (Tier 2 + Tier 1)

**Modifies** `tcw/store/fs.py`. `self._require_repository()` added to:

| Symbol | Placement |
| --- | --- |
| `FsTreeStore._stage`, `_rm`, `_mv` (`:798-805`) | first line of each — Tier 1 |
| `FsTreeStore._write_node` (`:836`) | first line, ahead of `d.mkdir` — covers taxonomy `add`/`update_term` and capabilities `add` |
| `FsTaxonomyStore.extends_add` (`:1042`), `extends_remove` (`:1063`) | first line |
| `FsCapabilitiesStore._write_meta` (`:1591`) | first line |
| `FsCapabilitiesStore.set` (`:1644`) | first line, ahead of `d.mkdir` |
| `FsCapabilitiesStore.update_capability` (`:1915`) | first line, ahead of `d.mkdir` |
| `FsCapabilitiesStore.extends_add` (`:1664`), `extends_remove` (`:1683`) | first line |

**Adds** to `tests/test_non_git_writes.py`: against stores whose `.git` was
removed, `FsTaxonomyStore.add`, `update_term`, `remove`, `extends_add`,
`extends_remove` and `FsCapabilitiesStore.add`, `set`, `update_capability`,
`remove`, `reset`, `extends_add`, `extends_remove` each raise `ValueError`
matching `not inside a git repository`, each paired with a manifest compare. The
`add` cases carry the sharpest assertion, since today they leave the folder:
`assert not (root / "docs" / "taxonomy" / "gadget").exists()`.

`extends_add`/`extends_remove` need a registered sibling project; build it with
the same two-node pattern `tests/test_capabilities_federation.py` already uses,
then remove `.git` from the node under test.

**Proves:** `pytest tests/test_non_git_writes.py tests/test_taxonomy.py
tests/test_capabilities.py tests/test_capabilities_federation.py
tests/test_capabilities_reset.py`, then the full suite.

### 4. The CLI boundary

**Modifies** `tcw/cli.py`:

- `run_init` (`:30-32`) prints `f"tcw init: {NOT_A_REPOSITORY}"` instead of the
  inline literal, importing `NOT_A_REPOSITORY` from `tcw.store.fs`. The emitted
  bytes are unchanged; this only makes the wording single-sourced.
- `main()` (`:176-182`) gains, beside the existing `except ValueError`:

```python
except subprocess.CalledProcessError as error:
    print(f"tcw: git command failed (exit {error.returncode}): "
          f"{shlex.join(str(a) for a in error.cmd)}", file=sys.stderr)
    return 1
```

with `import shlex` and `import subprocess` added at the top. No `error.stderr`
is printed: no `check=True` git call in `tcw/store/fs.py` captures output
(`:306`, `:311`, `:342`, `:345`, `:346`, `:365`, `:476`), so git's own message
already reached the terminal.

**Adds** to `tests/test_non_git_writes.py`:

- `main(["init"])` in a plain directory returns 1 and stderr is exactly
  ``tcw init: not inside a git repository. Run `git init` first.`` (criterion 6,
  pinned as a literal string).
- **The generic-handler test (criterion 8), behavioral.** Monkeypatch
  `tcw.store.fs._git` to raise `subprocess.CalledProcessError(128, ["git",
  "add", "x"])`, then drive one `work` write, one `taxonomy` write and one
  `capabilities` write through `main([...])` inside a real repository. Each
  returns nonzero, prints no `Traceback`, and prints the identical single line
  `tcw: git command failed (exit 128): git add x`. Identical output across three
  components is the checkable form of "the handler carries no per-command
  policy"; no assertion is made about the handler's source text.

**Proves:** `pytest tests/test_non_git_writes.py tests/test_smoke.py`, then the
full suite. `tests/test_smoke.py::test_init_refuses_outside_git` must still pass
**unmodified** (criterion 6).

### 5. `tcw serve` write routes (tests only, no code change expected)

**Modifies** `tests/test_serve_write.py`. Add a `_non_git_node` helper — the
existing `_node(tmp_path)` plus `_seed`, then `shutil.rmtree(root / ".git")` —
and one test that drives every write route against it:
`POST /api/work`, `POST /api/work/<slug>/actions/start`, `POST /api/taxonomy`,
`POST /api/capabilities`, `PATCH /api/work/<slug>`, `PUT` on a work artifact,
`DELETE` on a work artifact. Each returns **4xx, not 500**, with
`not inside a git repository` in the JSON body; the node's manifest is unchanged
across the whole sequence (criterion 9).

If any route returns 500, that is a real finding, not a test to relax: it means
the store method behind it has no guard, and the fix belongs in task 2 or 3.
Recorded here as the expected outcome rather than assumed away.

**Proves:** `pytest tests/test_serve_write.py`.

### 6. End-to-end CLI refusal matrix (criteria 1-4)

**Creates** `tests/cli/scenarios/14-non-git-writes.md` — the scenario document
for the shipped-binary run, listing every row of the spec's Problem §1 table as
a numbered assertion, in the style of the existing scenarios.

**Adds** to `tests/test_non_git_writes.py` an in-process matrix over `main()`
covering every command in acceptance criterion 1, each asserting exit 1, one
stderr line matching
``^tcw[a-z ]*: not inside a git repository\. Run `git init` first\.$``, no
`Traceback`, and an unchanged manifest. Fixtures needed beyond the basic node:

- a registered sibling project (`extends add`/`rm` rows) — the
  `test_capabilities_federation.py` two-node pattern;
- a parent and a child node (`delegate`, `escalate`) — the
  `tests/test_recursion.py` pattern;
- an epic with one child slice (`reconcile`);
- an inherited capability with a local override (`capabilities reset`).

A row whose fixture cannot be built is reported in `outcome.md` as unverified,
never silently dropped.

**Creates** `tests/fixtures/non_git_reads/` holding golden stdout for the eight
read commands of criterion 4, captured **before** the guard lands. Capture
procedure, run once at the start of this task: `git stash` the working tree,
build the fixture node, run the eight commands, write each stdout to
`tests/fixtures/non_git_reads/<command>.txt`, `git stash pop`. The test then
rebuilds the same fixture and diffs. This replaces the spec's earlier
"byte-identical to before the guard landed", which had no stated baseline.

**Proves:** `pytest tests/test_non_git_writes.py`, then the full suite.

### 7. Capability reconciliation

**Modifies** three capability bodies, matching the `changed:` list in this
item's `capabilities.yaml` sidecar. No status changes — all three stay
`Supported`.

- `docs/capabilities/taxonomy/add-a-term/description.md` — its "A refused add
  exits non-zero and writes nothing" is currently false outside a repository.
  Make the promise unconditional in one clause, naming the git case.
- `docs/capabilities/work/start-a-work-item/description.md` — its "Starting work
  is an atomic claim" is currently false outside a repository (the claim lands,
  the command dies). One clause: a claim that cannot be recorded is refused
  before the item moves.
- `docs/capabilities/web/editing/description.md` — one sentence that a save the
  store refuses is reported as such, with nothing written, rather than as a
  server error.

Each edit goes through `tcw capabilities set`/the store, not a hand edit of
`meta.yaml`, and `Planning doc:` is left alone (these are amendments to existing
entries, not new ones).

**Proves:** `tcw capabilities check` and `tcw validate` both exit 0; `tcw
capabilities show <path>` renders each amended body.

### 8. Documentation Sync pass

Executes the block below over the finished diff. **Modifies**
`docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`,
`skills/tcw-work/SKILL.md`, and
`tests/cli/scenarios/01-bootstrap-and-node-identity.md`.

**Proves:** `pytest tests/test_documentation_config.py
tests/test_documentation_sync_wiring.py tests/test_shipped_prompts.py
tests/test_skill_lifecycle_parity.py`, then the full suite.

## Documentation Sync

Evaluated all four entries (`tcw work docs`, and the `documentation-sync` skill):

### `docs/changelogs/upcoming.md` — `[Any-Code-Change]` **fires**

Under **Fixed**: writes to a filesystem-backed store outside a git repository
now raise `ValueError` before any filesystem mutation instead of dying in
`git_stage` with an unhandled `CalledProcessError` — one
`require_repository`/`_require_repository` guard applied at
`FsTreeStore`/`FsWorkStore`'s `_stage`/`_rm`/`_mv` and at nineteen public write
methods. Name the two placement exceptions (`update_work` after its no-change
return, `start` as its first statement) and the three module-level helpers left
unguarded by scope (`write_sentinel`, `init`, `ensure_worktree_ignored`). Under
**Added**: a generic `subprocess.CalledProcessError` handler in `main()`.

### `docs/release-notes/upcoming.md` — `[Public-API]` **fires**

User-visible, so plain language, no module names: running a `tcw` command that
writes outside a git repository now says so in one line and changes nothing on
disk, instead of printing a Python traceback after half-creating the item, term
or capability. Reading still works outside a repository, exactly as before. In
the local web app, the same refusal appears as an error on the save rather than
a server error. Mention that `tcw work start` was the sharpest case: it used to
move the item and *then* fail.

### `README.md` — `[Public-API]` **does not fire**

No CLI surface change: no new command, flag or argument, and no changed exit
code. `README.md:186` ("It refuses outside a git repo (write transitions need
git)") and `:1076` already state the contract this change enforces; both stay
true and neither becomes more precise by editing. Recorded as evaluated.

### `skills/<component>/SKILL.md` — `[Skill-Driven-Component]` **fires** (one skill)

`skills/tcw-work/SKILL.md` — the guardrail an agent needs is that a write
command outside a repository is a refusal to act on (`git init`, or move to the
right directory), not a crash to retry or work around. One line; `tcw-taxonomy`
and `tcw-capabilities` get the same behavior but no skill-level guidance changes
for them, since neither documents failure modes at this level. Recorded as
evaluated and not changed.

### Also, though not a declared entry

`tests/cli/scenarios/01-bootstrap-and-node-identity.md:41-45` currently reads
"Explicitly not covered here: Behaviour outside a git repository — that is a
known open backlog item (`2026-07-30-fix-non-git-write-paths-…`); scenario 12
records it as a documented gap rather than asserting either way." That exclusion
and its pointer to this item must be deleted and replaced with a pointer to the
new scenario 14 (task 6). Grep for the slug across `tests/cli/` before finishing
— scenario 12 is named in that sentence and may carry its own note.

## Verification

Beyond `pytest`:

- **The shipped binary, by hand.** The tests drive `main()` and the store API in
  process; none of them runs the installed `tcw`. Rebuild the spec's
  Reproduction fixture at the shell (`git init` a node, seed it, commit,
  `rm -rf .git`) and walk scenario 14 with the real binary. The two rows that
  need eyes are `tcw work start` (criterion 3 — the item must still be in
  `backlog/`) and `tcw work new` (criterion 2 — no
  `docs/work/backlog/<slug>/state.yaml` afterwards).
- **The manifest must include directories.** `FsWorkStore.start` creates
  `docs/work/.claiming/` (`fs.py:2116`) before it renames anything. A
  `path → sha256` map over *files* would call that clean. Every manifest in
  tasks 2, 3, 5 and 6 walks directories as well as files. This is the concrete
  form of the spec's "no partial filesystem mutation".
- **Perf, measured not assumed.** The spec dropped memoization and accepted
  ~6.6 ms per `git rev-parse`. Time `tcw work inbox accept` and `tcw work
  reconcile` — the two commands with the most guarded calls — before and after,
  and record both numbers in `outcome.md`. If either regresses by more than a
  few tens of milliseconds, that is a finding for `outcome.md`, not a silent
  acceptance.
- **Not verifiable here, stated instead:** whether any real user runs `tcw`
  writes outside a repository today and relies on the partial write that
  survives. The spec accepts breaking that; nothing in the suite can prove
  nobody does.

## Notes

### What the walk turned up that the spec did not predict

1. **`FsWorkStore.start` is a three-rename dance, not one `os.replace`.** It
   creates `docs/work/.claiming/` (`:2116`), renames into a private uuid-named
   folder (`:2132`), writes state (`:2138`), renames to `active/` (`:2141`) and
   renames back on failure (`:2143`) — on top of the take-over branch the spec
   did describe (`:2072-2076`). The guard placement is unchanged (first
   statement covers all seven), but the **directory** it creates is why every
   manifest in this plan walks directories. The spec's criterion 2 would have
   passed with a stray `.claiming/` on disk.
2. **`inbox_accept` deletes its source outside git when the entry is
   untracked** (`:3055` `self._rm` when tracked, else `shutil.rmtree`/`unlink`
   at `:3057`/`:3059`). All of it is downstream of `_stage(destination)` at
   `:3049`, so the single guard covers it — but it is the one write path in the
   adapter that mutates without any git call at all, and worth knowing exists.
3. **`FsCapabilitiesStore.set` guards twice** once `_write_meta` has its own
   guard. Harmless (two `git rev-parse` calls on one command) and left alone:
   `set` needs its own because it `mkdir`s first, and `_write_meta` needs its
   own for the funnel guarantee. Not worth a flag to suppress.

### Overlap with the three sibling items in this batch

This item implements first, because it owns the generic `CalledProcessError`
boundary that `2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically`
defers to it. Whoever implements second should **re-locate by symbol**, not by
line — every line number in this plan will have moved.

| Symbol this plan guards | Also edited by | Collision shape |
| --- | --- | --- |
| `FsCapabilitiesStore.set` | `…-validate-capability-subject-and-feature-refs-at-write-time` | Both add a first-line statement to `set`; that item also reworks `_validate_fields` above it. Textual conflict, trivial resolution: both statements stay, the guard first. |
| `FsCapabilitiesStore.update_capability` | same item | Same shape. |
| `FsWorkStore.inbox_accept` | `2026-08-19-derive-an-accepted-inbox-item-s-title-…` | That item changes how `accepted_title` is derived, a few lines below this guard. Conflict is adjacent, not overlapping. |
| `FsTreeStore` class body | `…-resolve-taxonomy-refs-against-symlinks-not-just-lexically` | That item adds `_within_store` beside `_stage`/`_rm`/`_mv`; this one adds `_require_repository`/`_write_git_root` in the same place. Both are new methods in one class body — a conflict git resolves badly and a human resolves in seconds. |
| `FsTaxonomyStore.add`, `FsCapabilitiesStore.add` | same item | **No direct collision.** That item guards `add` for containment; this item guards `_write_node`, which `add` calls. Independent lines. |

The symlink item's own leak — every write past a symlink dies at `git add` with
a raw `CalledProcessError` (its spec, Problem §6) — is closed by task 4, whether
or not that item has landed. It does not block this one and this one does not
block it.

### No blockers

Nothing this item depends on is open. It is the head of the batch.
