# Spec — Fix `tcw work new` hanging on inherited stdin

## Capability changes

**Changed.** `work/capture-raw-intake` (`docs/capabilities/work/capture-raw-intake/`)
gains one sentence: piping intake keeps working, and an invocation whose stdin
carries nothing proceeds without intake instead of waiting forever. No new
capability record — nothing new becomes possible; a thing that could hang stops
hanging. No records are written at this stage; the ledger is reconciled at
completion.

## Problem

### The hypothesis is true, and was measured rather than inferred

The initial request stated the hang as an observation and asked for evidence.
Three arms of `tcw work new`, per-call timeout of 15s, against a real scratch
node created with `tcw init --id … work`. The first attempt at this measurement
reproduced the original failure: every arm returned `rc=1` before reaching any
stdin code, because the node was never created — `tcw work init` exists, but it
refuses without `--id`, and the arms were measuring that refusal rather than
stdin. Only once all three arms reached real code did the difference appear:

| Arm | stdin | Result |
| --- | ----- | ------ |
| A | an `os.pipe()` read end the parent holds open and never writes to | **hung — killed at 15.01s**, no stdout, no stderr |
| B | `subprocess.DEVNULL` | completed in 0.12s, rc=0, item created |
| C | `input="raw intake body\n"` | completed in 0.10s, rc=0, item created **with `intake`** |

Arm A is the automation case: a subprocess, a CI runner, or a hook that inherits
an open stdin nobody will ever close. Arm C is the feature that must survive.

### The cause, and it is not confined to `tcw work new`

`tcw/work/cli.py:96-101`:

```python
def _stdin_body() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""
```

`isatty()` false is read as "a pipe carrying data". It actually means *anything
that is not a terminal* — a pipe with data, a pipe with no data and no writer
intending to close it, a socket, a file. `sys.stdin.read()` then blocks until
EOF, and in arm A no EOF is ever sent.

**The sweep is repo-wide, and it found the same function twice more.** It is
copied verbatim into two sibling CLIs, so the defect is three defects:

| Site | Consumed by |
| ---- | ----------- |
| `tcw/work/cli.py:96` | `work new` (`:230`), `work delegate` (`:187`), `work escalate` (`:202`) |
| `tcw/taxonomy/cli.py:28` | `taxonomy add` (`:78`) |
| `tcw/capabilities/cli.py:34` | `capabilities add` (`:99`) |

Five entry points, one bug, three copies. Fixing only the reported one leaves
four callers still able to strand a script.

`taxonomy add` is the one partial exception: it reads
`args.description or _stdin_body()` (`tcw/taxonomy/cli.py:78`), and Python's
`or` short-circuits, so `--description` given on the command line means stdin is
never touched. It hangs only when the description is omitted. The other four
call `_stdin_body()` unconditionally.

The sweep also confirms what is **not** there: `grep -rn "\binput(\|getpass\|
readline()" tcw/ --include=*.py` returns nothing, so no interactive prompt exists
anywhere in the package. Stdin is the only blocking-read surface.

### One sibling from the same sweep

`tcw/work/hooks.py:61-63` runs a project's `command:` bindings with
`subprocess.run(..., capture_output=True, text=True, timeout=timeout)` and no
`stdin=`, so every hook **inherits the parent's stdin**. Two consequences: a
hook that reads stdin steals the piped intake out from under `work new`, and a
hook that blocks on it stalls for the full hook timeout. It is bounded, so it is
a stall rather than a hang — but it is the same rule being broken (*read only the
stdin you asked for*) and the fix is one keyword argument.

`tcw/work/generate.py:107-111` is **not** in scope and must not be changed: it
passes `stdin=subprocess.PIPE` deliberately and writes the payload, which is the
`generate:` contract. Every other `subprocess.run` in the package invokes `git`
with non-interactive arguments; none reads stdin.

## Goals

1. No `tcw` invocation blocks indefinitely on a stdin it was not asked to read.
2. `echo "…" | tcw work new "…"` keeps working, byte-for-byte, including when the
   producer is slow to start.
