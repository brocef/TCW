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

- Tracked destination (`fs.py:323-324`): `git add -- None` exits 128 —
  `fatal: pathspec 'None' did not match any files` — raising
  `subprocess.CalledProcessError`. Verified directly against a scratch repo.
- Gitignored destination (`fs.py:313-322`, the default for `completed/` and
  `discarded/` — the ignore rules are set at `fs.py:489-499` and announced by the
  `tcw init` notice at `tcw/cli.py:67-69`): `git rm --cached --ignore-unmatch --
  None` succeeds silently, then `shutil.move("None", …)` raises
  `FileNotFoundError`.

Since `completed/` and `discarded/` are ignored by default, the *normal* terminal
transition takes the second branch; only a node that has un-ignored them takes
the first.

Neither is in the CLI's handled set (`tcw/work/cli.py:34`:
`_ERRORS = (ValueError, IllegalTransition, MultipleMatch, TransitionCommitError,
AlreadyClaimed)`), so the loser gets an unhandled traceback either way. Which
traceback depends on gitignore configuration, which is why the request's guess
was wrong.

### Which transitions are actually exposed

`transition()` (`base.py:1268-1276`) clears `owner`/`started` via `set_field`
when either end of the move is `active`, and `set_field` (`fs.py:2721-2723`) does
guard its own `_find`. That narrows the window for `submit` (`active → review`)
and `rework` (`review → active`) but does not close it: `set_field` and
`_effect_transition` each rescan independently.

Three routes have no guard in front of them at all — every legal transition
(`base.py:455-461`) where neither end is `active`:

- `review → completed` and `review → discarded` (`base.py:458-459`).
- `backlog → discarded` (`base.py:460`) — abandoning without a throwaway start.
- `backlog → completed` for a completable epic (`base.py:1408-1410`), which calls
  `_effect_transition` directly, bypassing `transition()` entirely.

### Is the window reachable?

Not demonstrated in the wild, and not equally for every transition. `start` is
the one two agents genuinely race — both picking the same backlog item — and that
one is now handled. Racing `submit` on a single item requires two agents that
both believe they own it, which the `start` claim exists to prevent. The honest
assessment is that this is **reachable but rare**, and that rarity is the
argument for a cheap answer rather than an expensive one.

### The sibling sweep

Repo-wide over all 23 `_find` call sites in `tcw/store/fs.py`. Five ignore the
`None`:

| Site        | Function            | Failure on `None`                                                     |
| ----------- | ------------------- | --------------------------------------------------------------------- |
| `fs.py:2734` | `_effect_transition` | The reported defect; crashes in `git_mv` as above.                    |
| `fs.py:2005` | `start` take-over    | `None.relative_to(...)` → `AttributeError`.                            |
| `fs.py:2219` | `_plan_stage_path`  | `None / "plan"` → `TypeError`. `_declared_plan_stages` guards first, so residual window only. |
| `fs.py:2485` | `_validation_problems` | `None / "plan.md"` → `TypeError`. Inside `except ValueError` (`fs.py:2504`), so a `ValueError` here is already absorbed as a reported problem. |
| `fs.py:2804` | `get_detail`        | `None / "state.yaml"` → `TypeError`. Already returns `WorkDetail \| None`. |

Of the remaining eighteen, one is `start`'s own call (`fs.py:2020`), already
translated into the claim-race recovery by the sibling item (`fs.py:2020-2034`);
the other seventeen guard explicitly, return the `None` deliberately, or test it.
Eight of the guards are the identical three-line
`if d is None: raise ValueError(f"no such work item: {slug}")` (`fs.py:2145`,
`2723`, `2795`, `2948`, `3086`, `3106`, `3143`, `3165`).

## Goals

1. No `_find` result reaches a consumer that cannot take `None`.
2. A transition that loses this race reports something a person can act on,
   naming the item's real current status, and does not itself move anything.
   **Not** "changes nothing" — see the residual writes below; the message must
   not claim more than the guard delivers.
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
  blanks `owner`/`started` (`base.py:1272-1274`) and `complete()` writes
  `resolution` (`base.py:1397`) *before* the move. On a lost race those have
  already landed, and via the pre-rename path they land inside the winner's
  moved folder. This is a real residual defect with its own worst case (below);
  it needs a separate item, and closing this one should not imply it was fixed.

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
        f"cannot move {slug} to {to_status}: another process moved it first "
        f"({where}). This process did not move it; re-read the item before "
        f"retrying."
    )
