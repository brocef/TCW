# Rework — Fix `tcw work new` hanging on inherited stdin

Rejected at `verify`. The delivered work is correct and the reported hang is
gone. What is wrong is that **the item met its goal by shrinking the goal.**

## What must change

**Close the gap Goal 1 was narrowed around.** The original goal — *no `tcw`
invocation blocks indefinitely on a stdin it was not asked to read* — was
rewritten mid-spec to cover only the five intake entry points plus lifecycle
`command:` hooks, because 21 `git` subprocesses inherit stdin and carry no
timeout. That narrowing was recorded honestly and a follow-up was proposed, but
review is the right place to say it is not enough: the residual is real, and it
is small enough that deferring it costs more in explanation than in code.

Measured — every `subprocess` call in the three files that shell out, and whether
it constrains stdin:

| File | git calls | Setting `stdin=` |
| ---- | --------- | ---------------- |
| `tcw/store/fs.py` | 19 | **0** |
| `tcw/store/project.py` | 1 | **0** |
| `tcw/work/cli.py` | 1 | **0** |

`git commit` (`fs.py:347`, `:410`) and `git merge` (`fs.py:484`) run the
repository's own hooks, and those hooks inherit fd 0. A `pre-commit` hook that
reads stdin therefore blocks a TCW transition forever — the exact failure this
item exists to remove, one layer down, and *unbounded* because unlike TCW's own
lifecycle hooks these carry no timeout.

**Fix it where every caller routes through.** In `fs.py` every `subprocess`
call is a git call, so one helper covers all nineteen at once; the two remaining
single sites take the argument directly.

**Add the guard that makes the invariant hold for code not yet written.** A test
that asserts every `subprocess.run` / `subprocess.Popen` under `tcw/` passes an
explicit `stdin=`. That is what stops the twenty-second call site from
reintroducing this, and it is stronger than a helper, which anyone can bypass by
calling `subprocess.run` directly.

`tcw/work/generate.py` continues to pass `stdin=subprocess.PIPE` deliberately and
must keep doing so — the guard asserts *explicitness*, not one particular value.

## Scope

- `tcw/store/fs.py`, `tcw/store/project.py`, `tcw/work/cli.py`.
- A guard test over the package.
- `spec.md` — Goal 1 is restored to its full form and the Risks entry that
  recorded the gap becomes a record of it being closed.
- No follow-up item is filed for this any more; it is the rework.

## Also correct in the record

A claim in the spec was false and has already been fixed at `2d7768f`: "a hook
that reads stdin steals the piped intake out from under `work new`". `_new`
(`tcw/work/cli.py:223-253`) runs no hooks at all. The stall is real and in fact
worse than described — it aborts the transition — but the theft was invented.
Noted here so the rework's own record does not repeat it.

## Not in scope

Timeouts on git subprocesses. A hung `git` is a different failure with a
different fix, and bounding every git call is a change with real blast radius —
`git commit` on a large tree is legitimately slow. This rework closes the *stdin*
inheritance only, which is what the item is about.
