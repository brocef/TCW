# Outcome — Fix `tcw work new` hanging on inherited stdin

The hang is gone, at all five intake entry points rather than the one that was
reported, and lifecycle hooks no longer inherit stdin either. The suite is
**1623 passed, 0 failed in 258.72s** — 31 tests more than the 1592 baseline, and
faster than the 284s that baseline took.

## What shipped, task by task

| # | Task | Commit |
| - | ---- | ------ |
| 1 | `tcw/stdin.py` + `tests/test_stdin.py`, wired to nothing | `3a6c1aa` |
| 2 | Five call sites wired, three `_stdin_body` copies deleted, `tests/test_stdin_cli.py` | `df17490` |
| 3 | `command:` hooks run with stdin closed | `5ee3ef8` |
| 4 | `work/capture-raw-intake` capability reconciled | `766e8af` |
| — | Regression fix: in-memory stdin with no descriptor | `d451cbb` |
| 5 | Documentation Sync — six files | `545078e` |

The reported symptom, re-measured against the fixed CLI with the same probe that
produced the spec's table:

| Arm | Before | After |
| --- | ------ | ----- |
| A — inherited open pipe | **hung, killed at 15.01s** | **2.10s, rc=0**, item created, warning on stderr, no intake |
| B — stdin closed | 0.12s, rc=0 | 0.09s, rc=0 |
| C — piped intake | 0.10s, rc=0, `intake` written | 0.10s, rc=0, `intake` written |

## Acceptance criteria

All fifteen met. Criteria 1–13 are covered by `tests/test_stdin.py` (22) and
`tests/test_stdin_cli.py` (9); 14 by
`test_a_descriptor_that_cannot_be_polled_is_not_read_blockingly`; 15 by the suite
run above. Criterion 9's grep is clean: `grep -rn "def _stdin_body" tcw/` returns
nothing.

## What the plan or spec got wrong

Five things, four of which were found by running something rather than reading it.

**1. The spec's rule "never fall back to a blocking read" was too broad, and the
full suite proved it.** `tests/test_work.py::test_cli_new_pipes_stdin_into_intake_not_a_request`
substitutes `sys.stdin` with an `io.StringIO` and calls `main()` in-process. A
descriptor-only helper returns `""` there, and the test failed with
`assert {'state.yaml'} == {'intake.md', 'state.yaml'}` — a genuine regression for
anyone embedding the CLI, not a test artifact. The rule that survives splits the
case the spec had merged: a `sys.stdin` **with** a `fileno()` is an OS stream and
a `select` failure must never become a blocking read; one **without** cannot be
the inherited pipe at all and is read plainly. Fixed in `d451cbb`; the spec, the
plan, and the module docstring now describe what shipped.

This is the one that matters most, because the twenty targeted tests written for
this item all passed while it was broken. The regression was only visible from a
test written for a different purpose two years of commits ago.

**2. Acceptance criterion 14 checked a string, not a property.** It asserted that
`grep -n "sys.stdin.read()" tcw/` returns nothing. It *passes on the shipped
code* — but only because the fallback is spelled `stdin.read()` on a local
variable. It would have kept passing regardless of what the code did. Rewritten
to assert the behavior with a test.

**3. The hook defect was worse than the spec described.** The spec called it "a
stall rather than a hang… bounded, so it is a stall". The failing test showed the
stall **aborts the transition**:

```
tcw work start: start pre hook `cat` exceeded the 5s timeout; 2026-08-18-hooked not started
```

A lifecycle hook could refuse a legitimate transition purely because the caller's
stdin was inherited and open. Same one-keyword fix; a materially worse bug than
the one written down.

**4. The Documentation Sync entry is a pattern, and the plan read it as one
file.** `skills/<component>/SKILL.md` covers all three components. The plan named
only `tcw-work`, reasoning from the reported bug rather than the shipped fix —
but the fix touches all five intake entry points, and
`skills/tcw-taxonomy/SKILL.md:63` and
`skills/tcw-capabilities/references/init.md:27` both instruct piping on stdin.
Caught at the gate by re-reading the entry instead of the plan's summary of it.
Both updated; `plan.md` corrected.

**5. Two CLI facts were wrong in the spec and only failed when tested.**
`tcw taxonomy add` takes `description` as a **positional**, not `--description` —
the test failed against the real parser with `unrecognized arguments`. And the
spec's Problem section claimed `tcw work init` "does not exist"; it does, and the
original probe had failed for want of `--id`. Both corrected.

## Notes

- **The item is in `active` one stage early, and this is the record of it.**
  `tcw work start` was run before `spec` was written; both `spec` and `plan` are
  legal only in `backlog`, and `tcw work stage` refused accordingly. There is no
  reverse transition and hand-moving the folder is forbidden, so both artifacts
  were written with the stage instructions composed manually — obtained by
  running `tcw work stage <stage>` against a sibling item that was legitimately
  in `backlog`, which resolves the same node-level bindings. Content unaffected;
  sequencing wrong.
- **Follow-up to file at completion:** roughly twenty `subprocess.run` calls to
  `git` (`tcw/store/fs.py:288, 293, 298, 323, 327, 328, 347, …`,
  `tcw/work/cli.py:541`) inherit stdin and carry no timeout. None contacts a
  remote, so no credential helper can prompt; the live exposure is a user's own
  git hook reading stdin during `git commit`. Out of scope by the narrowed
  Goal 1, and closing it means touching every git call site.
- **Unmeasured, and named as such:** the 2.0s default is a judgment. Nothing in
  this item measured what real pipelines need. `TCW_STDIN_TIMEOUT` exists so the
  number can move without a release.
- **Reviewed by `codex`; `bllm-review` produced nothing** — it waited 1440s on a
  workload lock and gave up, exiting `0` with no review. Filed to
  `/Users/brian/llama/docs/work/inbox/` per the user's standing instruction: an
  exit code of `0` for "never ran" is indistinguishable from "clean" to any
  caller that gates on it.
- The v1.0.0 fold gate was re-run against the network at the close of
  implementation: `STATUS: FOLDABLE`, exit `0` — the tag is still absent from
  `origin`, so this work can still join it.
