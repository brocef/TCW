# Refined outcome

**Accepted.** The user approved the work and directed closeout on 2026-09-17.

## The decision

TCW no longer tells an agent to volunteer a version cut when a work item
completes. Cutting a version still works exactly as it did; it now happens
because the user asked for it. That was the whole request: the offer fired on
essentially every completion, and the user was dismissing it every time.

## Evidence

Every acceptance criterion in `spec.md` was run against this checkout. All nine
pass.

| # | Criterion | Result |
| - | --------- | ------ |
| 1 | No offer instruction in shipped text | grep returns nothing; was 14 matches |
| 2 | Gone from sites the first pattern cannot reach | `version cut` matches only under `skills/documentation-sync/` and the renamed heading |
| 3 | `version offered` gone from every live checklist | no matches |
| 4 | Built-in Definition of Done has four items | `('tests pass', 'docs synced', 'capabilities reconciled', 'reviewed')` |
| 5 | A completion prints no version line | four boxes, no version line, on a scratch node with no `dod.yaml` |
| 6 | The `verify` prompt ends at step 8 | ends at the post-mortem offer; no occurrence of "version" |
| 7 | The cut still works when asked for | all three files present; `unpushed-version.sh` still exits 0/1/2 |
| 8 | Suite green the way CI runs it | bare `pytest`, **3687 passed**, 16:02 |
| 9 | Web dialog offers four boxes | four in `content-views.tsx`; formatting check no worse than baseline |

`tcw capabilities check` and `tcw validate` both report OK.

## A regression this stage caught

Criterion 9 found a real defect that the implementation had introduced and that
nothing else would have reported. Removing the fifth checklist entry left the
array in `web/client/src/ui/content-views.tsx` short enough for Prettier to want
it on a single line, so a file that was clean before this work started failing
`pnpm prettify:check`.

It was invisible in the obvious place to look: 310 files already fail that check
on a clean checkout, so the total did not move in a way anyone would notice. It
only surfaced by extracting the file's pre-change version and checking that
against the current one. Fixed in `0912bc8d` — whitespace only.

## Definition of Done

Checked by hand, because this item changed TCW's own code and CLAUDE.md forbids
driving the lifecycle with the CLI while that is true.

- **tests pass** — 3687 passed, bare `pytest`, zero failures.
- **docs synced** — the `documentation-sync` skill was run; entries written to
  `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md`; the guide,
  the configure and transitions references and this repo's own `dod.yaml` all
  updated.
- **capabilities reconciled** — four capability descriptions updated under
  `changed:`, none new or removed, back-pointer written to `capabilities.yaml`,
  `tcw capabilities check` OK.
- **reviewed** — by the user directly. No adversarial reviewer agent was run on
  this change; recording that plainly rather than implying a review that did not
  happen.
- **originating GitHub issue** — not applicable; this came from a user request,
  not an issue.

## A test failure that was not one

A full-suite run partway through this work reported three failures, all showing
the deleted step-9 text and all looking exactly like a genuine regression:

```
tests/test_procedure_verb.py::test_an_unconfigured_node_prints_every_default
tests/test_prompt_fallback.py::test_an_unconfigured_node_sees_the_recorded_bytes[verify]
tests/test_stage_verb.py::test_an_unconfigured_node_prints_tcws_own_instructions
```

They were environmental. Each of those three compares an in-process `import tcw`
against a `subprocess.run(["tcw", ...])`, and they fail whenever the two resolve
to different source trees. The machine's shared editable install pointed at
another session's worktree at the time.

The non-obvious part, and the reason the first attempt to work around it failed:
**bare `pytest` does not put the current directory on the module search path**, so
the editable install's import hook wins even from the checkout root. From the same
directory, in the same second, `python -c "import tcw"` resolved to this checkout
while bare `pytest` resolved to the worktree. A private virtual environment first
on `PATH` fixes the console script but not the interpreter unless the environment
also has its own `pytest` binary.

Proven in both directions on the same commit: with both sides on this checkout the
three tests pass; split deliberately, the same test fails again. That finding has
been written into the project memory note about virtual environments, correcting a
claim there that was wrong.

## Deferred, deliberately

- **Backlog item `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`**
  is strengthened by this change, not obsoleted — its own spec already argues a
  version cut is always user-initiated. Left open. Its "completion options" prose
  refers to the offer that no longer exists and needs a touch when that item runs.
- **The shared editable install** still points at another session's worktree. That
  session agreed to restore it to `/Users/brian/Projects/TCW` when their item
  finishes. Until then, a bare `pytest` in this repo that does not go through a
  pinned virtual environment will show the three false failures described above.
- **No version was cut.** Fitting, given what this item does: it is the user's
  call, and they did not ask for one.

## Notes

`docs/work/inbox/2026-09-17-complete-says-the-verify-stage-was-skipped-for-a-worktree-item.md`
records that the Definition of Done checklist printed with every box unticked in a
non-interactive run and completion continued anyway. That is about whether the
checklist is **enforced**; this item changed what it **says**. No open item covers
it, and it is at risk of being triaged away as a duplicate of this one. It is not.
