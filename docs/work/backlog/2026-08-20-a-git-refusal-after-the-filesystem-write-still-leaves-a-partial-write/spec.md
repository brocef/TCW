# Spec — A git refusal after the filesystem write still leaves a partial write

## Capability changes

No new capabilities, no status flips. Wording deltas only, on the entries whose
commands can now undo what they created when git refuses the stage:

| Entry | Delta |
| ----- | ----- |
| `taxonomy/add-a-term` | Its promise today is scoped to the *absent*-repository case — "A refused add exits non-zero and writes nothing — including outside a Git repository, where the command refuses before it creates the term folder rather than leaving one behind" (`docs/capabilities/taxonomy/add-a-term/description.md:3`). Broaden it to a repository that exists and refuses. |
| `capabilities/add-a-capability` | Same promise, same reason. |
| `capabilities/override-inherited` | A materialized override folder is removed when its staging is refused. |
| `capabilities/set-a-capabilitys-status` | Same. |
| `work/open-a-work-item` | `tcw work new` leaves no half-created item folder. |
| `work/customize-lifecycle-artifact-templates` | The `tcw work scaffold` entry: a refused stage leaves no `<artifact>.draft.md`. |
| `web/editing` | The `serve` write routes compose the same store methods, so they inherit the rollback. |

The plan confirms the final list against `tcw capabilities list` and writes the
sidecar; nothing is written at this stage.

**Not changed:** `work/retitle-a-work-item`, `work/tag-a-work-item`,
`work/start-a-work-item`, `work/manage-the-work-inbox`. The first two edit files
that already exist (nothing is created, so nothing is undone — see Goal 3), the
third is a move (Non-goals), and the fourth already rolls back
(`tcw/store/fs.py:3245-3249`).

## Problem

TCW refuses a filesystem-store write *before* touching the disk when the
repository is absent: `require_repository` (`tcw/store/fs.py:318-329`) raises
`ValueError`, and `FsTreeStore._require_repository` (`:936-938`) is called at the top
of every public write. A repository that exists and **refuses** has no such
guard, and cannot have one — a lock acquired a millisecond later is not
predictable. It surfaces only when `git add` fails, which is after the content is
on disk.

Reproduced at `4ebb1c5`, `tcw 1.0.0` (editable install), macOS. Fixture: a git
repository with `tcw init work`, committed; then `touch .git/index.lock` for the
duration of the command. That lock is a precise simulation — verified: `git add`
exits **128**, while `git rev-parse --show-toplevel` and `git check-ignore` both
still exit 0, so `require_repository` (`:318`) and `git_ignored` (`:331-344`) answer
normally and the call reaches staging exactly as a real refusal does.

**`tcw work new "Repro item"`** — exit 1, one line on stderr
(`tcw: git command failed (exit 128): git -C … add -- …/state.yaml`, rendered by
`tcw/cli.py:190-203`), and left behind:

```
docs/work/backlog/2026-08-20-repro-item/
docs/work/backlog/2026-08-20-repro-item/state.yaml
?? docs/work/backlog/2026-08-20-repro-item/
```

**`tcw work scaffold spec <slug>`** — exit 1, and `spec.draft.md` survives in the
item folder, untracked.

**`tcw taxonomy add Widget --slug widget`** — exit 1, and
`docs/taxonomy/widget/` survives with both files.

The message is legible. What is missing is that the user is not told what to
remove, and nothing removes it.

### Why the code stops where it does

The three sites that already roll back deliberately exclude the staging phase:

- `_write_node` (`tcw/store/fs.py:981-1018`) rolls back a directory it created on
  a *content* failure, then stages **outside** the guard: _"a git failure after
  both files landed leaves a fully valid object on disk, and deleting it would
  destroy content the caller just wrote"_ (`:1015-1017`).
- `create_work` (`:3446-3560`) says the same at `:3550`.
- `set` (`:1793-1810`) and `update_capability` (`:2067-2116`) key their rollback
  on `not existed and not (d / "meta.yaml").exists()` — content landed means keep
  it (`:1807`, `:2114`).

That reasoning is right for an **update** and wrong for a **creation**. On a
folder this call brought into existence, "content the caller just wrote" is the
only content there is; nothing pre-existing is at risk, and leaving it behind is
the reported symptom. This item reverses the policy for created paths only.

### Sites with no rollback at all

Every remaining creating write stages immediately after writing, with nothing in
between:

| Site | Write | Stage |
| ---- | ----- | ----- |
| `_write_meta` (capabilities) | `:1742-1743` | `:1744` |
| `write_plan_stage` | `:2586-2587` | `:2588` |
| `update_work` | `:3690` | `:3692`, `:3694` |
| `write_artifact` | `:3754` | `:3755` |
| `write_draft` (`tcw work scaffold`) | `:3780` | `:3781` |
| `write_sidecar` | `:3854` | `:3855` |
| `_set_fields_at` | `:3288` | `:3289` |
| `_write_tags` | `:2917` | `:2918` |
| `FsTaxonomyStore.extends_add` / `_remove` | `:1207`, `:1221` | `:1208`, `:1222` |
| `FsCapabilitiesStore.extends_add` / `_remove` | `:1831`, `:1845` | `:1832`, `:1846` |

`update_work` creates `initial-request.md` when the item had none (`:3692-3694`
stage it separately). The four `extends` sites create their component
`config.yaml`: `init` writes only leaf directories and a `.gitkeep` (`:722-723`),
so `docs/taxonomy/config.yaml` does **not** exist after `tcw init taxonomy` —
verified on a fresh node — and `tcw taxonomy extends add` is what creates it.

## Goals

1. A git refusal during a filesystem-store write removes the paths **that call
   created**, then re-raises. After `tcw work new` under a held `index.lock`,
   `git status --porcelain` is empty and the backlog folder is as it was.
2. One place does it, not one per caller: content and its `git add` meet in a
   single method, and every creating write goes through it.
3. **Nothing that already existed is ever removed.** An update whose staging is
   refused keeps what it wrote; a folder that was already there survives even
   when a file inside it is undone.
4. The failure is still reported, in the same words: exit 1, one line on stderr,
   no traceback. Rolling back and exiting 0 would be worse than today.
5. A rollback that cannot proceed never masks the original error, and never adds
   a second line of output.

## Non-goals

- **Write-to-temp-then-move atomicity** for every write path. Explicitly deferred
  by the requester. `inbox_accept` already has that shape (`:3221-3233`) and is
  left alone.
- **Undoing a move.** `tcw work start` stages after the rename
  (`:2240`, `:2309`), and `_effect_transition` moves before it writes fields
  (`:3320`). Under a held lock `start` leaves the item in `active/`, stamped and
  unstaged — verified. That is not a partial *creation*: undoing it means
  deleting or moving back content that existed before the call, and the codebase
  already settled the question the other way — _"The move is never rolled back on
  a commit failure … undoing it introduces a second failure mode worse than the
  first"_ (`:3349-3352`). The behavior is pinned as a criterion so nothing drifts
  into it.
- **Restoring the previous content of a file this call overwrote.** Under a held
  lock, `tcw work edit <slug> --title X` reports failure with the new title
  already in `state.yaml` — verified. Fixing that needs a content snapshot, which
  is the deferred atomicity work, and touching it here would cross the hard
  boundary in the opposite direction.
- **`git rm` failing partway.** `git_rm` (`:310-312`) deletes; recovering deleted
  content is not "undo what this call created".
- **`docs/work/.claiming/`,** created by every `start` and never removed. Its own
  deferred item (prior item's `refined-outcome.md:125-126`).
- **A precondition that predicts a refusal.** Impossible by construction.
- **`ensure_worktree_ignored` (`:485-494`)** — the one `git_stage` outside the
  store classes. It can create `.gitignore` and leave it after a refused stage,
  but only on a node where the user deleted the `.gitignore` that `init` writes
  (`:725-732`), and the leftover is one line the node wants anyway. Found by the
  sweep; deliberately not covered.
- **`init` itself.** It stages nothing — _"Unstaged, like everything else init
  writes"_ (`:592`) — and its only git calls are `git_root` (`:90-104`, swallows
  `CalledProcessError`) and `git_ignored` (`:331-344`, returns a code). It cannot
  reach this failure.
- **`_inbox_write` (`tcw/work/recursion.py:258-283`),** the delegate/escalate
  path. _"The one write in the adapter that never stages"_ — same reason.

## Design

### Where it lives

The chokepoint is not a git helper — `git_stage` cannot know which of the paths
it is given were just created. It is the **write-then-stage pair**, which is one
shape repeated seventeen times in `tcw/store/fs.py` and nowhere else in the
package (`grep -rn "write_text\|_atomic_write\|dump_yaml" tcw/ | grep -v store/fs.py`
returns exactly one line, `recursion.py:281`, which never stages). Collapse the
pair into one private method on `FsTreeStore`, and the rollback is written once.

