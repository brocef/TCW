# 06 — Stdin, pipes, and process boundaries

The area that cannot be tested in-process at all: a parent holding a pipe's write
end open is not reproducible inside one Python process.

## Functionality covered

- Piped text into the four commands that read it: `tcw work new` (the
  request), `tcw work comment` (the comment), `tcw taxonomy add` (the
  description) and `tcw capabilities add` (the body)
- `TCW_STDIN_TIMEOUT`
- Refusal on a truncated read
- Inherited-but-open stdin (the reported hang)
- Every subprocess `tcw` spawns closing its own stdin

## What is tested

| # | Assertion |
| - | --------- |
| 1 | `echo "body" \| tcw work new "Title"` creates the item **and** stores the piped text as its request: `tcw work show <slug>` prints it under `request:`. stdout of `new` is exactly the full slug. |
| 2 | The same for `taxonomy add` (piped description) and `capabilities add` (piped body); each prints exactly the new entry's path on stdout. `taxonomy add` takes its description from stdin only: a second positional argument is a usage error (exit 2). |
| 3 | `tcw work new "Title" </dev/null` creates the item with **no** request (`request: none` in `show`), exit 0. `tcw work comment <slug> </dev/null` is a usage error (exit 2): a comment needs text. |
| 4 | **The reported bug.** `tcw work new "Title"` invoked with a stdin that is an open pipe **nobody ever writes to and nobody closes** completes within a few seconds, exit 0, item created. Measured with a hard `timeout`; a timeout kill is the failure. |
| 5 | The same held-open-pipe invocation prints a note on **stderr** saying it proceeded without input — a silent proceed is indistinguishable from lost input. stdout still carries only the slug. |
| 6 | A producer that is **slow to start** but then writes (`(sleep 1; echo body) \| tcw work new "Title"`) has its text read in full. The bound measures a gap in the stream, not total duration. |
| 7 | A producer that **streams for longer than the timeout** without ever gapping (`for i in 1..20; do echo line; sleep 0.2; done \|`) is read in full. This is the assertion that distinguishes a per-gap bound from a total-duration bound, and it is the one most likely to be got wrong. |
| 8 | A producer that writes a partial document and then **stalls forever** causes a non-zero exit with a message naming `TCW_STDIN_TIMEOUT`, and **creates nothing** — no item folder, no partial artifact. |
| 9 | `TCW_STDIN_TIMEOUT=0` never waits: the held-open pipe case returns immediately with no intake. |
| 10 | `TCW_STDIN_TIMEOUT=10` on a producer that first writes after 3s reads the text (proving the knob raises the bound, not just that it is parsed). |
| 11 | A malformed `TCW_STDIN_TIMEOUT` (`abc`, `-1`) falls back to the default **silently** and still creates the item — a bad environment variable must not break item creation. |
| 12 | Interactive use is unchanged: with a pty (or, if that is too heavy, with stdin bound to `/dev/tty` where available), no intake is read and nothing blocks. If a pty is impractical in the harness, **skip explicitly with a message** rather than pretending to cover it. |
| 13 | Every entry point that reads stdin behaves identically for cases 4 and 8 — the reading is one implementation (`tcw/stdin.py`), and a table-driven loop over all four commands proves it rather than assuming it. |
| 14 | A `post` hook on a stage that reads its own stdin, run by `tcw work advance` with `tcw`'s stdin held open by a pipe, completes promptly: hooks are given no stdin. |

## Refusals asserted

- truncated input creates nothing (8)

## Explicitly not covered here

Timeouts on the read-only `git` calls TCW still makes (finding the repository
root, the uncommitted-changes check). A hung `git` is a different failure and
is out of scope here.

## Notes for the implementer

Assertions 4, 7 and 8 are the whole point of this file and each needs a real
held-open descriptor. The pattern:

```sh
mkfifo "$tmp/pipe"
sleep 30 > "$tmp/pipe" &      # holds the write end open, writes nothing
holder=$!
timeout 10 tcw work new "Title" < "$tmp/pipe"
kill "$holder"
```

Do **not** substitute `< /dev/null` or a closed descriptor anywhere in this file
— every such substitution turns a real test into a tautology. Clean up every
background holder in the `EXIT` trap; a leaked `sleep` outliving the run is a
bug in the test, not a harmless leftover.

Assertion 14 pins that a hook never inherits `tcw`'s stdin. Since TCW 3.0 TCW
changes no git state itself, so a project that records its changes does it in
a hook, and that hook must not be able to stall on a pipe it was handed by
accident.