```

That is the answer to the request's open design question, and it is five lines.
The loser learns the item's real status and can decide whether to retry —
without a protocol, a lock, or a new error class.

**The message deliberately says "did not move it", not "nothing was changed".**
The latter would be false: by the time `_effect_transition` runs, `transition()`
has already blanked `owner`/`started` (`base.py:1272-1274`) or `complete()` has
already stamped `resolution` (`base.py:1397`). Scoping the claim to the move is
the difference between an accurate error and a new lie.

Litmus test: "could a non-filesystem store report a transition that lost a race
by re-reading the item's current status?" Yes — any store can re-read. The
*guard* lives in the FS adapter because `_find` does, but nothing about the
reported outcome is filesystem-specific, and the error type is the one the
abstract CLI already handles.

### 3. The residual this does *not* fix

Two `complete` calls racing one `review` item with different resolutions — A with
`done`, B with `wontfix` — can leave B's `resolution: wontfix` stamped on the
item A moved into `completed/`. That is a status/resolution disagreement, which
`_status_resolution_problems` (`fs.py:2508-2513`) documents as something "no code
path can produce". This race can produce it, so that docstring is now known to be
optimistic.

Fixing it means reordering or rolling back the pre-move `set_field` — and the
ordering is deliberate, with a comment at `tcw/work/cli.py:915-918` explaining
that a hook evaluated any later would abort after already stamping a resolution.
That is a design change of its own size, not a rider on a `None` guard. It gets a
follow-up item; this spec records the finding rather than smuggling the fix.

## Acceptance criteria

1. `FsWorkStore._effect_transition` raises `ValueError` — not
   `CalledProcessError`, `FileNotFoundError`, or `TypeError` — when `_find`
   returns `None`, and the message names both the slug and the item's re-read
   current status.
2. That error reaches the CLI on stderr with exit code 1 rather than a traceback,
   at each command's *existing* prefix — `tcw work: <message>` for `submit`
   (`work/cli.py:583`) and `rework` (`work/cli.py:605`), `tcw work complete:
   <message>` for `complete` (`work/cli.py:923`). The inconsistent prefix is
   pre-existing and not changed here; the criterion asserts what the code does,
   not what would be tidier.
3. When the guard fires, `_mv` is not called and the item's folder is still where
   the competing process left it. This is a narrow claim on purpose: the guard
   sits directly above `_mv` (`fs.py:2743`), so the test is close to tautological
   and is worth writing only as a regression pin against someone later moving the
   guard below the move. It asserts nothing about `owner`/`started`/`resolution`,
   which criterion 9 covers instead.
4. A test forces `_find` to return `None` deterministically (monkeypatch, as the
   sibling item's test does — not by racing threads), and fails against the
   current code.
5. Each of `fs.py:2005`, `2219`, `2485`, `2804` has a test that drives it with
   `_find` returning `None` and asserts the handled outcome (`ValueError`, a
   reported validation problem, or `None`) rather than an attribute/type error.
6. `grep -n "_find(" tcw/store/fs.py` shows no remaining call whose result is
   dereferenced without either a `None` check or `_require_dir`.
7. The eight collapsed guard sites raise the same exception type and the same
   message as before — `no such work item: <slug>`. The three existing tests that
   assert that text (`tests/test_work.py:1680`, `tests/test_qualified_ref.py:95`,
   `tests/test_store_editor.py:299`) still pass unmodified. They do **not** cover
   all eight sites individually, so the collapse is additionally checked by
   reading the diff — no site gains or loses a `raise`.
8. `MultipleMatch` still propagates from every collapsed site (it is raised
   inside `_find`, above the guard, and callers rely on it — `work/cli.py:451`,
   `474`, `820`).
9. A test pins the *known-unfixed* residual: a lost `complete` leaves its
   `resolution` written. It asserts the current behavior with a comment naming
   the follow-up item, so the next person meets a documented limitation instead
   of rediscovering it as a bug.
10. Full suite green locally and both CI legs green.

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
- **Pre-move `set_field` writes are not rolled back**, and this item makes the
  crash go away without making the data correct (Design §3). The honest framing
  at closeout is "the loser no longer crashes", not "the race is handled" — and
  the follow-up item must exist before this one completes, or the residual is
  lost with the session that found it.
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