```python
def _mkdir_owned(d: Path) -> bool:
    """Create `d`, returning whether *this call* made it.

    `exist_ok=False` is the ownership proof: exactly one process's `mkdir`
    succeeds, so there is no check-then-act window — which is what closes the
    `existed = d.exists()` TOCTOU noted at `_write_node`.
    """
    try:
        d.mkdir(parents=True)
        return True
    except FileExistsError:
        return False
```

on `FsTreeStore`:

```python
    def _write_staged(self, pairs: list[tuple[Path, str]], *,
                      owned_dir: Path | None = None) -> None:
        """Write every `(path, content)` and stage the lot, undoing what *this
        call* created if either half fails, then re-raising.

        Never removes a path that was already there: an update whose staging is
        refused keeps the content it just wrote, because deleting it turns a
        recoverable failure into data loss. `owned_dir` is a directory the caller
        proved it created (`_mkdir_owned`, or a bare `mkdir`) — removed whole.
        Everything else is per file, and only files absent when this call began.

        Best-effort and silent: the undo never masks the original error, and
        never adds a second line to a refusal whose one-line shape is pinned.
        """
        new = [p for p, _ in pairs if not p.exists()]
        try:
            _atomic_write_all(pairs)
            self._stage(*(p for p, _ in pairs))
        except BaseException:
            if owned_dir is not None:
                shutil.rmtree(owned_dir, ignore_errors=True)
            else:
                for p in new:
                    with suppress(OSError):
                        p.unlink()
            raise
```

