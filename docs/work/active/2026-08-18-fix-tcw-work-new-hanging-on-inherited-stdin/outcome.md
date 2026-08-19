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

---

# Rework outcome — closing the inherited-stdin gap

Rejected at `verify` for meeting Goal 1 by shrinking it. The gap is now closed.
`rework.md` holds the analysis; this records what shipped.

## What changed — `8d69daa`

| File | Change |
| ---- | ------ |
| `tcw/store/fs.py` | New `_git()` helper defaulting `stdin=DEVNULL`; all **19** git calls in the module routed through it |
| `tcw/store/project.py` | `_probe_worktree`'s `rev-parse` — inline `stdin=DEVNULL` |
| `tcw/work/cli.py` | `_start`'s `git config --get` probe — inline |
| `tcw/serve/__init__.py` | `_open_locator`'s desktop-opener `Popen` |
| `tcw/serve/runtime.py` | `node --version`, and the **node server `Popen`** |
| `tests/test_subprocess_stdin.py` | New: AST walk over every module under `tcw/`, failing any `subprocess` spawn without an explicit `stdin=` |
| `tests/test_serve.py` | Three `Popen` stubs took one positional; they now accept kwargs, and the opener test asserts `stdin=DEVNULL` |

25 lines of source, 24 tests. Suites re-run: 205 pass across
`test_serve.py` + `test_work.py` + `test_repo_lifecycle.py`; 55 across the three
stdin suites.

## The justification changed, and that matters more than the diff

The rework was authorised on a premise I had not executed: that a repository
`pre-commit` hook reading stdin would block a transition forever. **It is
false.** Git redirects its hooks' stdin — measured directly, hook running `cat`,
`git commit` handed a held-open pipe:

```
git commit: rc=0 in 0.14s
  hook said: HOOK: drained fd0 and reached EOF
```

A TCW-level probe agreed: `tcw work start` completed in 0.28s **both before and
after** the fix. The probe written to prove the bug does not discriminate,
because there is no bug on that path. Surfaced to the user, who chose to keep
the change on the corrected justification.

So what the 21 git changes actually buy: **explicitness, enforced by a test.**
No reachable hang existed on them — git closes hook stdin, no TCW git call
reaches a remote, none takes input on stdin. The invariant is still worth
holding for the *next* call site, and a test holds it better than a helper
anyone can bypass.

**The guard test is the part that paid for itself.** It found three `tcw serve`
spawns neither review had looked at, one of which is a genuine defect and was
never about git: `serve/runtime.py:169` launches a long-running node server that
inherited fd 0 and competed with the supervising `tcw serve` for the terminal.

## Second false premise in this item

This is the second argument in this work item built on an untested failure
story — the first was the spec's "a hook steals the piped intake out from under
`work new`" (corrected at `2d7768f`; `_new` runs no hooks at all). Both were
plausible mechanisms; both dissolved on execution. Recorded here rather than in
the post-mortem because it is a pattern within one item, not across the release.

## Still open, deliberately

Timeouts on git subprocesses. A hung `git` is a different failure with a
different fix, and bounding every git call is a change with real blast radius —
`git commit` on a large tree is legitimately slow. Not filed as a follow-up
either: nothing has been observed to hang, and a speculative item is backlog
weight. If it is ever seen, the fix has one obvious home now — `_git()`.
