# Spec — Harden _effect_transition against a lost status-transition race

## Capability changes

None. This node has no capabilities component (`tcw capabilities list` →
"no tcw capabilities node here"), so there is no ledger to delta. The change also
declares nothing new: `submit` / `rework` / `complete` already promise to either
move the item or say why they could not; this makes that true on one timing where
it currently crashes instead.

## Problem

`FsWorkStore._effect_transition` (`tcw/store/fs.py:2729-2745`) resolves the item
twice and only tolerates a miss on the first:

```python
item = self.get(slug)          # fs.py:2732 — returns None tolerantly
src  = self._find(slug)        # fs.py:2734 — typed `-> Path | None` (fs.py:2073)
...
self._mv(src, dst)             # fs.py:2743 — None is never checked
```

`_find` (`fs.py:2073-2077`) rescans the store from disk, so a competing process
that moves the item's folder between line 2732 and line 2734 leaves `src` as
`None`. This is the same shape as the defect just fixed in `start()`
(`fs.py:2020`, item `2026-08-11-fix-typeerror-when-a-work-claim-loses-the-race-at-find`,
completed 2026-08-11), which deliberately left this call site alone.

**The symptom is not the `TypeError` the request assumed.** `_mv` → `git_mv`
(`fs.py:300-324`) stringifies its argument, so `None` becomes the literal
pathspec `"None"` and the two branches fail differently:

- Tracked destination (`fs.py:322-323`): `git add -- None` exits 128 —
  `fatal: pathspec 'None' did not match any files` — raising
  `subprocess.CalledProcessError`. Verified directly against a scratch repo.
- Gitignored destination (`fs.py:313-321`, the default for `completed/` and
  `discarded/` — see the `tcw init` notice in `cli.py:66-68`): `git rm --cached
  --ignore-unmatch -- None` succeeds silently, then `shutil.move("None", …)`
  raises `FileNotFoundError`.

Neither is in the CLI's handled set (`tcw/work/cli.py:34`:
`_ERRORS = (ValueError, IllegalTransition, MultipleMatch, TransitionCommitError,
AlreadyClaimed)`), so the loser gets an unhandled traceback either way. Which
traceback depends on gitignore configuration, which is why the request's guess
was wrong.

### Which transitions are actually exposed

`transition()` (`base.py:1268-1276`) clears `owner`/`started` via `set_field`
when either end of the move is `active`, and `set_field` (`fs.py:2721-2723`) does
guard its own `_find`. That narrows the window but does not close it: `set_field`
and `_effect_transition` each rescan independently. Two routes have no guard in
front of them at all:

- `review → completed` and `review → discarded` — neither end is `active`, so
  `set_field` is skipped and `_effect_transition` is the first resolution.
- `backlog → completed` for a completable epic (`base.py:1408-1410`), which calls
  `_effect_transition` directly, bypassing `transition()`.

### Is the window reachable?

Not demonstrated in the wild, and not equally for every transition. `start` is
the one two agents genuinely race — both picking the same backlog item — and that
one is now handled. Racing `submit` on a single item requires two agents that
both believe they own it, which the `start` claim exists to prevent. The honest
assessment is that this is **reachable but rare**, and that rarity is the
argument for a cheap answer rather than an expensive one.

### The sibling sweep

Repo-wide over all 22 `_find` call sites in `tcw/store/fs.py`. Five ignore the
`None`:

| Site        | Function            | Failure on `None`                                                     |
| ----------- | ------------------- | --------------------------------------------------------------------- |
| `fs.py:2734` | `_effect_transition` | The reported defect; crashes in `git_mv` as above.                    |
| `fs.py:2005` | `start` take-over    | `None.relative_to(...)` → `AttributeError`.                            |
| `fs.py:2219` | `_plan_stage_path`  | `None / "plan"` → `TypeError`. `_declared_plan_stages` guards first, so residual window only. |
| `fs.py:2485` | `_validation_problems` | `None / "plan.md"` → `TypeError`. Inside `except ValueError` (`fs.py:2504`), so a `ValueError` here is already absorbed as a reported problem. |
| `fs.py:2804` | `get_detail`        | `None / "state.yaml"` → `TypeError`. Already returns `WorkDetail \| None`. |

The other seventeen either guard explicitly or are `_find is None` tests
themselves. Eight of the guards are the identical three-line
`if d is None: raise ValueError(f"no such work item: {slug}")` (`fs.py:2145`,
`2723`, `2795`, `2948`, `3086`, `3106`, `3143`, `3165`).

## Goals

1. No `_find` result reaches a consumer that cannot take `None`.
2. A transition that loses this race reports something a person can act on, and
   changes nothing.
3. The guard is one obvious call, so the next `_find` caller does not have to
   rediscover the rule.

## Non-goals

- **No claiming protocol for `submit`/`rework`/`complete`.** `.claiming/`, the
  retry loop, and `AlreadyClaimed` exist because `start` has a genuine two-agent
  race with a meaningful winner. These transitions do not, and building the
  protocol for an undemonstrated window is cost without evidence.
- **No new exception type.** `ValueError` is already in `_ERRORS`
  (`work/cli.py:34`) and already renders as `tcw work <cmd>: <message>`.
