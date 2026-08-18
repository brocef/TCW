# Plan — Fix `tcw work new` hanging on inherited stdin

Five tasks. The ordering constraint is that **the helper and its tests exist and
pass before anything is wired to it**: the helper is where all three outcomes are
decided, and wiring five call sites to an unproven helper turns one failure into
five. The suite is green at every commit boundary — task 1 adds a module nothing
calls yet, which is green by construction.

## Tasks

### 1. `tcw/stdin.py` and its tests, wired to nothing

**Creates:** `tcw/stdin.py`, `tests/test_stdin.py`
**Modifies:** nothing

`read_piped_stdin(timeout: float | None = None) -> str`, plus
`StdinTruncated(ValueError)`.

The loop is the spec's: `isatty()` → `""`; otherwise `select`-gated
`os.read(fd, 65536)` until EOF, accumulating bytes and decoding once with
`errors="replace"`. Three endings, per the spec's table:

| Ending | Behavior |
| ------ | -------- |
| EOF | return the text, silently |
| timeout, `not chunks` | warn on stderr, return `""` |
| timeout, `chunks` | **raise `StdinTruncated`**, naming bytes received and `TCW_STDIN_TIMEOUT` |

**`StdinTruncated` subclasses `ValueError` deliberately, and that choice is what
keeps this task from spreading into the five call sites.** Every one of them
already sits inside a `try` that catches `ValueError`:
`tcw/work/cli.py:40` (`_ERRORS = (ValueError, …)`) covers `new`, `delegate` and
`escalate`; `tcw/taxonomy/cli.py:79` catches `ValueError`;
`tcw/capabilities/cli.py:100` catches `(ValueError, RefError)`. So truncation
already exits 1 with the right `tcw <command>:` prefix and creates nothing, with
**no new error-handling code anywhere**. Verified by reading all five, not
assumed.

Timeout resolution: `TCW_STDIN_TIMEOUT` if set and parseable as a non-negative
float, else `2.0`. Unparseable or negative falls back to the default silently —
a malformed environment variable must not break item creation.

Every exception path returns `""` (`OSError`, `ValueError` from `isatty`,
`fileno`, `select`, `os.read`). **No fallback to `sys.stdin.read()`** — a
fallback that reintroduces the hang is not a fallback.

The docstring states the fd-0 exclusivity contract: call before anything touches
`sys.stdin`; do not read `sys.stdin` after.

`tests/test_stdin.py` drives real file descriptors — `os.pipe`, `os.devnull`, a
temp file, `socket.socketpair` — covering every row of the spec's measured table
plus the three endings. Acceptance criteria 3, 4, 6, 7, 8, and the helper half of
2 and 5.

**Proves it:** the new test file passes; the rest of the suite is untouched at
1592.

**Commit:** `feat: add a bounded, non-blocking stdin reader`

### 2. Wire the five call sites; delete the three copies

**Modifies:** `tcw/work/cli.py`, `tcw/taxonomy/cli.py`, `tcw/capabilities/cli.py`
**Creates:** `tests/test_stdin_cli.py`

Delete `_stdin_body` from all three modules (`tcw/work/cli.py:96`,
`tcw/taxonomy/cli.py:28`, `tcw/capabilities/cli.py:34`) and point their five
callers at `read_piped_stdin` — `work new` (`:230`), `work delegate` (`:187`),
`work escalate` (`:202`), `taxonomy add` (`:78`), `capabilities add` (`:99`).

`taxonomy add` keeps `args.description or read_piped_stdin()` exactly as it is
(`description` is a positional argument, not a flag):
the short-circuit is a feature, and preserving it is acceptance criterion 12.

`tests/test_stdin_cli.py` runs the real CLI as a subprocess against a real
scratch node — the only way to exercise an inherited-and-open fd 0, which
in-process `main([...])` cannot reproduce. Arms A, B, C plus the truncation arm,
for `tcw work new`, `tcw taxonomy add`, and `tcw capabilities add`.

Process-level assertions use a 30s deadline as a **hang tripwire only**; the real
timing assertions live on the helper in task 1, because a full CLI invocation
also does filesystem and git work this design does not govern.

**Proves it:** acceptance criteria 1, 2, 5, 9, 11, 12, 13.

**Commit:** `fix: never block on an inherited stdin in the five intake commands`

### 3. Hooks stop inheriting stdin

**Modifies:** `tcw/work/hooks.py`, `tests/test_lifecycle_hooks.py`

`subprocess.run` at `tcw/work/hooks.py:61-63` gains `stdin=subprocess.DEVNULL`.
`tcw/work/generate.py` is **not** touched: its `Popen` at `:107-111` owns
`stdin=subprocess.PIPE` and writes the payload, which is the `generate:`
contract.

A test binds a `command:` hook of `cat` and asserts it completes without
consuming piped intake and without stalling to the hook timeout.

