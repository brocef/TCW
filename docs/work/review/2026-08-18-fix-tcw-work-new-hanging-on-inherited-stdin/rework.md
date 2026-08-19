# Rework — Fix `tcw work new` hanging on inherited stdin

Rejected at `verify`. The delivered work is correct and the reported hang is
gone. What is wrong is that **the item met its goal by shrinking the goal.**

## What must change

**Close the gap Goal 1 was narrowed around.** The original goal — *no `tcw`
invocation blocks indefinitely on a stdin it was not asked to read* — was
rewritten mid-spec to cover only the five intake entry points plus lifecycle
`command:` hooks, because 21 `git` subprocesses inherit stdin and carry no
timeout. That narrowing was recorded honestly and a follow-up was proposed. The
residual is small enough that deferring it costs more in explanation than in
code — though **not** for the reason first given here.

Measured — every `subprocess` call in the three files that shell out, and whether
it constrains stdin:

| File | git calls | Setting `stdin=` |
| ---- | --------- | ---------------- |
| `tcw/store/fs.py` | 19 | **0** |
| `tcw/store/project.py` | 1 | **0** |
| `tcw/work/cli.py` | 1 | **0** |

**The reason this rework first gave was false, and testing it is what found
that out.** The claim was that `git commit` (`fs.py:347`, `:410`) and `git merge`
(`fs.py:484`) run the repository's own hooks, that those hooks inherit fd 0, and
that a `pre-commit` hook reading stdin therefore blocks a transition forever.
Executed, with no TCW involved — a `pre-commit` hook running `cat`, and `git
commit` given a held-open pipe as its stdin:

```
git commit: rc=0 in 0.14s
  hook said: HOOK: drained fd0 and reached EOF
```

**Git closes its hooks' stdin.** The hook saw EOF immediately. A TCW-level probe
agreed: `tcw work start` with a held-open pipe and a `cat` pre-commit hook
completed in 0.28s **both before and after** the fix, so the probe I wrote to
prove the bug does not discriminate — because there is no bug there to catch.

So what is actually true, and what this rework is now for:

- The 21 git subprocesses **do** inherit stdin. That is a fact, not a hang.
- No reachable path turns it into a hang today: git redirects hook stdin, no TCW
  git invocation contacts a remote (so no credential helper can prompt), and none
  takes input on stdin (`-m` is always passed; nothing uses `--file=-`).
- The one case that was never about git at all is real: `tcw serve` spawns a
  long-running **node** process (`serve/runtime.py:169`) that inherited fd 0 and
  would compete with the supervising `tcw serve` for the terminal.

**The honest justification is explicitness, not a fixed hang.** Every process TCW
launches should say what its stdin is, so that the *next* one — a git call that
does reach a remote, a helper that does read input — cannot inherit it silently.
That is a real invariant and it is now enforced by a test rather than by
argument. It is a smaller claim than the one this document opened with.

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