3. Interactive use is unchanged.
4. When intake cannot be obtained, the invocation **proceeds and says so** —
   never waits, and never silently discards input a user believes was piped.
5. The bound is tunable, because no fixed number is right for both a local
   `echo` and a network-fed pipe.
6. All five entry points are fixed through one implementation, not five.

## Non-goals

- Removing or flag-gating piped intake. The request names it a real feature.
- Changing what intake *is*, where it is stored, or how `intake` is rendered.
- `tcw serve`, which blocks by design.
- The `generate:` hook payload protocol.
- Windows support, which this repository does not currently claim
  (`pyproject.toml` declares no OS classifiers and no platform-specific code
  exists). The design degrades to today's behavior there rather than breaking.

## Design

### One helper, in one new module

A new `tcw/stdin.py` exporting `read_piped_stdin() -> str`. It cannot live in
`tcw/cli.py`, which imports all three component CLIs (`tcw/cli.py:12-18`) and
would create an import cycle; it does not belong in `tcw/store/base.py`, which is
the storage-abstracted model and has no business knowing the process has a
stdin. The three `_stdin_body` copies are deleted and their five call sites call
the shared helper.

### Bounded readiness, not a bare blocking read

```python
if sys.stdin.isatty():
    return ""                       # unchanged: a terminal is never intake
fd = sys.stdin.fileno()             # ValueError under pytest capture → ""
chunks = bytearray()
while True:
    if not select.select([fd], [], [], timeout)[0]:
        if not chunks:              # waited, got nothing at all
            warn_that_nothing_arrived()
        break                       # bounded either way: never wait twice over
    block = os.read(fd, 65536)
    if not block:                   # EOF — the normal end
        break
    chunks += block
return chunks.decode("utf-8", "replace")
```

**The `if not chunks` guard is load-bearing and was found by running the loop,
not by reading it.** A first draft used `while select(...): … else: warn`, whose
`else` fires on *any* timeout exit — including the measured case "writer sent a
line and then held the pipe open", which yields `expired=True` **with** data. That
draft would have warned "no piped input" at a command that had just read a full
intake. The rule is: warn only when nothing at all arrived.

Why each piece:

- **`select` before every read**, not once. A single up-front poll would race a
  producer that has not written its first byte yet, and would silently drop the
  intake of `gh issue view … | tcw work new …`. Polling per chunk means the
  timeout measures a *gap in the stream*, not the total duration: a producer that
  streams for a minute with sub-timeout gaps is read in full.
- **`os.read` on the raw fd, not `sys.stdin.read(n)`.** The buffered text reader
  may block trying to fill its request; the raw read returns what is there.
  Bytes are accumulated and decoded once at the end, so a multi-byte character
  split across a chunk boundary is not corrupted.
- **`errors="replace"`.** Intake is user text of unknown provenance; a stray byte
  must not turn a work item into a traceback.
- **EOF ends the loop immediately**, so arm B and arm C keep their present
  sub-second timings. The timeout is only ever paid by arm A.

### The loop was executed against every stdin shape, not reasoned about

Measured with a 0.5s timeout so the probe is quick; `expired` is the flag that
gates the warning:

| stdin | Result | Elapsed |
| ----- | ------ | ------- |
| regular file (always "ready" to `select`) | `'file body\n'`, `expired=False` | 0.00s |
| `/dev/null` | `''`, `expired=False` | 0.00s |
| pipe, data then writer closes | `'piped body\n'`, `expired=False` | 0.00s |
| **pipe held open, no data** | `''`, `expired=True` | 0.51s |
| **pipe, data then held open** | `'data then silence\n'`, `expired=True` | 0.51s |
| slow producer, gap under the bound | `'slow body\n'`, `expired=False` | 0.26s |
| three chunks, **total 0.91s > 0.5s bound** | all three chunks, `expired=False` | 0.91s |
| UTF-8 sequence split across two writes | `'héllo wörld ✓\n'` intact | 0.06s |
| socketpair | `'sock body\n'`, `expired=False` | 0.00s |
| closed fd | raises `OSError` (EBADF) | — |
| pytest's captured stdin | `fileno()` raises `ValueError` | — |