**Proves it:** acceptance criterion 10.

**Commit:** `fix: run lifecycle command hooks with stdin closed`

### 4. Reconcile the capability record

**Modifies:** `docs/capabilities/work/capture-raw-intake/`

The spec declares one **Changed** capability. Its body currently promises piped
text "lands in `intake.md` verbatim" and says nothing about what happens when
stdin carries nothing or stalls. Add: an invocation with nothing piped proceeds
without intake rather than waiting; a stream that stalls mid-way is refused
rather than stored truncated, because a fragment stored as a verbatim artifact
would break the promise the rest of the sentence makes.

Done through `tcw capabilities`, not by hand-editing the store.

**Proves it:** `tcw capabilities check` and `tcw capabilities drift` stay clean;
the `complete` transition's capability-reconciliation gate passes.

**Commit:** `docs: record the intake capability's stdin behavior`

### 5. Documentation Sync

Evaluated against this repo's four entries. All four fire:

| Entry | Trigger | Fires? | Why |
| ----- | ------- | ------ | --- |
| `README.md` | Public-API | **Yes** | New user-facing environment variable `TCW_STDIN_TIMEOUT`, and a new failure mode (truncated intake is refused). Both are things a user must be able to look up. |
| `docs/release-notes/upcoming.md` | Public-API | **Yes** | A hang that stranded automation is fixed — the most user-visible kind of change there is. Plain language: no `select`, no file descriptors. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **Yes** | Behavior-affecting code in `tcw/`. Grouped Fixed (the hang, the hook stdin inheritance) and Added (the environment variable). |
| `skills/tcw-work/SKILL.md` | Skill-Driven-Component | **Yes** | The work component's intake guardrails change. The concrete edit is `skills/tcw-work/references/commands.md:42-43`, which today tells an agent how piped intake behaves and would be wrong afterwards. |

The fourth is the one worth stating explicitly, because the entry names
`SKILL.md` while the stale text is in a `references/` file the skill routes to.
The trigger is about the skill drifting from the tool, so the reference counts.

**Modifies:** `README.md`, `docs/release-notes/upcoming.md`,
`docs/changelogs/upcoming.md`, `skills/tcw-work/references/commands.md`

**Commit:** `docs: README, release notes, changelog and skill for stdin handling`

## Verification

Beyond the suite:

1. **The original reproduction, re-run.** The scratch probe that produced the
   spec's three-arm table is run again against the fixed CLI. Arm A must now
   complete rather than being killed at 15s. This is the only check that closes
   the loop on the reported symptom rather than on a test written from the same
   understanding that produced the fix.
2. **The suite's wall clock.** Several tests spawn `tcw` as a subprocess without
   setting `stdin=` (`tests/test_scaffold.py:40`,
   `tests/test_lifecycle_baseline.py:30,40`,
   `tests/test_documented_cli_surface.py:99`). If any started paying the 2s
   timeout the run would visibly lengthen. Baseline is **1592 passed in ~284s**,
   measured on this tree today; a run beyond ~310s means something regressed even
   if every test passes.
3. **Whether 2.0s is a defensible default** — no test can answer it. Judged by
   running the fixed CLI by hand in a normal shell pipeline and confirming no
   perceptible delay on the paths that hit EOF immediately.
4. **Full suite:** ≥ 1592 passed, 0 failed. Once, at the end.

## Notes

- **The item is in `active` one stage early.** `tcw work start` was run before
  `spec`, and both `spec` and `plan` are legal only in `backlog`
  (`tcw work stage` refuses: "'spec' is not legal for an item in 'active'").
  There is no reverse transition, and hand-moving the folder is exactly what
  `AGENTS.md` forbids. Both artifacts were therefore written with the stage
  instructions composed manually from `tcw work stage <stage>` run against a
  sibling item in `backlog`, which resolves the same node-level bindings. The
  content is unaffected; the sequencing error is recorded here and belongs in
  `outcome.md` rather than being tidied away.
- No `--blocked-by` links: every dependency is between tasks inside this item.
- Self-review against the spec: criteria 1, 2, 5, 9, 11, 12, 13 → task 2;
  3, 4, 6, 7, 8 → task 1; 10 → task 3; 14 → task 1 (asserted by grep after the
  helper exists) and re-checked in task 2 once the copies are deleted; 15 →
  Verification 2 and 4. Every task traces back: 1→c3/c4/c6/c7/c8/c14,
  2→c1/c2/c5/c9/c11/c12/c13, 3→c10, 4→the capability gate at `complete`, 5→the
  Documentation Sync gate.
- The follow-up the spec's Risks names — ~20 git subprocesses that inherit stdin
  and carry no timeout — is **not** a task here. It is filed as a new work item
  at completion, because closing it means touching every git call site and that
  is a different change with a different blast radius.
