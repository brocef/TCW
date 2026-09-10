# Refined outcome: compose a lifecycle stage into one skill document

**Accepted** on 2026-09-10, verified against `f355e02` on
`feat/stage-gate-and-prompt-verbs`.

## The decision

Accepted with one guard knowingly left weakened and two defects filed rather than
fixed. All three are recorded in the inbox notes named below.

## Evidence

| Check | Result |
| --- | --- |
| `tests/test_skill_lifecycle_parity.py` | 95 passed |
| `tests/test_documented_cli_surface.py`, `tests/test_plugin_manifests.py` | 227 passed |
| `tests/test_stage_verb.py`, `test_shipped_prompts.py`, `test_skill_flow.py` | 79 passed |

The illegal-stage note and the missing-item error were both confirmed by hand:

```
tcw work stage prompt: note — 'plan' is not legal for an item in 'review'; it runs
in backlog. Printing its instructions anyway because you asked to read them, not
to enter the stage.

tcw work stage prompt: no such work item: no-such-item-at-all
```

Criteria 1 through 4 concern what the Claude skill harness renders. The underlying
commands and the `|| true` guards that let the skill survive a non-zero exit were
verified directly; the harness-level render is carried over from this item's own
measurements rather than re-measured, since no headless invocation was re-run.

**Criterion 7's guard bites.** Dropping `Bash(cat *)` from `allowed-tools` fails
`test_the_composing_skill_declares_the_commands_it_injects`. That matters because
the failure it prevents is an invocation that aborts showing the model nothing at
all, which this item's own outcome calls indistinguishable from the skill not
existing.

## Criterion 8 no longer describes the repository

It required that the seven routers keep naming `begin` and that the
harness-neutral parity check stay untouched. Both halves are now false, and both
in the right direction: the routers name `gate` and `prompt`, and the parity check
was rewritten by a later item to require **both** verbs in every stage document.
The criterion's purpose, keeping a route that works under Codex, is preserved and
better enforced than before.

The skill at HEAD names `gate` everywhere and never names the removed verb, which
is correct rather than stale.

Criterion 9's router text was likewise changed by that later item after this one
landed.

## The guard that stopped biting

`test_the_composing_skill_reads_with_prompt_and_names_begin_for_entry` defends the
one hazard this item's plan calls out by name: the composing skill becoming a
documented route around the gate, since it is built on the reading verb. It
asserts only that a literal string appears somewhere in the body.

When this item shipped, that literal occurred once, in the prose warning, so
deleting the warning failed the test. A later item added the same literal to the
manual-fallback code fence, and it now occurs twice. Deleting the entire prose
warning leaves the suite green. Confirmed by mutation.

**Neither item caused this alone.** It is reachable only once both had landed, and
no single-item review could have produced it. Recorded in
`docs/work/inbox/2026-09-10-verification-findings-on-the-stage-verb-branch.md`
with the three-line fix, which strips code fences before asserting so the
requirement becomes that the gate is named in prose. That is preferred over
asserting a count of two, which would pass again if someone added a third fence
and deleted the prose.

The function's own name is stale after the rename and is the only such identifier
left in the test suite.

## Deferred

- The weakened guard above.
- `.codex-plugin/plugin.json` says the plugin ships **eight** skills and names
  each. There are nine, and `tcw-work-stage` — the skill this item added — is not
  among those named. No test checks the count.
- Neither `|| true` is guarded by a test. This item measured two independent
  causes of a silent empty render and guarded only the first. Filed as
  `docs/work/inbox/2026-09-10-untested-skill-guards-and-the-blob-silencing-advice.md`.

## Noted, not defects

The gate command appears four times in a single composed render, and the skill's
own text says it does not repeat that reminder before repeating it three lines
later. Nothing contradicts anything, so this is noise rather than a fault.

`outcome.md`'s criterion 4 row quotes a line telling the reader to run the removed
verb. True for its own commit, stale against HEAD.

## Closeout

- **Merge route:** merged locally into `main`, no pull request.
- **Version:** 2.0.0 offered separately, after all four items complete.
- **Originating issue:** none.
- **Post-mortem:** not run. The weakened guard is a genuine process finding and is
  captured in full in the inbox note instead.