Three of these settle open questions. A **regular file** as stdin is read to EOF
and never stalls, so redirecting a file in still works. The **chunked** row is the
per-gap argument holding under measurement: 0.91s of total duration against a
0.5s bound, and nothing dropped. The **closed fd** and **pytest** rows are why
both `OSError` and `ValueError` must be caught rather than one of them.

### The bound, and the knob

Default **2.0 seconds**, overridden by `TCW_STDIN_TIMEOUT` (seconds, float; `0`
means never wait). A value that is unparseable or negative falls back to the
default rather than failing the command — a malformed environment variable must
not break item creation.

No single number is correct. Two seconds is far longer than any local pipe needs
and short enough that a script making fifteen calls loses thirty seconds instead
of hanging forever. A network-fed producer that needs longer sets the variable,
and it learns that it needs to because of the next paragraph.

### Expiry is loud

When the wait expires with nothing read, the command writes to **stderr**:

```
tcw: no piped input after 2.0s — proceeding without intake
     (close stdin, or set TCW_STDIN_TIMEOUT to wait longer)
```

and proceeds normally. This is the part that makes a bounded read safe: without
it, shortening an infinite wait to a finite one converts a visible hang into
silent data loss, which is a worse bug than the one being fixed. Nothing is
written to stdout, so `slug=$(tcw work new …)` is unaffected.

The warning fires only on expiry — never for a terminal, never on EOF, never
when any byte was read — so an interactive user and a normal pipe never see it.

### Hooks stop inheriting stdin

`tcw/work/hooks.py:61` gains `stdin=subprocess.DEVNULL`. A hook that reads stdin
now sees EOF instead of the parent's pipe.

### Abstraction litmus test

| Operation | Verdict |
| --------- | ------- |
| Read piped intake from the process's stdin | **Neither — it is not a store operation at all.** It happens in the CLI layer before any store is constructed, and the string it produces is passed to the existing `intake=` parameter. No store interface changes, no adapter learns anything new. A Jira-backed node's `tcw work new` reads its stdin exactly the same way. |
| Run a hook with stdin closed | **Filesystem-adapter-free CLI detail**, same as the timeout already applied there. |

Nothing here is a filesystem trick, and nothing here is reachable from the model.

### Harness compatibility

Entirely inside the `tcw` CLI, which is the layer the harness rule names as the
only place a guarantee can live. Claude and Codex both get it; neither has to do
anything.

## Acceptance criteria

Arms below mean the three from the Problem section, re-run as tests.

1. **Arm A no longer hangs.** `tcw work new "<title>"` with stdin an `os.pipe()`
   read end the parent holds open exits 0 within `timeout + 5s`, creates the
   item, writes **no** intake artifact, and prints the expiry warning on stderr.
   Asserted for all three real verbs: `tcw work new`, `tcw taxonomy add`
   (without `--description`, since it short-circuits), and
   `tcw capabilities add` — each creating its own kind of record, not an item.
2. **Arm C is unchanged.** `echo "raw intake body" | tcw work new "<t>"` writes
   `intake` containing exactly `raw intake body\n`, exits 0, in under 1s.
3. **A slow producer is not dropped.** A writer that sleeps 1s (under the 2.0s
   default) before writing still delivers its full body to `intake`.
4. **A chunked producer past the total-duration mark is not dropped.** A writer
   emitting three chunks 1s apart — 3s total, over the 2.0s bound — delivers all
   three, proving the timeout measures a gap and not a duration.
5. **Arm B is unchanged.** `stdin=DEVNULL` exits 0 in under 1s, no intake, and
   **no** warning on stderr.
6. **A terminal is never read.** With `isatty()` true, `read_piped_stdin`
   returns `""` without touching the fd. Asserted directly on the helper.
