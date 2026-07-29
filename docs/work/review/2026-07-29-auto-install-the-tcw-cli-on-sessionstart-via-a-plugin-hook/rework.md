# Rework — Auto-install the tcw CLI on SessionStart via a plugin hook

Rejected at `verify` on the user's decision. The delivered scope is sound —
12 of 13 acceptance criteria met, 1088 tests green, the editable guard proven by
hand — but verification found a defect this change introduced that the user wants
fixed inside this item rather than deferred. No `refined-outcome.md` was written.

## What has to change

### 1. `allowed-tools` must cover the script both documents now instruct

**The defect.** Task 3 rewrote `skills/tcw-plugin/references/setup.md` and
`references/doctor.md` to run `scripts/session_bootstrap.sh`, and task 5 pointed
`commands/tcw-doctor.md` at the same call. Neither grant permits it:

- `skills/tcw-plugin/SKILL.md:5` — `Bash(tcw *), Bash(command -v *), Bash(pipx list *), Read`
- `commands/tcw-doctor.md:3` — `Bash(tcw *), Bash(command -v *), Bash(pipx *), Bash(python3 *)`

**Failure scenario.** A Claude user whose `tcw` is missing invokes `/tcw-doctor`
or the `tcw-plugin` skill. The agent follows the reference, tries to run the
bootstrap script, and falls outside the grant — a permission prompt in exactly
the path this item exists to make frictionless. The install still works if the
user approves; the ergonomics do not.

**Note the gap is wider than the script.** `SKILL.md` grants `Bash(pipx list *)`,
so `setup.md`'s `pipx install "<clone-root>"` and doctor's
`pipx install --force` were *already* outside it before this change. Fix the
whole grant, not just the script line — a partial fix leaves the same prompt
firing one step later.

**Requirements:**

- Both documents' `allowed-tools` must cover every command their procedures now
  instruct: the bootstrap script, `pipx install` / `pipx install --force`, and
  whatever `doctor.md` steps 1–3 call.
- **Determine a pattern that actually matches and verify it** — do not assume.
  The script is invoked by absolute path (`"<clone-root>"/scripts/session_bootstrap.sh`)
  and the clone root is a version-namespaced cache directory that changes on every
  plugin update, so a literal path is wrong and a leading-wildcard pattern may not
  be supported. If no pattern can match a path that moves per update, say so in
  `outcome.md` and pick the honest fallback rather than writing a grant that
  silently never matches.
- Keep the two grants consistent with each other; they drive the same procedures.
- `allowed-tools` is Claude-only frontmatter — Codex ignores it. This is an
  ergonomics fix for one harness, and it must not change what either harness
  *does*. No behavior change, no new capability.

### 2. Correct the stale cross-reference this change falsified

`docs/work/backlog/2026-07-28-make-the-consolidate-plans-workflow-reachable-from-codex/initial-request.md:60`
asserts: *"Only three command files carry it: this one, `tcw-doctor`, and
`tcw-init`."* Deleting `commands/tcw-init.md` makes that two. The count is
load-bearing — it supports that item's argument about `disable-model-invocation:
true` guarding a workflow that **deletes files**, so a wrong count there weakens a
safety argument, not just a doc.

Correct the sentence to match reality. Do not otherwise edit that item; it is
another item's `request` artifact and only this factual claim is ours to fix.

## Out of scope for this rework

- **Plan Verification items 2 and 4** (real plugin update round trip; whether a
  deleted command lingers on an installed plugin). The user chose to close on
  these and let the next release surface them. They stay recorded as not run.
- The capability flip for `plugin/bootstrap-the-cli` — still a `complete`-time
  step, unchanged by this rework.
- `.claude/settings.local.json:91` — user-local, out of scope, and staying that way.

## What must still hold when this returns

Everything verified at the first pass, re-checked rather than assumed:

- The full suite green (1088 at rejection).
- `test_real_editable_checkout_is_left_alone` **runs** rather than skips.
- The editable guard still holds with a stub `pipx` on PATH and cwd set to the
  repo — the condition that defeated the spec's original guard.
- Silence discipline on every skip: exit 0, empty stdout, empty stderr.
- `grep -rn "tcw-init" README.md skills/ commands/` still returns nothing.

Update `outcome.md` with what this pass changed rather than writing a second
outcome artifact.
