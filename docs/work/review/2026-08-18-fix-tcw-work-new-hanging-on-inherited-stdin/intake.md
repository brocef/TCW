## Inbox manifest

- `tcw-work-new-may-block-reading-stdin-unverified.md`

## Inbox body

# `tcw work new` may block reading stdin when stdin is neither a TTY nor closed

**Unverified.** The investigation was cut short, so this is an observation with a
plausible cause attached, not a diagnosis. Treat the cause as a hypothesis to
test, not a finding to fix.

## What was observed

A script driving `tcw` through `subprocess.run(...)` without setting `stdin`
timed out after 120 seconds. The script made roughly fifteen `tcw` calls, each
of which takes under a second when run by hand, so it should have finished in
well under thirty. The first `tcw work new` call is where it appeared to stop.

## The hypothesis

v1.0.0 made `tcw work new` read piped stdin into `intake.md`. If the
implementation reads stdin whenever it is not a TTY — rather than only when it is
a pipe with data, or only when explicitly asked — then a caller that inherits an
open stdin (a subprocess, a CI runner, a hook) blocks forever waiting for EOF on
input nobody is going to send.

That would make the failure mode: `tcw work new` is safe interactively and safe
with `echo … |`, and hangs in exactly the automation contexts where a hang is
worst.

## What was NOT established

- That `tcw work new` is where it actually blocked. It was inferred from
  ordering, not observed directly.
- That the cause is stdin at all. The timeout killed the whole compound command,
  and no per-call timing was captured.
- Whether `stdin=subprocess.DEVNULL` fixes it. A comparison run was attempted
  from the wrong working directory and returned `rc=1` for both arms, which
  measured nothing.

## How to check it properly

Run `tcw work new` in a real node with stdin held open and nothing written to it,
with a per-call timeout, and compare against the same call with stdin closed:

```python
subprocess.run(["tcw", "work", "new", "x"], cwd=node, timeout=8)                     # inherited
subprocess.run(["tcw", "work", "new", "y"], cwd=node, timeout=8, stdin=DEVNULL)      # closed
```

If the first hangs and the second does not, the hypothesis holds and the fix is
to read stdin only when it is a pipe that is ready, or to require an explicit
flag. If neither hangs, this entry is wrong and should be discarded — say so
rather than leaving it open.

## Why it would matter

`tcw work new` is the entry point every automated intake path goes through, and
TCW's own test suite builds scratch nodes by shelling out to it. A hang there is
worse than an error: it looks like slowness, and it strands CI.