7. **`TCW_STDIN_TIMEOUT=0`** makes arm A return in well under 1s.
   **`TCW_STDIN_TIMEOUT=abc`** and `=-1` behave as the 2.0s default and do not
   raise.
8. **Multi-byte text survives chunking.** A body split mid-UTF-8-sequence across
   two writes arrives intact.
9. **One implementation.** `grep -rn "def _stdin_body" tcw/` returns nothing, and
   every one of the five call sites listed in Problem calls the shared helper.
10. **Hooks do not inherit stdin.** A `command:` binding of `cat` on a node runs
    to completion without consuming piped intake and without stalling to the hook
    timeout.
11. **Nothing reaches stdout on the warning path**, so `$(tcw work new …)`
    captures only the slug.
12. **`taxonomy add --description "x"` never reads stdin at all**, and so cannot
    expire or warn even with stdin held open — the short-circuit is preserved.
13. **The suite does not get slower.** `python -m pytest -q` reports ≥ 1592
    passed, 0 failed, and its wall-clock stays within 10% of the 284s measured on
    this tree today. Several tests spawn `tcw` as a real subprocess without
    setting `stdin=` (`tests/test_scaffold.py:40`,
    `tests/test_lifecycle_baseline.py:30,40`,
    `tests/test_documented_cli_surface.py:99`), so if any of them started paying
    the timeout the run would visibly lengthen. Under pytest's default fd capture
    those subprocesses inherit `/dev/null` and hit EOF at once; the timing check
    is what proves that rather than assuming it.

## Risks

- **A bounded read can silently drop a genuinely slow producer.** This is the
  risk the whole design turns on, and it is why the timeout is a per-gap poll
  rather than a total, why expiry is announced on stderr, and why the bound is
  tunable. It is reduced, not eliminated: a producer whose *first* byte is more
  than `TCW_STDIN_TIMEOUT` away still loses its intake. Accepted, because the
  alternative is the hang, and the user is told.
- **Two seconds is a judgment, not a measurement.** Named ceiling: if a real
  workflow is found that needs longer by default, the number moves — the knob
  exists so that does not require a release.
- **`select` on a non-socket fd is POSIX-only.** On a platform where it raises,
  the helper falls back to today's `sys.stdin.read()`, so behavior there is
  exactly what ships now, including the hang. Deliberate: this repository does
  not claim Windows support, and pretending to fix it there untested would be
  worse than leaving it.
- **Mixing `os.read(0, …)` with `sys.stdin`.** Correct only because nothing reads
  `sys.stdin` before the helper; if a future caller reads it first, buffered
  bytes would be lost. The helper is called once, at the top of a command.
- **The stderr warning is new output.** Any caller asserting on exact stderr for
  an empty-stdin invocation sees one more line. The suite is the check.

## Notes

- The measurement is reproducible:
  `/private/tmp/claude-501/-Users-brian-Projects-TCW/2c522064-e54a-48d2-8072-1ff5efdfa137/scratchpad/stdin_probe.py`.
  It is scratch, not shipped; criteria 1–5 are its arms turned into tests that
  live in the repository.
- The request asked that the item be closed as not-a-bug if the hypothesis did
  not hold. It held, so it is not closed.
- `tcw/work/generate.py:12` already documents this exact hazard from the other
  side — "a script that exits without reading stdin makes the parent's write
  raise" — which is why that file is the one place stdin handling was thought
  through, and the three CLI copies were not.
- Every `file:line` above was re-resolved against the tree while writing this,
  and again during self-review. The self-review pass corrected four things the
  first draft got wrong, all recorded above rather than quietly fixed: the claim
  that `tcw work init` does not exist (it does; it refuses without `--id`), the
  verb name `taxonomy new` (it is `taxonomy add`), the `while/else` warning gate
  (it misfires on data-then-held-open), and the missing note that
  `taxonomy add --description` short-circuits past stdin entirely.
- The suite baseline is **exactly 1592 passed in 284s**, measured on this tree
  today, not carried over from the previous item's `outcome.md`. Criterion 13's
  "≥ 1592" therefore means "no test was lost", which is its purpose.