`from contextlib import suppress` is the only new import; `shutil`,
`_atomic_write_all` (`:877-902`) and `_stage` (`:940-942`, overridden at
`:2176-2178` so the work store's own repository is used) already exist. No
`ExitStack`, no transaction object: one `try` covers both phases, and a stack of
callbacks would be more machinery than the thing it manages.

### How a path is known to be created

Two mechanisms, because a directory and a file have different failure costs.

- **Directory — `mkdir(exist_ok=False)` succeeding.** Not racy: only one
  process's `mkdir` returns. This is what lets the undo `rmtree` a folder
  outright, and it retires the `existed = d.exists()` pattern at `:991`, `:1797`
  and `:2085` along with the `ponytail:` TOCTOU note at `:1004-1010` that names
  it. That note says closing the race needs "a create-only
  `mkdir(exist_ok=False)`, or a lock" — this takes the first.
- **File — absent at entry to `_write_staged`.** This *is* a check-then-act
  window, and it is acceptable here in a way the directory one is not: if a
  competitor creates the file between the check and the failure, our own
  `_atomic_write_all` has already replaced its content with ours (last writer
  wins, as it does today). Deleting the file destroys nothing the call had not
  already overwritten. A `rmtree` on a directory has no such argument — it would
  take sibling files we never touched — which is why directories get the
  stronger proof.

### The rule, pinned

- The call created `backlog/<slug>/` and three files inside → the **folder** goes,
  including the files. `create_work`'s `parents=True` may also have created an
  intermediate `backlog/`; only the leaf is removed, and an empty `backlog/` is
  inert (git does not track it, every read path tolerates it) — the existing note
  at `:3543-3550`, unchanged.
- The call wrote one file into a folder that was already there → only the
  **file** goes; the folder and every sibling stay.
- The call overwrote a file that was already there → **nothing** goes.
- A multi-file write that fails partway: the undo is best effort and per path.
  Files this call created are removed one at a time, each in its own
  `suppress(OSError)`, so one that cannot be unlinked does not stop the rest.
  `shutil.rmtree(..., ignore_errors=True)` is the same discipline for a folder.
  When the undo cannot proceed the behavior degrades to exactly today's: the real
  error propagates, and something is left on disk. Nothing extra is printed —
  a second stderr line would break the one-line refusal shape pinned by
  `tests/cli/scenarios/14-non-git-writes.md:39` and
  `tests/test_non_git_writes.py:305-335`.
- `except BaseException`, matching `_atomic_write` (`:872-874`) and
  `_atomic_write_all` (`:899-902`): a `KeyboardInterrupt` mid-write cleans up too.

### Call sites

Every `self._stage(...)` in `tcw/store/fs.py` becomes a `_write_staged` call,
except two that do not stage written content:

| Site | Change |
| ---- | ------ |
| `_write_node` `:981-1018` | `owned = _mkdir_owned(d)`; one `_write_staged([...], owned_dir=d if owned else None)`. Its `try`/`except`, its `existed`, and the "staging stays outside" note all go. |
| `_write_meta` `:1739-1744` | Same shape, one pair; it now does its own `mkdir`. |
| `set` `:1793-1810` | Drops its `existed`, its `mkdir` and its whole guard — `_write_meta` owns both now. |
| `update_capability` `:2085-2116` | `owned = _mkdir_owned(d)` replaces `existed` + `mkdir`; the guard becomes `if owned: shutil.rmtree(d, ignore_errors=True)`. It stays, because its delta-clearing branch stages a *directory* (`:2096`) to pick up a `description.md` removal, which `_write_staged` does not model. The inner `_write_node`/`_write_meta` see the directory already there, pass `owned_dir=None`, and undo per file — the two guards compose without double-deleting. |
| `write_plan_stage` `:2586-2588` | `owned = _mkdir_owned(path.parent)`, then `_write_staged([(path, content)], owned_dir=...)` — a `plan/` folder this call created goes with the file. |
| `_write_tags` `:2917-2918`, `_set_fields_at` `:3288-3289`, four `extends` sites `:1207-1208`, `:1221-1222`, `:1831-1832`, `:1845-1846` | `dump_yaml(p, x)` + `_stage(p)` → `_write_staged([(p, yaml.safe_dump(x, sort_keys=False, allow_unicode=True))])`. Identical bytes — `dump_yaml` (`:766-767`) is that exact call — via `_atomic_write_all` instead of a bare `write_text`. The four `extends` sites create their `config.yaml`; the other two overwrite a file that is always there, and route through anyway so the chokepoint has no exceptions to remember. |
| `create_work` `:3551-3558` | Keeps its bare `d.mkdir(parents=True)` (a slug collision must still raise), passes `owned_dir=d`; its `try`/`except` goes. |
| `update_work` `:3690-3694` | One `_write_staged(writes)`; the two `_stage` calls collapse. A created `initial-request.md` is undone, `state.yaml` is not. |
| `write_artifact` `:3754-3755`, `write_draft` `:3780-3781`, `write_sidecar` `:3854-3855` | `_write_staged([(p, content)])`. |
| `update_capability` `:2096` and `inbox_accept` `:3234` | **Unchanged.** Neither stages content it just wrote through this pair — the first stages a directory for a removal, the second stages a folder swapped into place, and already rolls back at `:3245-3249`. |
| `git_stage` at `:492`, `:2240`, `:2309` | **Unchanged.** `ensure_worktree_ignored` and the two `start` renames — see Non-goals. |

`tcw serve` composes the same store methods and inherits the rollback with no
change to `tcw/serve/`.

### Abstraction litmus test

**The contract passes; the mechanism is filesystem-private.**

_"Could a non-filesystem store implement this operation?"_ — "a write that fails
undoes the records it created, and touches nothing that existed before" is a
plain statement about **items, fields and attachments**. A tracker-backed store
implements it by deleting the issue it just POSTed, or by not committing its
transaction. So the *guarantee* belongs in the model and is documented as store
behavior.

The *mechanism* has no abstract analog and stays behind the adapter's private
door: `mkdir(exist_ok=False)` as an ownership proof, `unlink`, `shutil.rmtree`,
and the fact that "staged" is a thing at all. `_write_staged` and `_mkdir_owned`
are private to `tcw/store/fs.py`; **nothing is added to `tcw/store/base.py`**, no
operation is added or changed, and no caller outside the adapter learns a new
verb. A remote store that implements the same guarantee differently satisfies
every criterion below except the ones that name a path on disk.

### Harness compatibility

Nothing here is a skill, a command, a hook or an injected line of context: it is
CLI behavior in `tcw/store/fs.py`, identical under Claude and Codex. No
documentation entry needs a harness-specific variant.

## Acceptance criteria

**The refusal fixture, used by every criterion below.** A git repository with
`tcw init --id t work taxonomy capabilities`, everything committed, then
`.git/index.lock` created and held for the duration of the command under test and
removed afterwards. Verified at spec time: with the lock held `git add` exits
**128** while `git rev-parse --show-toplevel` and `git check-ignore -q` both exit
0, so the write reaches staging exactly as a real refusal does. A test may
equivalently `monkeypatch.setattr("tcw.store.fs.git_stage", …)` to raise
`subprocess.CalledProcessError(128, ["git", "add", "x"])`, which is what
`tests/test_non_git_writes.py:317-325` already does — the end-to-end criteria (1,
2, 3, 9) use the real lock, since only that proves the whole command path.

1. **`tcw work new "T"` leaves nothing.** Under the fixture, exit **1**, and
   afterwards `git status --porcelain` is empty and
   `find docs/work/backlog -mindepth 1` prints only `docs/work/backlog/.gitkeep`.
   (Today: the folder and `state.yaml` survive, `?? docs/work/backlog/<slug>/`.)
2. **`tcw work scaffold spec <slug>` leaves nothing.** On a committed backlog
   item, under the fixture: exit **1**, `git status --porcelain` empty, and
   `<slug>/spec.draft.md` does not exist. (Today it does.)
3. **`tcw taxonomy add Widget --slug widget` leaves nothing.** Exit **1**,
   `git status --porcelain` empty, `docs/taxonomy/widget` does not exist.
   The same for `tcw capabilities add a/b Thing` and `docs/capabilities/a/b`.
4. **A file in a folder that was already there takes only the file.** With a
   committed item that has `state.yaml` and `initial-request.md`, a
   `write_artifact(slug, "spec", "x")` whose staging is refused leaves the item
   folder present, `state.yaml` and `initial-request.md` byte-identical to
   before, and no `spec.md`.
5. **An update is never undone — the hard boundary.** With a committed item,
   `tcw work edit <slug> --title Renamed` under the fixture exits 1 and
   `state.yaml` still reads `title: Renamed`; the file is not deleted and not
   reverted. Same for a `capabilities set` on a capability whose folder already
   existed: its `meta.yaml` survives.
6. **The two tests that pin the reversed policy are rewritten, not deleted.**
   `tests/test_store_editor.py:1127` `test_update_capability_keeps_override_when_staging_fails`
   and `:1164` `test_set_keeps_override_when_staging_fails` today assert that a
   *freshly materialized override folder* survives a refused stage. Both now
   assert it is gone, and each docstring records that this item deliberately
   reverses what its old docstring pinned. Their siblings at `:1105` and `:1147`
   (a *content* failure removes the folder) pass unmodified.
7. **No `.tmp` survives.** After every criterion above,
   `list(node.rglob("*.tmp")) == []`.
8. **The message is unchanged.** `tests/test_non_git_writes.py:305-335`
   (`test_a_git_subprocess_failure_is_a_message_not_a_traceback`) and `:847-867`
   (`test_a_string_valued_git_command_is_rendered_as_one_command`) pass
   **unmodified** — verified green at spec time. Under the fixture each command
   in criteria 1-3 prints exactly one line on stderr from `tcw` matching
   ``^tcw: git command failed \(exit 128\): git .*$`` (git's own diagnostic goes
   straight to the terminal and is not counted), and no line contains
   `Traceback`.
9. **A move is still not rolled back.** Under the fixture, `tcw work start
   <slug>` exits 1 and the item is in `docs/work/active/<slug>/` with `owner` and
   `started` written — the behavior measured today, pinned so the rollback does
   not spread into transitions. `tests/test_external_work_store.py:838-856`
   (`test_a_refused_stage_after_the_move_is_a_transition_commit_error`) passes
   unmodified.
10. **One chokepoint, checkable structurally.** In `tcw/store/fs.py`,
    `grep -n "self\._stage("` returns exactly three sites: inside `_write_staged`,
    `update_capability`'s directory stage (`:2096` today), and `inbox_accept`'s
    (`:3234` today). `grep -n "_atomic_write\|dump_yaml("` returns no call that is
    followed by a `self._stage(...)` of the same path.
11. **The undo cannot mask the original error.** With `Path.unlink` monkeypatched
    to raise `PermissionError` and `git_stage` raising
    `CalledProcessError(128, …)`, `FsWorkStore.create_work` raises the
    `CalledProcessError` — not the `PermissionError` — and `main(["work", "new",
    "T"])` still returns 1 with the criterion-8 line.
12. **Nothing added to the abstract interface.**
    `git diff --stat` touches `tcw/store/fs.py` and tests only; `tcw/store/base.py`
    is unmodified, and `_write_staged` / `_mkdir_owned` appear nowhere outside
    `tcw/store/fs.py`.
13. **`pytest` from the repository root is green** — the bare command CI runs
    (`.github/workflows/test.yml`, after `pip install -e .[dev]`). Run outside any
    sandbox that restricts `git`; the suite creates throwaway repositories.

## Risks

- **Deleting something that mattered.** The whole change is a delete on a failure
  path, and the failure path is by definition rare and hard to observe. The
  ownership proofs are the mitigation: a directory is removed only when this
  call's own `mkdir(exist_ok=False)` returned, and a file only when it was absent
  a moment earlier and this call has since overwritten it. Criterion 5 is the
  guard test; it must fail if the guard is dropped.
- **Two guards on one path.** `update_capability` keeps an outer directory guard
  while its inner `_write_node` runs `_write_staged`. Composed wrongly, the inner
  per-file undo could delete files inside a directory the outer guard is about to
  keep. It cannot as designed — the inner call sees the directory already present
  and only unlinks files it created there, which the outer `rmtree` would have
  taken anyway — but this is the one place in the diff worth a second reader.
- **`dump_yaml` → `_atomic_write_all` on six sites** changes how `tcw-config.yaml`
  and the component `config.yaml` files are written (temp file beside the target,
  then `replace`). Byte-identical output; a brief `tcw-config.yaml.tmp` in the
  user's tree is new, and `_atomic_write_all` unlinks it on any failure
  (`:899-902`).
- **`work edit` still half-applies.** Criterion 5 makes it a *requirement* that a
  refused `edit` leaves the new title on disk while reporting failure. That is
  surprising, and it is the requester's decided boundary — the alternative is
  restoring prior content, which is the deferred atomicity work. Worth a sentence
  in the release note so it reads as a choice rather than an oversight.
- **A missed site** leaves the fix looking complete while one command still
  litters. Criterion 10 is the structural sweep that discharges it; criteria 1-4
  are the behavioral spot checks.

## Notes

### Repo-wide sibling sweep (stage-`spec` step 5)

Not narrowed. `grep -rn "write_text\|_atomic_write\|dump_yaml" --include=*.py tcw/`
returns exactly one hit outside `tcw/store/fs.py` — `tcw/work/recursion.py:281`
(`_inbox_write`), which never stages and is guarded at `:272` instead. Every
`git_stage` call in the package is at `tcw/store/fs.py:492`, `:942`, `:2178`,
`:2240`, `:2309`. So the whole surface is one file, and the table under **Call
sites** is the complete census of it. Two siblings found and dispositioned:

- **`tcw taxonomy extends add` / `capabilities extends add` create their
  component `config.yaml`.** `init` writes only leaf directories and a
  `.gitkeep` (`:717-723`) — confirmed on a fresh node: `docs/taxonomy/config.yaml`
  does not exist after `tcw init taxonomy`. A refused stage there leaves a
  created file behind, the same defect wearing different clothes. **In scope**,
  via the same chokepoint.
- **`ensure_worktree_ignored` (`:485-494`)** can create `.gitignore` and leave it.
  **Out of scope** — see Non-goals for why the reachable case is not worth three
  lines.

### `tcw/store/fs.py:888` is a different defect

The `ponytail:` note there — _"the promote loop is not atomic across files — a
process death between two `replace()` calls still leaves a partial update"_ —
is about **crash** atomicity inside `_atomic_write_all`, not about a git refusal.
This change does not fix it and does not need to: `_write_staged` calls
`_atomic_write_all` unchanged, and a torn multi-file update into a **pre-existing**
folder (`update_work` rewriting `state.yaml` and `initial-request.md` when both
already existed) still leaves one promoted and one not. Nothing in this item
touches that window. Leave the note where it is.

Its cross-reference is stale, though: it cites _"the `accept_inbox` shape,
fs.py:2246"_, and `inbox_accept` is now at `:3167` with the whole-directory swap
at `:3238`. `:2246` is inside `start`'s take-over branch. Worth correcting while
the file is open.

### Assumptions

- That a held `.git/index.lock` is representative of "a repository that exists
  and refuses" for *staging specifically*. Verified for `git add` (exit 128) and
  for the read-only probes the write path makes first. A rejecting `pre-commit`
  hook is a different animal — it refuses `git commit`, not `git add`, and that
  path already reports through `git_commit_result` / `TransitionCommitError`
  (`:3341-3358`), which this item does not touch.
- That no test outside `tests/test_store_editor.py:1127` and `:1164` asserts a
  created path survives a refused stage. Searched: `grep -rn "staging fails\|
  when_staging\|git_stage" tests/` returns those two plus
  `tests/test_non_git_writes.py` (message shape), `tests/test_work_autocommit.py`
  (commit, not stage) and `tests/test_external_work_store.py:838` (the move,
  criterion 9). The plan should re-run that search before editing, since a
  sibling item may land a new one.
