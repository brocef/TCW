# Refined outcome — Auto-install the tcw CLI on SessionStart via a plugin hook

**Accepted** by the user at `verify`, on the second pass. The first pass was
rejected over the `allowed-tools` gap; that rejection is recorded in `rework.md`
and its fix, plus four defects verification found alongside it, are in
`outcome.md` → Rework pass.

## The decision and its evidence

Accepted on evidence run by the coordinating session, not on the implementing
agents' reports:

- **1091 tests pass** (1088 before the rework; +2 for the new provenance guard,
  +1 from concurrent unrelated work).
- **The editable guard holds against this machine's real checkout.** Re-proved by
  hand with a stub `pipx` prepended to the real PATH and cwd set to the repo —
  the exact condition that defeated the spec's original guard. pipx never
  invoked, sentinel never written, stdout and stderr both empty.
- **`test_real_editable_checkout_is_left_alone` runs rather than skips**, so the
  guarantee is checked against reality on every run here, not only in fixtures.
- **The `allowed-tools` pattern was verified with a negative control** — the
  matching rule executed the script, a deliberately non-matching rule was blocked
  by the permission system. A pass without the control would have proven nothing.
- **Criteria 9 and 11 closed at this stage**, as designed: the
  `plugin/bootstrap-the-cli` body no longer names `/tcw-init`, `tcw capabilities
  check` passes with the capability still `Supported`, and `grep -rn "tcw-init"`
  over `README.md`, `skills/`, `commands/`, and `docs/capabilities/` is clean.

All 13 acceptance criteria are met.

## What verification was worth

Two defects of the same species — a guard that looks right and is wrong in a real
configuration — that neither planning nor implementation caught:

1. **The `sys.path` trap** (found at `implement`): the spec's own mitigation for
   its highest-stated risk did not work, because a hook runs with the project as
   cwd and a checkout's `tcw.egg-info` answers before the real dist-info.
2. **The wrong-interpreter probe** (found at `verify`): the guard asked whatever
   `python3` PATH resolved to, not the interpreter owning the `tcw` on PATH. Every
   test passed only because both are pyenv shims here sharing one interpreter.
   The fix inverts the invariant — *only replace a `tcw` whose own interpreter
   reports a plain, non-editable install; an install whose owner cannot be
   identified is not ours to replace* — so it fails safe on unknown provenance.

The second was found only because the assessment was asked to be skeptical about
the specific thing the item most depended on. That is worth repeating on work of
this shape.

## Deferred follow-ups

None block closeout; all are recorded rather than left implicit.

1. **A plain `pip install tcw` is still force-installed over.** Non-editable and
   not plugin-installed, so the provenance guard admits it. Unchanged from before
   this item; `setup.md` warns against keeping both and `/tcw-doctor` diagnoses it.
2. **An editable checkout whose `tcw` is not on PATH** (venv not activated) falls
   through to a global pipx install. Not destructive — separate environments — but
   it produces the two-copies drift the README warns about.
3. **Plan Verification items 2 and 4 were not run**: the real plugin update round
   trip, and whether a deleted `/tcw-init` disappears from an installed plugin or
   lingers until reinstall. Both need a live install from this branch; the user
   chose to let the next release surface them. The fallback holds either way — a
   lingering command routes to the rewritten `setup.md`, which runs the same script.
4. **The provenance guard was never exercised against real pipx** — pipx is not
   installed on this machine. Fixture-covered only. This is also why the fix reads
   a shebang rather than pipx's JSON: an unverifiable schema guess would have
   risked a hook that silently never installs for anyone.
5. **`2026-07-28-make-the-consolidate-plans-workflow-reachable-from-codex`** states
   a command count that this item falsified (three → two). Deliberately *not*
   patched: `initial-request.md` records what was asked, and the count is rarity
   color whose argument holds at two. That item's `spec.md` should re-derive it.
6. **`claude plugin validate --strict .` fails at the repo root** on a missing
   marketplace `description`. Pre-existing and unrelated, but "strict validation is
   clean" is not currently true of this repo.
7. **`.claude/settings.local.json:91`** holds a stale local permission entry naming
   `commands/tcw-init.md`. User-local, out of scope.

## Closeout

- **Route:** committed directly to `main`; no branch or PR. Nine commits carry the
  change, plus the lifecycle transitions TCW committed itself.
- **Documentation:** current as of `implement` and re-run over the rework diff.
  All four Documentation Sync triggers fired across the two passes and all four
  were answered.
- **Capability:** `plugin/bootstrap-the-cli` rewritten and still `Supported`.
- **Version:** offered to the user after `complete`, per `stage-verify.md` step 9.

## Notes

**Process defect worth recording.** Commit `4e7c251` swept two files belonging to
a *different* work item — `2026-07-29-triage-github-issues-into-tcw-work-items`,
being authored concurrently in another session — into this item's docs commit,
via a `git add docs/` before a narrow-staging instruction reached the agent.
Nothing was lost or altered and that session's own commits built on top normally;
the cost is attribution only. Deliberately not untangled: rewriting a commit that
a concurrently-committing session has already built four commits on top of is a
worse risk than the mis-attribution. The general lesson — when more than one
session commits to one repo, stage by explicit path, never by directory — belongs
in whatever guidance governs multi-session work, not in this item.

**Delegation shape.** Three subagents: implementation, documentation, and a
read-only verifier, with this session coordinating and re-running every check
itself. None of the three returned its report without being asked, so a
coordinator that treated silence as completion would have shipped unverified work
three times.
