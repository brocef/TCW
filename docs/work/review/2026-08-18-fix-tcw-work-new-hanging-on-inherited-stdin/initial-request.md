# Fix `tcw work new` hanging on inherited stdin

`tcw` must never block waiting for end-of-input on a stdin it was not asked to
read. Today it may, and the place it was observed is `tcw work new`.

## What was seen

A script driving `tcw` through `subprocess.run(...)` without setting `stdin`
timed out after 120 seconds. It made roughly fifteen `tcw` calls, each of which
completes in under a second by hand, so it should have finished in well under
thirty. The first `tcw work new` call is where it appeared to stop.

**This is an observation, not a diagnosis.** It was inferred from ordering, not
watched directly, and no per-call timing was captured. The hypothesis is that
v1.0.0's piped-intake feature reads stdin whenever stdin is not a TTY, rather
than only when it is a pipe carrying data — which would make a caller that
inherits an open stdin (a subprocess, a CI runner, a hook) wait forever for an
EOF nobody will send.

Nothing here is established. That the block is in `tcw work new`, that stdin is
the cause at all, and that closing stdin avoids it are all open. A comparison run
meant to settle the last one was made from the wrong working directory and
returned `rc=1` for both arms, measuring nothing.

## What is being asked for

Two things, in order.

First, **settle whether the hypothesis is true**, with evidence rather than
inference: a per-call timeout, a real node, one arm with stdin inherited and
open, one arm with stdin closed. If neither arm hangs, the hypothesis is wrong
and this item should be closed saying so rather than left open.

Second, **if it holds, make `tcw` automation-safe by default.** No invocation may
block waiting for EOF on stdin it did not ask for.

## Constraints

- Interactive use must keep working unchanged.
- `echo "…" | tcw work new "…"` must keep working — piped intake is a real
  feature and the ask is not to remove it.
- The failure mode this exists to kill is a *hang*, not an error. An invocation
  that cannot get its intake should fail or proceed, never wait.

## Out of scope

How to achieve it. Reading stdin only when it is a ready pipe, requiring an
explicit flag, or something else entirely are alternatives for `spec` to weigh —
naming one here would hide the others.

## Notes

Why it matters more than its size suggests: `tcw work new` is the entry point
every automated intake path goes through, and TCW's own test suite builds
scratch nodes by shelling out to it. A hang there is worse than an error — it
reads as slowness, and it strands CI.

Reference material: asked; none provided. The requester considers the repository
itself sufficient.