- **No change to `_find`.** Returning `None` is correct; the callers are wrong.
- **`start()`** — fixed by the sibling item.
- **The `set_field` writes that precede a failed transition.** `transition()`
  blanks `owner`/`started` and `complete()` writes `resolution` before the move.
  On a lost race those land in the winner's item (the same inode, via the pre-
  rename path). Recorded as a risk below, not fixed here — the values written are
  the ones the winner's own transition wants anyway.

## Design

### 1. One resolver that cannot return `None`

Add a private helper next to `_find`:

```python
def _require_dir(self, slug: str) -> Path:
    d = self._find(slug)
    if d is None:
        raise ValueError(f"no such work item: {slug}")
    return d
```

Replace the eight hand-written copies of that guard, and use it at `fs.py:2005`
and `fs.py:2219`. Behavior-preserving — the message is byte-identical to what
those sites already raise. Net effect is a deletion (≈8 × 2 lines removed against
5 added), which is the whole reason the helper earns its place rather than
writing four more inline guards.

`fs.py:2485` becomes `_require_dir` too, where its `ValueError` is caught by the
enclosing `except ValueError` (`fs.py:2504`) and reported as a validation
problem — the right outcome for a validation sweep that races a transition.

`fs.py:2804` (`get_detail`) does **not** use it: the function is already
`-> WorkDetail | None`, so `if d is None: return None` is both correct and
smaller.

### 2. `_effect_transition` reports the race, not a generic miss

`_require_dir`'s "no such work item" is wrong here — the item *does* exist, it
just moved. Re-read it and say so:

```python
src = self._find(slug)
if src is None:
    current = self.get(slug)
    where = (f"it is now in '{current.status}'" if current is not None
             else "it no longer exists")
    raise ValueError(
        f"cannot move {slug} to {to_status}: another process moved it while "
        f"this transition was running ({where}). Nothing was changed."
    )
```

That is the answer to the request's open design question, and it is four lines.
The loser learns the item's real status, learns nothing was written, and can
decide whether to retry — without a protocol, a lock, or a new error class.

Litmus test: "could a non-filesystem store report a transition that lost a race
by re-reading the item's current status?" Yes — any store can re-read. The
*guard* lives in the FS adapter because `_find` does, but nothing about the
reported outcome is filesystem-specific, and the error type is the one the
abstract CLI already handles.

## Acceptance criteria

1. `FsWorkStore._effect_transition` raises `ValueError` — not
   `CalledProcessError`, `FileNotFoundError`, or `TypeError` — when `_find`
   returns `None`, and the message names both the slug and the item's re-read
   current status.
2. That error reaches the CLI as `tcw work submit: cannot move <slug> …` with a
   non-zero exit code, not a traceback.
3. When the guard fires, nothing under the work root has moved: the item's folder
   is exactly where the competing process left it.
4. A test forces `_find` to return `None` deterministically (monkeypatch, as the
   sibling item's test does — not by racing threads), and fails against the
   current code.
5. Each of `fs.py:2005`, `2219`, `2485`, `2804` has a test that drives it with
   `_find` returning `None` and asserts the handled outcome (`ValueError`, a
   reported validation problem, or `None`) rather than an attribute/type error.
6. `grep -n "_find(" tcw/store/fs.py` shows no remaining call whose result is
   dereferenced without either a `None` check or `_require_dir`.
7. The eight collapsed guard sites raise the same message as before —
   `no such work item: <slug>` — verified by the existing tests that assert it,
   unchanged.
8. Full suite green locally and both CI legs green.

## Risks

- **Proof-by-monkeypatch, again.** As with the sibling, no arrangement of files
  reproduces the interleaving: whatever makes `get()` succeed makes `_find`
  succeed. The tests exercise the handler, not the race. Accepted — the
  alternative is no test at all.
- **Touching eight already-correct call sites in a bug-fix item.** The collapse
  is behavior-preserving and net-negative in lines, but it widens the diff beyond
  the reported defect. Criterion 7 exists to bound it: any message change means
  the collapse went wrong. It is separable — if review objects, dropping it costs
  four inline guards instead.
- **Pre-move `set_field` writes are not rolled back** (see Non-goals). A losing
  `complete` will already have written `resolution` into the winner's item. That
  is pre-existing, unchanged by this item, and worth its own item if it ever
  matters.
- **`fs.py:2485` changes a crash into a reported validation problem**, so
  `tcw work validate` racing a transition now prints an extra line instead of
  exiting badly. That is the intended behavior, but it is a visible output change
  in a command whose output some caller may parse.

## Notes

- The request's claim that `_mv` fails with "the same opaque `TypeError`" is
  wrong; see Problem. The fix is unaffected, but the test must assert on
  `ValueError` rather than on "no longer `TypeError`".
- Documentation triggers expected to fire at implement time:
  `docs/changelogs/upcoming.md` (Any-Code-Change) and
  `docs/release-notes/upcoming.md` (user-visible error behavior).
  `skills/tcw-work/SKILL.md` does not — no CLI surface, lifecycle, or guardrail
  change.
