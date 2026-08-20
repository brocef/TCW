# Plan — A git refusal after the filesystem write still leaves a partial write

**Line numbers derived against `70bda31`** — read from the committed blob
(`git show 70bda31:tcw/store/fs.py`, 3946 lines). Code is addressed by **symbol**
first; every `:NNNN` is a locator, never an identity. The one file that changes
under `tcw/` is `tcw/store/fs.py`.

> **The line numbers here are already drifting, by design.** Planning started at
> `a875de9`; three `containment:` commits then landed on `tcw/store/fs.py`
> mid-plan (`776b76d`, `5d02f69`, `70bda31`, +84 lines), and at the time of
> writing the file is **dirty in the working tree** under another agent. The §1
> census was re-derived from scratch after that drift and the **structure is
> unchanged** — the same seventeen `self._stage(` sites, the same six
> `_atomic_write` callers, the same six `dump_yaml`-then-stage pairs. The
> containment work edits read paths only (`_load_node`, `get_local`,
> `_local_slugs`, `_compose_body`, plus a containment guard at the top of
> `FsTaxonomyStore.add`); it touches no write-then-stage pair.
>
> **Re-derive at the start of every task**, and read a mismatch as drift rather
> than as an error in this plan:
> ```
> grep -n "self\._stage(\|_atomic_write\|dump_yaml(" tcw/store/fs.py
> grep -n "    def <name>" tcw/store/fs.py
> ```
> The census is the invariant; the numbers are not. Tasks 1–5 also each shift the
> locators for the ones after them.

---

## 1. The write-then-stage census

The spec claims *"fifteen `self._stage(...)` calls across fourteen methods"*.
**Verified exact.** `grep -n "self\._stage(" tcw/store/fs.py` returns **seventeen**
call sites; two of them do not stage content the same call just wrote, and the
spec excludes them by name. Fifteen sites in fourteen methods are the
write-then-stage pairs this item converts.

Separately, `git_stage(...)` is called directly — bypassing `_stage` — at three
module/method sites: `ensure_worktree_ignored` (`:493`), and `start`'s two rename
branches (`:2324`, `:2393`). All three are Non-goals; none writes-then-stages a
file it created (the first appends to a `.gitignore` the node wants anyway; the
other two stage a rename).

### The seventeen `self._stage(...)` sites

| # | Symbol (class) | Stage @ | What it writes | Creates a directory it owns? | This task |
| - | -------------- | ------- | -------------- | ---------------------------- | --------- |
| 1 | `FsTreeStore._write_node` (def `:1045`) | `:1082` | `meta.yaml` + `description.md`, via `_atomic_write_all` (`:1058`) | **Yes** — `d.mkdir(parents=True, exist_ok=True)` (`:1056`) | **Convert** — `owned_dir=d` when `_mkdir_owned(d)` returned True, else `None` |
| 2 | `FsTaxonomyStore.extends_add` (def `:1264`) | `:1284` | `docs/taxonomy/config.yaml`, via `dump_yaml` (`:1283`) | No — writes into `docs/taxonomy/`, which `init` made. **Creates the file**: `init` (`:584`) writes only leaf dirs + `.gitkeep` — re-verified in §4e | **Convert** — `owned_dir=None` |
| 3 | `FsTaxonomyStore.extends_remove` (def `:1286`) | `:1298` | same file (`:1297`) | No — the guard raises unless `extends` already exists, so the file does too | **Convert** — `owned_dir=None` |
| 4 | `FsCapabilitiesStore._write_meta` (def `:1823`) | `:1828` | `meta.yaml`, via `_atomic_write` (`:1826`) | Not today (its callers mkdir); **yes after this task** — it takes over the `mkdir` via `_mkdir_owned(d)` | **Convert** — `owned_dir=d` when `_mkdir_owned(d)` returned True, else `None` |
| 5 | `FsCapabilitiesStore.extends_add` (def `:1898`) | `:1916` | `docs/capabilities/config.yaml` (`:1915`) | No; creates the file, same as #2 | **Convert** — `owned_dir=None` |
| 6 | `FsCapabilitiesStore.extends_remove` (def `:1918`) | `:1930` | same file (`:1929`) | No | **Convert** — `owned_dir=None` |
| 7 | `FsCapabilitiesStore.update_capability` (override-clear branch, def `:2151`) | `:2180` | **nothing** — stages the *directory* `d` so git records the `desc.unlink(missing_ok=True)` at `:2178` | n/a | **Leave.** Not a write-then-stage pair; `_write_staged` does not model staging a directory for a removal |
| 8 | `FsWorkStore.write_plan_stage` (def `:2660`) | `:2672` | `<item>/plan/<stage-id>.md`, via `_atomic_write` (`:2671`) | **Yes** — `path.parent.mkdir(parents=True, exist_ok=True)` (`:2670`) creates `plan/` | **Convert** — `owned_dir=path.parent` when `_mkdir_owned(path.parent)` returned True, else `None` |
| 9 | `FsWorkStore._write_tags` (def `:2989`) | `:3002` | the node sentinel `tcw-config.yaml` (`:3001`) | No — `_config_path()` is `node_root / SENTINEL` (`:2870`), always present on a real node | **Convert** — `owned_dir=None` |
| 10 | `FsWorkStore.inbox_accept` (def `:3251`) | `:3318` | **nothing new** — stages `destination`, a folder built in a temp dir (`:3311-3312`) and `os.replace`d into place; already rolls back below the stage | n/a | **Leave** |
| 11 | `FsWorkStore._set_fields_at` (def `:3360`) | `:3373` | `<item>/state.yaml` (`:3372`) | No — the item dir and its `state.yaml` both pre-exist | **Convert** — `owned_dir=None` |
| 12 | `FsWorkStore.create_work` (def `:3530`) | `:3642` | `state.yaml` + optional `initial-request.md` + optional `intake.md`, via the `_atomic_write` loop (`:3637-3638`) | **Yes** — bare `d.mkdir(parents=True)` (`:3635`), no `exist_ok` | **Convert** — `owned_dir=d`, **unconditional** |
| 13 | `FsWorkStore.update_work` (state, def `:3646`) | `:3776` | `state.yaml`, via `_atomic_write_all(writes)` (`:3774`) | No — `_require_dir(slug)` (`:2461`) resolved an existing folder | **Convert** — merged with #14 into one call, `owned_dir=None` |
| 14 | `FsWorkStore.update_work` (body) | `:3778` | `initial-request.md` — **may be created** when the item had no body | No | merged into #13 |
| 15 | `FsWorkStore.write_artifact` (def `:3813`) | `:3839` | `<name>.md` — may be created (`:3838`) | No | **Convert** — `owned_dir=None` |
| 16 | `FsWorkStore.write_draft` (def `:3848`) | `:3865` | `<artifact>.draft.md` — always created, or `--force`-replaced (`:3864`) | No | **Convert** — `owned_dir=None` |
| 17 | `FsWorkStore.write_sidecar` (def `:3897`) | `:3939` | `capabilities.yaml` or `rollup.md` — may be created (`:3938`) | No | **Convert** — `owned_dir=None` |

**Totals.** 17 sites → 15 converted across 14 methods (`update_work` holds two),
2 left as-is (#7, #10). After Task 5 the file contains exactly three
`self._stage(` calls: one inside `_write_staged`, plus #7 and #10.

### 2. `owned_dir` per converted site — why, exactly

`owned_dir` is the one parameter that can take a sibling file with it, so each
site is stated on its own rather than by rule.

**Passes an `owned_dir` (three sites, all conditional on an ownership proof):**

- **#1 `_write_node`** — `owned = _mkdir_owned(d)`; pass `d` only when `owned`.
  Reached from `FsTaxonomyStore.add` (def `:1223`, `d` is brand new — `add`
  refuses on `if d.exists()`) and `FsCapabilitiesStore.add` (def `:1770`, same
  guard), where `owned` is True and the whole node folder goes;
  and from `update_term` / `update_capability` on an existing node, where `owned`
  is False and only files this call created are unlinked. Passing `d`
  unconditionally here would `rmtree` a term folder on a failed *update*,
  destroying attachments the call never touched.
- **#4 `_write_meta`** — same shape. `owned` is True on the `set`-materializes-a-
  fresh-override path (Task 3 hands the `mkdir` to `_write_meta`); False when
  `update_capability` already made the directory a few lines earlier, which is
  what keeps the two guards from double-deleting.
- **#8 `write_plan_stage`** — `owned = _mkdir_owned(path.parent)`. True the first
  time a plan stage is written for an item (`plan/` did not exist), False
  afterwards. Unconditional would delete every previously written plan stage on a
  refused write of the second one.

**#12 `create_work` is the one unconditional `owned_dir=d`** — and only because
its `d.mkdir(parents=True)` has **no** `exist_ok`, so reaching the next line is
itself the proof. A slug collision must still raise `FileExistsError` (that is
how `_unique_slug` failures surface), which is why this site keeps its bare
`mkdir` instead of adopting `_mkdir_owned`.

**Passes `owned_dir=None` (the remaining eleven sites: #2, #3, #5, #6, #9, #11,
#13/#14, #15, #16, #17)** — every one writes into a directory that existed before
the call:

- #2/#3/#5/#6 write `config.yaml` into `docs/taxonomy/` or `docs/capabilities/`,
  scaffolded by `init`. The *file* is created by #2/#5 and is undone per file;
  the component root is shared with every term/capability folder and must never
  be `rmtree`d.
- #9 writes the node sentinel, which sits beside `.git` at the node root.
  `owned_dir` there would delete the repository's working tree.
- #11, #13/#14, #15, #16, #17 all write inside `<status>/<slug>/`, resolved by
  `_require_dir(slug)` (`:2461`), which raises if it is absent. The folder
  holds `state.yaml` and every other artifact; per-file undo is the only safe
  mode. This is exactly criterion 4.

### 3. Sites deliberately **not** converted

| Site | Why it stays |
| ---- | ------------ |
| `update_capability` `:2180` | Stages a directory to record a *removal* (`desc.unlink` at `:2178`). Nothing was written to undo. Its outer directory guard is reworked in Task 3 but this `_stage` call is untouched. |
| `inbox_accept` `:3318` | Whole-directory swap, already rolled back in its own `except`. Its writes go to a temp dir (`:3311-3312`), so no `(path, content)` pair it stages was written where it now sits. |
| `ensure_worktree_ignored` `:493` | Non-goal. Module-level `git_stage`, and the leftover is one `.gitignore` line the node wants. |
| `start` `:2324`, `:2393` | Non-goal — a rename, not a creation. Pinned by criterion 9. |
| `_inbox_write` (`tcw/work/recursion.py:281`) | Non-goal — never stages. Confirmed still the only write outside `tcw/store/fs.py`: `grep -rn "write_text\|_atomic_write\|dump_yaml" --include=*.py tcw/ \| grep -v store/fs.py` returns that one line. |

---

## 4. Empirical verification of the spec's claims

Run at `a875de9` in a **throwaway** repository under `/tmp` (`/tmp/pw-verify-70843`
and `/tmp/pw-verify2-76486`, both since deleted), never in this checkout. The
three `containment:` commits that landed afterwards do not touch any path
exercised below — they edit read paths only — so every result stands at
`70bda31`. Fixture: `git init`, then
`tcw init --id pwtest work taxonomy capabilities`, then `git add -A && git commit`.
Everything below is raw output.

> **Fixture correction, worth carrying into the tests:** `tcw init --id t` is
> **rejected** — `tcw init: project ID is reserved: t`. The spec's fixture line
> (`tcw init --id t work taxonomy capabilities`) does not run as written. Use a
> non-reserved id.

### 4a. A held `index.lock` really does make `git add` fail

```
$ touch .git/index.lock
$ git add -- probe.txt
fatal: Unable to create '/tmp/pw-verify-70843/.git/index.lock': File exists.
...
git add exit=128
rev-parse exit=0
check-ignore(backlog/x)  exit=1     # answers "not ignored"
check-ignore(completed/x) exit=0    # answers "ignored"
```

Confirmed: `git add` → **128**; `git rev-parse --show-toplevel` → 0, so
`require_repository` (`:318-329`) passes; `git check-ignore -q` **answers
normally** rather than erroring, so `git_ignored` (`:331-344`) and the `live`
filter in `git_stage` (`:305`) behave as on an unlocked repository.

> **Precision note on the spec.** The spec says `git check-ignore -q` "exits 0"
> under the lock. That is true only for a path the rules *do* hide
> (`docs/work/completed/x` → 0); a path they do not hide answers 1
> (`docs/work/backlog/x` → 1), which is `check-ignore`'s normal "not ignored".
> The claim the fixture actually rests on — *`check-ignore` answers instead of
> failing* — holds in both directions. No change to the design follows.

### 4b. The failure surfaces as one `tcw:` line, not a traceback

```
$ tcw work new "Repro item"
exit=1
--- stderr ---
fatal: Unable to create '/tmp/pw-verify-70843/.git/index.lock': File exists.
   (…6 more lines of git's own advice…)
tcw: git command failed (exit 128): git -C /private/tmp/pw-verify-70843 add -- \
  /private/tmp/pw-verify-70843/docs/work/backlog/2026-08-20-repro-item/state.yaml
--- stderr lines starting with "tcw: " --- 1
--- lines containing Traceback --- 0
```

Eight lines reach the terminal; **exactly one** comes from `tcw`, the other seven
are git's own diagnostic written straight to fd 2 by the subprocess. This is what
criterion 8 must assert against — count lines matching `^tcw: `, not total stderr
lines.

### 4c. The defect: `tcw work new` under a held lock leaves the folder

```
--- git status --porcelain ---
?? docs/work/backlog/2026-08-20-repro-item/
--- find docs/work/backlog -mindepth 1 ---
docs/work/backlog/.gitkeep
docs/work/backlog/2026-08-20-baseline-item
docs/work/backlog/2026-08-20-baseline-item/state.yaml
docs/work/backlog/2026-08-20-repro-item          <-- leftover
docs/work/backlog/2026-08-20-repro-item/state.yaml
--- *.tmp --- (none)
```

The other two end-to-end criteria reproduce identically:

```
$ tcw work scaffold spec 2026-08-20-baseline-item     exit=1
tcw: git command failed (exit 128): git … add -- …/2026-08-20-baseline-item/spec.draft.md
$ ls docs/work/backlog/2026-08-20-baseline-item/
spec.draft.md
state.yaml                                            <-- spec.draft.md survives

$ tcw taxonomy add Widget --slug widget               exit=1
tcw: git command failed (exit 128): git … add -- …/docs/taxonomy/widget/meta.yaml …/description.md
$ ls docs/taxonomy/widget
description.md
meta.yaml                                             <-- both survive

$ tcw capabilities add a/b Thing                      exit=1
$ find docs/capabilities/a
docs/capabilities/a
docs/capabilities/a/b
docs/capabilities/a/b/description.md
docs/capabilities/a/b/meta.yaml                       <-- both survive
```

**A finding the spec does not state.** `capabilities add a/b` creates the
intermediate `docs/capabilities/a/` as well (via `parents=True`). Rolling back
`d = …/a/b` leaves an **empty `a/`** behind — the same disposition `create_work`
already documents for an intermediate `backlog/` (`:3546-3550`). It is inert: git
does not track an empty directory (`git status --porcelain` is empty), and
`_all_meta_dirs` (`:1507-1518`) only recognises a folder holding `meta.yaml`.
**Criterion 3's test must assert `docs/capabilities/a/b` is gone and
`git status --porcelain` is empty — not that `docs/capabilities/a` is gone.**

### 4d. The three pinned non-goals behave today exactly as the spec says

`tcw work start` under the lock — item **moved**, fields **stamped**, nothing
rolled back:

```
exit=1
tcw: git command failed (exit 128): git … add -- …/docs/work/backlog/2026-08-20-baseline-item \
                                                …/docs/work/active/2026-08-20-baseline-item
Traceback count: 0
--- where is the item? ---  docs/work/active/2026-08-20-baseline-item
--- state.yaml ---
slug: 2026-08-20-baseline-item
title: Baseline item
created: '2026-08-20'
resolution: null
owner: t@t
started: '2026-08-20T22:16:22.769076Z'
--- git status --porcelain ---
 D docs/work/backlog/2026-08-20-baseline-item/state.yaml
?? docs/work/active/2026-08-20-baseline-item/
```

`tcw work edit --title` under the lock — new title **on disk**, failure reported:

```
exit=1
tcw: git command failed (exit 128): git … add -- …/2026-08-20-second-item/state.yaml
--- state.yaml ---
slug: 2026-08-20-second-item
title: Renamed Title            <-- the new title survives
created: '2026-08-20'
resolution: null
--- git status --porcelain ---
 M docs/work/backlog/2026-08-20-second-item/state.yaml
```

Both are true **today**, so criteria 5 and 9 are honest pins of current behavior
rather than new promises.

### 4e. The sibling sweep claim

```
$ ls -1 docs/taxonomy/          # after `tcw init … taxonomy`, before any extends
(empty — only the dot-file .gitkeep)
```

Confirmed: `docs/taxonomy/config.yaml` does **not** exist after `init`, so
`extends_add` (#2/#5) creates it. In scope, as the spec says.

---

## 5. Tasks

Ordered so `python -m pytest -q` is green at every commit boundary. Each task
names the exact files it touches and what proves it.

### Task 1 — Land the chokepoint, with no callers

**Modifies:** `tcw/store/fs.py`, `tests/test_store_editor.py`.
**Commit:** `store: add the write-then-stage chokepoint`

1. Add `from contextlib import suppress` to the import block at the top of
   `tcw/store/fs.py`. It is the only new import; `shutil` is already there.
2. Add module-level `_mkdir_owned(d: Path) -> bool` immediately after
   `_atomic_write_all` (def `:878`, ends `:903`), with the docstring from the
   spec's Design section: `d.mkdir(parents=True)` inside `try`, `return True`;
   `except FileExistsError: return False`.
3. Add `FsTreeStore._write_staged(self, pairs, *, owned_dir=None)` immediately
   after `_stage` (`:994-996`), verbatim from the spec's Design section —
   `new = [p for p, _ in pairs if not p.exists()]` computed **before** the write,
   one `try` spanning `_atomic_write_all(pairs)` and `self._stage(...)`,
   `except BaseException` → `shutil.rmtree(owned_dir, ignore_errors=True)` when
   `owned_dir` is not None, else `for p in new: with suppress(OSError): p.unlink()`,
   then bare `raise`.

**Proves it** — new tests in `tests/test_store_editor.py`, beside the
`_atomic_write_all` block (`:1011-1071` in that file, which the containment work
did not touch), driving a bare `FsTreeStore` on a
`_work_node(tmp_path)` repository with `tcw.store.fs.git_stage` monkeypatched:

- `_mkdir_owned` returns True on a fresh path (and creates parents), False on an
  existing one, and raises nothing on a race-shaped second call.
- Staging failure with `owned_dir` set removes the whole directory.
- Staging failure with `owned_dir=None` removes only the files absent at entry,
  leaving a pre-existing sibling byte-identical.
- Staging failure re-raises the **staging** exception, and
  `list(root.rglob("*.tmp")) == []`.
- `Path.unlink` monkeypatched to `PermissionError` → the original
  `CalledProcessError` still propagates (criterion 11's unit half).

Nothing calls `_write_staged` yet, so the rest of the suite is untouched.

### Task 2 — Convert the eleven file-only sites

**Modifies:** `tcw/store/fs.py`, `tests/test_store_editor.py`.
**Commit:** `store: route the file-only writes through _write_staged`

Census rows **#2, #3, #5, #6, #9, #11, #13/#14, #15, #16, #17** — every one passes
`owned_dir=None` (reasons in §2).

- The six `dump_yaml(p, x)` + `self._stage(p)` pairs (`FsTaxonomyStore.extends_add`
  / `extends_remove`, `FsCapabilitiesStore.extends_add` / `extends_remove`,
  `_write_tags`, `_set_fields_at`) become
  `self._write_staged([(p, yaml.safe_dump(x, sort_keys=False, allow_unicode=True))])`.
  Byte-identical to `dump_yaml` (`:767-768`), now promoted through a temp file.
- `update_work`: `_atomic_write_all(writes)` + the two `self._stage(...)` calls
  (`:3774-3778`) collapse to `self._write_staged(writes)`. `writes` already holds
  exactly the paths the two stage calls covered, so the staged set is unchanged.
- `write_artifact`, `write_draft`, `write_sidecar`: `_atomic_write(p, content)` +
  `self._stage(p)` → `self._write_staged([(p, content)])`.

**Proves it:**

- New `tests/test_store_editor.py::test_a_refused_stage_removes_only_the_artifact_it_created`
  — criterion 4: a committed item with `state.yaml` + `initial-request.md`,
  `git_stage` raising `CalledProcessError(128, …)`, `write_artifact(slug, "spec",
  "x")` → item folder present, both pre-existing files byte-identical, no
  `spec.md`, no `*.tmp`.
- New `…::test_a_refused_stage_keeps_an_overwritten_state_yaml` — criterion 5's
  work half at the store level: `update_work(slug, title="Renamed")` under a
  refused stage leaves `state.yaml` present and reading `title: Renamed`.
- New `…::test_a_refused_undo_does_not_mask_the_staging_error` — criterion 11:
  `Path.unlink` → `PermissionError`, `git_stage` → `CalledProcessError(128, …)`,
  `write_artifact` raises the **`CalledProcessError`**; plus
  `main(["work", "scaffold", "spec", slug])` returns non-zero and prints the
  criterion-8 line.
- Regression watch: `test_update_work_body_failure_leaves_state_and_body_unchanged`
  (`tests/test_store_editor.py:1181`) is a *content* failure and must pass
  unmodified.

### Task 3 — Convert the folder-node writes and rework the two capability guards

**Modifies:** `tcw/store/fs.py`, `tests/test_store_editor.py`.
**Commit:** `store: roll back a node folder this call created`

Census rows **#1** and **#4**, plus their two callers. These four edits **must
land in one commit**: converting `_write_node` alone makes its per-file undo
remove `meta.yaml`, which flips `update_capability`'s existing
`not existed and not (d / "meta.yaml").exists()` guard (`:2198`) from "keep" to
"delete" and turns `test_update_capability_keeps_override_when_staging_fails`
red at that boundary.

1. **`_write_node` (`:1045-1082`).** Replace `existed = d.exists()` (`:1055`) +
   `d.mkdir(parents=True, exist_ok=True)` (`:1056`) with `owned = _mkdir_owned(d)`;
   replace the `try` / `except BaseException` / trailing `self._stage(...)` with a
   single `self._write_staged([...], owned_dir=d if owned else None)`. Delete the
   `ponytail:` TOCTOU note (`:1068-1075`) — `_mkdir_owned` is the ownership
   signal it asked for — and the "Staging stays outside the rollback" note
   (`:1079-1081`), whose policy this item reverses. Keep `self._require_repository()`
   ahead of the mkdir (`:1054`) and rewrite the "**Callers wrapping this in a
   rollback**" docstring paragraph (`:1048-1052`), which now describes the old
   contract.
2. **`_write_meta` (`:1823-1828`).** `owned = _mkdir_owned(d)`, then
   `self._write_staged([(d / "meta.yaml", yaml.safe_dump(meta, sort_keys=False,
   allow_unicode=True))], owned_dir=d if owned else None)`.
3. **`set` (`:1877-1894`).** Delete `existed` (`:1881`), the `d.mkdir(...)`
   (`:1882`) and the whole `try`/`except` (`:1883-1893`) — `_write_meta` owns the
   directory now. The body becomes validate → `_write_target` →
   `self._write_meta(d, self._merge_meta(...))` → `return self.get(identifier)`.
4. **`update_capability` (`:2169-2200`).** `owned = _mkdir_owned(d)` replaces
   `existed = d.exists()` (`:2169`) + `d.mkdir(...)` (`:2170`); the guard
   (`:2198-2199`) becomes `if owned: shutil.rmtree(d, ignore_errors=True)`. The
   `try` stays, because the `self._stage(d)` at `:2180` (census #7) is still
   outside `_write_staged`.
   Rewrite the two comment blocks (`:2186-2197`) to state the new composition:
   the inner `_write_node` / `_write_meta` see the directory already there, pass
   `owned_dir=None`, and undo per file; the outer `rmtree` would have taken those
   files anyway, so the two guards cannot double-delete.

**Proves it:**

- **Rewrite, do not delete,** `tests/test_store_editor.py:1127`
  `test_update_capability_keeps_override_when_staging_fails` and `:1164`
  `test_set_keeps_override_when_staging_fails` (criterion 6). Both now assert the
  freshly materialized override folder is **gone**; each docstring records that
  this item deliberately reverses what its predecessor pinned, and names this
  work item. Consider renaming to `…_removes_override_when_staging_fails` and
  keeping the old name in the docstring so `git log -S` finds the reversal.
- Unmodified and must stay green: `:1105`
  `test_update_capability_failure_removes_override_it_materialized`, `:1147`
  `test_set_failure_removes_override_it_materialized`, `:1074`
  `test_write_node_failure_leaves_existing_node_untouched`, `:1092`
  `test_write_node_failure_removes_directory_it_created`. All four are *content*
  failures; traced by hand against the new code, each reaches the same end state.
- New end-to-end test (criterion 3), in `tests/test_non_git_writes.py` beside
  `test_a_git_subprocess_failure_is_a_message_not_a_traceback` (`:304`), using the
  real `index.lock` fixture of §6: `tcw taxonomy add Widget --slug widget` exits 1,
  `docs/taxonomy/widget` does not exist, `git status --porcelain` is empty; then
  `tcw capabilities add a/b Thing` exits 1, `docs/capabilities/a/b` does not
  exist, `git status --porcelain` is empty (**not** asserting `docs/capabilities/a`
  is gone — see §4c).

### Task 4 — Convert the two work-store directory owners

**Modifies:** `tcw/store/fs.py`, `tests/test_non_git_writes.py`.
**Commit:** `store: roll back a work item folder this call created`

Census rows **#12** and **#8**.

1. **`create_work` (`:3635-3642`).** Keep `d.mkdir(parents=True)` (`:3635`)
   exactly as it is — no `exist_ok`, so a slug collision still raises. Delete the
   `try` / `except BaseException: shutil.rmtree(...)` / `raise` (`:3636-3641`)
   and the trailing `self._stage(...)` (`:3642`); replace with
   `self._write_staged([(d / name, content) for name, content in written.items()],
   owned_dir=d)`. Rewrite the comment block (`:3627-3634`) — keep its
   intermediate-`backlog/` paragraph, drop "Staging stays outside".
2. **`write_plan_stage` (`:2660-2673`).** `owned = _mkdir_owned(path.parent)`
   replaces `path.parent.mkdir(parents=True, exist_ok=True)` (`:2670`); then
   `self._write_staged([(path, content)], owned_dir=path.parent if owned else None)`.

**Proves it** — two end-to-end tests using the real `index.lock` fixture (§6),
in `tests/test_non_git_writes.py`:

- Criterion 1: `main(["work", "new", "T"])` returns 1; afterwards
  `git status --porcelain` is empty and `find docs/work/backlog -mindepth 1`
  yields only `docs/work/backlog/.gitkeep`.
- Criterion 2: on a committed backlog item, `main(["work", "scaffold", "spec",
  slug])` returns 1, `git status --porcelain` is empty, `<slug>/spec.draft.md`
  does not exist.
- Both assert `list(root.rglob("*.tmp")) == []` (criterion 7) and the criterion-8
  stderr shape: exactly one line matching `^tcw: git command failed \(exit \d+\): git `,
  and no `Traceback`.
- Criterion 9, the **pin** that the rollback did not spread into transitions:
  a third test in the same file — under the same real lock, `main(["work",
  "start", slug])` returns 1, the item is at `docs/work/active/<slug>/`, and its
  `state.yaml` carries both `owner` and `started`. Exactly the behavior measured
  in §4d; it must not change. It belongs here because Task 4 is the commit that
  could plausibly break it (`_set_fields_at` after the move).
- Unmodified and must stay green: `tests/test_store_editor.py:1201`
  `test_create_work_failure_leaves_no_directory` (content failure), and
  `tests/test_external_work_store.py:838`
  `test_a_refused_stage_after_the_move_is_a_transition_commit_error`.

### Task 5 — Retire `_atomic_write`

**Modifies:** `tcw/store/fs.py`, `tests/test_store_editor.py`.
**Commit:** `store: retire _atomic_write, now unused`

After Tasks 2–4 all six production callers (`:1826`, `:2671`, `:3638`, `:3838`,
`:3864`, `:3938`) are gone. Verified by grep before deleting.

1. Delete `_atomic_write` (`:863-875`).
2. `tests/test_store_editor.py`: drop `_atomic_write` from the import at `:21-25`,
   and repoint its three direct tests — `:946`
   `test_atomic_write_preserves_prior_on_failure`, `:967`
   `test_atomic_write_temp_cleanup_on_failure`, `:987`
   `test_atomic_write_success_stages_file` — at `_atomic_write_all([(p, content)])`.
   All three assert behavior the plural has (`:900-903` is the same handler),
   and `test_atomic_write_all_single_pair` (`tests/test_store_editor.py:1018`)
   already proves the singular call shape works. Rename them
   `test_atomic_write_all_…` for consistency.
3. Correct the stale cross-reference in `_atomic_write_all`'s `ponytail:` note
   (`:889`): it cites "the `accept_inbox` shape, fs.py:2246", but `inbox_accept`
   is at `:3251` and its whole-directory swap at `:3318`. Leave the note itself —
   it names a crash-atomicity ceiling this item does not touch.

**Proves it:** the three repointed tests, plus the structural sweep in §8 run by
hand (criterion 10).

### Task 6 — Documentation Sync, capability wording, and the sidecar

**Modifies:** `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`,
seven `docs/capabilities/**/description.md` files, and this item's
`capabilities.yaml` sidecar.
**Commit:** `docs: record the rollback of a refused stage`

Scheduled as one block at the end, per the stage instructions. Details in §8.

---

## 6. How a test simulates a git refusal

**Two mechanisms, and the choice per test is not free.**

**(a) `monkeypatch.setattr("tcw.store.fs.git_stage", boom)`** — for store-level
tests (criteria 4, 5, 6, 11 and Task 1's unit tests). The suite already does this
in five places (`tests/test_non_git_writes.py:325`, `:864`,
`tests/test_store_editor.py:1138`, `:1174`, `tests/test_external_work_store.py:852`).
Patch `git_stage`, **not** `_git` — patching `_git` also breaks `git_root`, so
`require_repository` answers first and the test never reaches staging
(`tests/test_non_git_writes.py:321-324` says exactly this). Raise
`subprocess.CalledProcessError(128, ["git", "add", "x"])` so the CLI renders the
criterion-8 line.

**(b) A real held `.git/index.lock`** — for the end-to-end criteria 1, 2, 3, 9,
because only the real lock proves the whole command path. **Confirmed to work
from inside pytest**: the mechanism is a plain `touch`, nothing about it is
interactive, and §4 ran it against the installed CLI. `git add` returns 128; the
repository-existence probes still answer, which matters because
`_require_repository` now runs **before** every write — a fake or absent repo
would make the command fail at the guard, with nothing written, and the test
would pass for the wrong reason.

**Fixture shape** — put it in `tests/test_non_git_writes.py`, which already has
`repo()` (`:46-52`) building a committed node with all three components:

```python
@contextlib.contextmanager
def refusing(root: Path):
    """A repository that exists and refuses: `git add` fails, every read-only
    probe answers. Held for the duration of the command under test.

    A real lock rather than a patched `git_stage`, because these criteria are
    about what the whole command leaves on disk. The repository must be real and
    initialized — `_require_repository` runs ahead of every write now, so an
    absent `.git` fails at the guard and the test would pass without ever
    reaching staging.
    """
    lock = root / ".git" / "index.lock"
    lock.touch()
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)
```

Used as:

```python
def test_a_refused_stage_leaves_no_work_item(tmp_path, monkeypatch, capsys):
    root = repo(tmp_path)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
    monkeypatch.chdir(root)
    with refusing(root):
        assert main(["work", "new", "T"]) == 1
    err = capsys.readouterr().err
    assert [ln for ln in err.splitlines() if ln.startswith("tcw: ")] == [...]
    assert "Traceback" not in err
    assert porcelain(root) == ""
    assert list((root / "docs/work/backlog").iterdir()) == [
        root / "docs/work/backlog/.gitkeep"]
    assert list(root.rglob("*.tmp")) == []
```

Three things the fixture's users must get right:

1. **Commit the baseline first.** `git status --porcelain` can only be asserted
   empty if everything `repo()` scaffolded is already committed. `repo()` does
   commit (`:50-51`); an item created for criterion 2 must be committed too.
2. **Count `tcw: ` lines, not stderr lines.** Under a real lock git writes seven
   lines of its own advice to fd 2 (§4b). `capsys` captures them only when git
   inherits the captured fd; either way the assertion must filter on the `tcw: `
   prefix.
3. **Release the lock before the assertions** that shell out to git
   (`git status --porcelain`) — hence the `finally` in the contextmanager.

---

## 7. Criterion → task

| # | Acceptance criterion | Task(s) | Evidence |
| - | -------------------- | ------- | -------- |
| 1 | `tcw work new "T"` leaves nothing | **4** | new e2e test, real lock; `porcelain == ""`, backlog holds only `.gitkeep` |
| 2 | `tcw work scaffold spec` leaves nothing | **4** | new e2e test, real lock (`write_draft` converted in Task 2, its dir owner in Task 4 — the test lands with Task 4 so both halves are in place) |
| 3 | `tcw taxonomy add` / `capabilities add` leave nothing | **3** | new e2e test, real lock; asserts `.../a/b` gone + `porcelain == ""` (§4c) |
| 4 | A file in an existing folder takes only the file | **2** | `test_a_refused_stage_removes_only_the_artifact_it_created` |
| 5 | An update is never undone (the hard boundary) | **2** (work half), **3** (capabilities half) | `…keeps_an_overwritten_state_yaml`; `set` on an existing capability folder keeps its `meta.yaml` |
| 6 | The two reversed-policy tests are rewritten, not deleted | **3** | `tests/test_store_editor.py:1127`, `:1164` rewritten with docstrings naming this item |
| 7 | No `.tmp` survives | **1, 2, 3, 4** | `assert list(root.rglob("*.tmp")) == []` in every new test |
| 8 | The message is unchanged | **4** (assertion), **all** (must not regress) | `tests/test_non_git_writes.py:304`, `:847` pass **unmodified**; new tests assert one `^tcw: git command failed` line and no `Traceback` |
| 9 | A move is still not rolled back | **4** (pin only — no code change) | `tests/test_external_work_store.py:838` passes unmodified; new `tcw work start` e2e pin under the real lock (behavior measured in §4d) |
| 10 | One chokepoint, checkable structurally | **5** | the three greps in §8 **Verification**, run by hand — deliberately not a test (see §9) |
| 11 | The undo cannot mask the original error | **1** (unit), **2** (store + CLI) | `Path.unlink` → `PermissionError`, `git_stage` → `CalledProcessError`; the latter is what propagates |
| 12 | Nothing added to the abstract interface | **1–5** | `git diff --stat` under `tcw/` names only `tcw/store/fs.py`; `grep -rn "_write_staged\|_mkdir_owned" tcw/` returns only `tcw/store/fs.py` |
| 13 | `pytest` from the repository root is green | **every task** | full run at each commit boundary, outside any sandbox that restricts `git` |

Every task traces back: Task 1 → 7, 11; Task 2 → 4, 5, 7, 11; Task 3 → 3, 5, 6, 7;
Task 4 → 1, 2, 7, 8, 9; Task 5 → 10; Task 6 → the documentation entries below.
Criteria 12 and 13 are properties of the whole diff.

---

## 8. Documentation Sync

Read from `tcw-config.yaml` under `work.documentation` (via `tcw work docs`) —
**not** from `CLAUDE.md`. All four entries evaluated.

| Entry | Trigger | Fires? | Reason |
| ----- | ------- | ------ | ------ |
| `README.md` | **[Public-API]** | **No** | No command, flag, argument, exit code or output line changes. Every command that could hit this failure already exits 1 with the same single stderr line (criterion 8 pins that byte-for-byte). What changes is what is *left on disk* after a failure the README does not describe. Re-check at implement time if any CLI surface moved. |
| `docs/release-notes/upcoming.md` | **[Public-API]** | **Yes** | User-visible behavior change: a command that fails because git refused now cleans up after itself instead of leaving a half-created item. Two short paragraphs, plain language: (a) what now gets removed — only what that command created; (b) **the honest caveat the spec's Risks section asks for** — a failed `tcw work edit --title` still leaves the new title on disk, and a failed `tcw work start` still leaves the item moved. Say it as a deliberate boundary, not an oversight. No module names, no `_write_staged`. |
| `docs/changelogs/upcoming.md` | **[Any-Code-Change]** | **Yes** | Grouped entries: **Fixed** — a refused `git add` no longer leaves a partially created term / capability / work item / draft / plan stage behind; **Internal** — `FsTreeStore._write_staged` is the single write-then-stage chokepoint (15 sites converted), `_mkdir_owned` replaces the `existed = d.exists()` TOCTOU pattern at three sites, `_atomic_write` removed (all callers route through `_atomic_write_all`); **Changed** — `capabilities set` / `update_capability` now remove an override folder they materialized when staging is refused, reversing the prior policy. |
| `skills/<component>/SKILL.md` | **[Skill-Driven-Component]** | **No** | Nothing in the CLI surface, the item model, the lifecycle, or a guardrail changes. `skills/work/SKILL.md`, `skills/taxonomy/SKILL.md` and `skills/capabilities/SKILL.md` teach agents which commands to run and in what order; none of them documents what a git-refused write leaves behind, and no new verb, flag or field appears. Re-confirm with `grep -rn "index.lock\|git command failed\|partial" skills/` at implement time — if a skill *does* tell an agent to clean up by hand after a failed write, that instruction is now wrong and the entry fires. |

**Also in Task 6, outside the four entries:**

- **Capability wording**, seven entries. All seven confirmed present in
  `tcw capabilities list` at this sha: `taxonomy/add-a-term`,
  `capabilities/add-a-capability`, `capabilities/override-inherited`,
  `capabilities/set-a-capabilitys-status`, `work/open-a-work-item`,
  `work/customize-lifecycle-artifact-templates`, `web/editing`. The four
  "Not changed" entries also exist and stay untouched: `work/retitle-a-work-item`,
  `work/tag-a-work-item`, `work/start-a-work-item`, `work/manage-the-work-inbox`.
  The concrete edit for the first two is broadening the existing sentence at
  `docs/capabilities/taxonomy/add-a-term/description.md:3` — *"A refused add exits
  non-zero and writes nothing — including outside a Git repository, where the
  command refuses before it creates the term folder rather than leaving one
  behind"* — so it covers a repository that exists and refuses. No status flips.
- **The sidecar.** Write `capabilities.yaml` in this item's folder — the
  `changed:` list of the seven capability paths with a short trailing comment
  each, in the shape used by
  `docs/work/completed/2026-08-19-derive-an-accepted-inbox-item-s-title-…/capabilities.yaml`.
- **`tcw validate`** and **`tcw capabilities check`** must pass after the wording
  edits.

---

## 9. Verification

Things the suite cannot check, to be run by hand and recorded in `outcome.md`:

1. **Criterion 10, the structural sweep.** After Task 5:
   ```
   grep -n "self\._stage(" tcw/store/fs.py     # expect 3: _write_staged, update_capability, inbox_accept
   grep -n "_atomic_write" tcw/store/fs.py     # expect 2: def _atomic_write_all, its call in _write_staged
   grep -n "dump_yaml(" tcw/store/fs.py        # expect 6: the def + write_sentinel, init, start ×2, inbox_accept
   ```
   and confirm no surviving `dump_yaml(` call is followed by a `self._stage(...)`
   of the same path. **Deliberately not a test**: this repo argues against
   source-text assertions in `tests/test_non_git_writes.py:305-312` — *"an
   assertion about the handler's source text would pass or fail for reasons that
   have nothing to do with coupling."* The behavioral criteria (1–4) are the real
   coverage; this grep is the sweep that catches a missed site.
2. **Criterion 12.** `git diff --name-only main -- tcw/` returns only
   `tcw/store/fs.py`; `git diff main -- tcw/store/base.py` is empty;
   `grep -rn "_write_staged\|_mkdir_owned" tcw/ tests/ --include=*.py` finds them
   only in `tcw/store/fs.py` and `tests/test_store_editor.py`.
3. **The end-to-end fix, by hand, in a throwaway `/tmp` repo** — repeat every
   command in §4c under a held `index.lock` and confirm each now leaves
   `git status --porcelain` empty. The automated criteria cover the same ground;
   this is the one that would catch a CLI-layer difference the store tests miss.
4. **Criterion 13.** `python -m pytest -q` from the repository root, outside any
   sandbox that restricts `git` — the suite creates throwaway repositories, and a
   git-blocked sandbox fails it for the wrong reason. Run at **every** commit
   boundary, not only at the end; the ordering in §5 exists precisely to make
   that possible.

   **Baseline measured at `a875de9`: `1859 passed in 434.24s (0:07:14)`, 0
   failed.** The final count must be `1859 + (tests added)`, with nothing
   deleted — criterion 6 is a rewrite of two tests, not a removal. Budget for
   the runtime: six commit boundaries × ~7 min. Between boundaries, iterate with
   the three files this work actually touches
   (`python -m pytest -q tests/test_store_editor.py tests/test_non_git_writes.py
   tests/test_external_work_store.py`) and spend the full run on the boundary
   itself.
5. **Re-run the spec's test search before editing** (its own Assumptions section
   asks for this, since a sibling item may have landed a new one):
   `grep -rn "staging fails\|when_staging\|git_stage" tests/`. At `a875de9` it
   returns `tests/test_store_editor.py:1127,1138,1164,1174` (the two to rewrite),
   `tests/test_non_git_writes.py:5,190,321,325,602,864`,
   `tests/test_work_autocommit.py:315`, `tests/test_external_work_store.py:852`
   and `tests/cli/scenarios/14-non-git-writes.md:49` — none of which asserts a
   created path *survives* a refused stage except the two named. Checked
   individually: `test_work_autocommit.py:311-333` describes the old half-item
   behavior in prose and asserts the **repository guard**, not a leftover;
   `test_non_git_writes.py:189-206` asserts `.claiming/` is never created outside
   a repo. Both pass unmodified.
6. **Scenario 14.** `tests/cli/scenarios/14-non-git-writes.md` assertion 8
   (line 39) pins the *message shape* of a refusal and explicitly not the
   atomicity. It needs no edit, but read it before touching the stderr assertions
   — it is the contract the initial request names as the one not to break.

---

## 10. Notes

### Collision with the sibling item `2026-08-20-enforce-the-gitignore-trap-at-write-time-not-only-at-init`

**Verdict: no semantic collision. A textual one, in one direction, and it is
cheaper to land the sibling first.**

Both items touch the staging path, but at **different levels of the same file**
and in disjoint functions:

| | This item | Sibling |
| - | --------- | ------- |
| Functions modified | `FsTreeStore._write_staged` (new), `_mkdir_owned` (new), `_write_node`, `_write_meta`, `set`, `update_capability`, `write_plan_stage`, `_write_tags`, `_set_fields_at`, 4 × `extends_*`, `create_work`, `update_work`, `write_artifact`, `write_draft`, `write_sidecar`; deletes `_atomic_write` | module-level `git_stage` (`:301-307`), module-level `git_mv` (`:347-371`), one new shared helper |
| Functions **both** touch | — none — | |
| `git_stage` | calls it (through `_stage`), never edits it | edits it; its criterion 9 forbids touching any `_stage` override or `FsWorkStore` method |
| `_stage` | calls it from inside `_write_staged` | does not touch it |

Behavioral interaction, checked in both directions:

- The sibling makes `git_stage` **print and proceed** on a dropped path — it
  raises nothing, so `_write_staged`'s `except BaseException` never fires and no
  rollback is triggered by a warning. Correct: a dropped path is a path git
  never had, not a failed write.
- When every path is dropped, the sibling's `git_stage` runs no `git add` at all
  (`live` is empty, `:306-307` today), so there is nothing to fail and nothing to
  undo. Unchanged by this item.
- **One assertion worth coordinating.** This item's criterion 8 pins *exactly one*
  `tcw: ` line on stderr for a refused stage. The sibling adds a second `tcw: `
  line when a staged path is also gitignored. The two cannot both fire in this
  item's fixture — its paths (`docs/work/backlog/…`, `docs/taxonomy/…`) are not
  ignored, verified in §4a (`check-ignore(backlog/x) exit=1`) — but the new tests
  should filter stderr on the **`tcw: git command failed`** prefix rather than on
  "exactly one `tcw: ` line", so they stay true whichever item lands first.

**Order: sibling first, this item second.** Purely a line-drift argument. The
sibling's diff is small and localized around `:301-371`, shifting everything
below it by a uniform handful of lines. This item's diff restructures fourteen
methods spread from `:1045` to `:3939`, invalidating every fs.py citation in the
sibling's spec past `:1045` and forcing its author to re-derive them.

Worth telling that author regardless of order: **the sibling's spec was written
against `a875de9` too, so its fs.py numbers are already stale** by the three
containment commits — `:305`→`:306`, `:359`→`:360`, `:492`→`:493`,
`:994`→`:1058`, `:1207`→`:1283`, `:1221`→`:1297`, `:1831`→`:1915`,
`:1845`→`:1929`, `:2917`→`:3001`, `:3289`→`:3373`, `:3692-3701`→`:3776-3785`. Neither order produces a merge conflict in the same
hunk. If this item lands first anyway, the sibling's plan must re-run its own
line derivation — nothing in its design changes.

### The `_write_staged` contract does not restore an unlinked file

`update_capability`'s override-clear branch runs `desc.unlink(missing_ok=True)`
(`:2178`) before `_write_meta`. If staging is refused afterwards and the
directory was not owned by this call, the `description.md` that was deleted is
**not** restored. That is pre-existing behavior, unchanged, and it is on the
correct side of the spec's boundary — restoring prior content is the deferred
atomicity work, not this item. Worth a sentence in the reworked comment block so
the next reader does not think it was missed.

### The empty intermediate directory

`capabilities add a/b` and `taxonomy add x/y` create the intermediate parent via
`parents=True`; the rollback removes only the leaf. Verified inert: git does not
track an empty directory, so `git status --porcelain` is clean, and
`_all_meta_dirs` (`:1583`) does not see a folder without `meta.yaml`. Same
disposition `create_work` already documents for `backlog/` (`:3627-3634`). Tests
must assert on the leaf and on `porcelain`, never on the parent.

### Fixture id

`tcw init --id t …` is rejected (`project ID is reserved: t`). The spec's
acceptance-criteria fixture uses it. Use any non-reserved id.

### `dump_yaml` promotion via a temp file

Six sites move from `path.write_text(...)` to `_atomic_write_all`, which writes
`<name>.tmp` beside the target and `replace`s it. Byte-identical output, but a
transient `tcw-config.yaml.tmp` now appears in the user's tree during
`tcw work tags add`. `_atomic_write_all` unlinks it on any failure (`:900-903`),
and criterion 7 asserts none survives.
