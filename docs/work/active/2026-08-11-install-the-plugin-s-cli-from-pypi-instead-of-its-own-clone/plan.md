# Plan — Install the plugin's CLI from PyPI instead of its own clone

Compressed at the requester's direction: the spec carries the design, the
per-file docs table, and grep-checkable acceptance criteria, so this plan
sequences rather than restates. No bounded stage documents. Run sequentially in
one session — the `doctor.md` / `commands/tcw-doctor.md` pair must stay
consistent, and splitting them across agents is how they drift.

## Ordering rationale

The script change and the two test assertions that name the clone are **one
commit**. `session_bootstrap.sh:93` is asserted by
`tests/test_session_bootstrap.py:203` and `:215`; changing either side alone
leaves the suite red, so they are not two tasks (`stage-plan.md` step 2). Docs
follow as one block at the end, per the Documentation Sync gate — written against
the finished diff, not predicted mid-flight.

The riskiest task is not the script (4 lines, fully covered by existing tests) —
it is **task 4**, the `doctor.md` rewrite, which is prose with no test behind it.
It is placed after the code is settled and green, so its description of reality
is written against reality.

## Tasks

### 1. Switch the install source, and the two assertions that pin it

**Changes:** `scripts/session_bootstrap.sh`, `tests/test_session_bootstrap.py`.

- Line 93: `pipx install --force "$root"` → `pipx install --force tcw-cli`.
- Line 99: the failure message stops naming `$root` and names PyPI. Still one
  line, still routes to `/tcw-doctor` (Codex: the `tcw-plugin` skill), still no
  attempt to classify the failure.
- Line 2 (file header) and line 71 (step-2 comment): both say the script installs
  from / matches "the clone". Reword to the sentinel's real meaning — *the plugin
  has not changed since we last installed* — per spec §"What the sentinel is,
  precisely". No behavior change; this is the comment that would otherwise lie.
- `tests/test_session_bootstrap.py:215` → expect `install --force tcw-cli`.
- `tests/test_session_bootstrap.py:203` → `.endswith("tcw-cli")`.

**Verified by:** `pytest tests/test_session_bootstrap.py` green with exactly
those two assertions changed (spec criteria 1-6). Criterion 2 is the sharp one:
if any *other* assertion needed changing, the change escaped its intended scope
and the plan is wrong, not the test.

### 2. Confirm the migration against real pipx

**Changes:** none — a check, recorded in `outcome.md`.

Run the block in spec §Design → Migration in a throwaway `PIPX_HOME`. Expect one
venv named `tcw-cli` and `package_or_url` flipping from the local path to
`tcw-cli`.

**Verified by:** spec criterion 12. Deliberately not a test — the suite forbids
real pipx (`tests/test_session_bootstrap.py:3-7`) and this would add a network
dependency to CI.

### 3. Reword the three capability records

**Changes:** `docs/capabilities/plugin/bootstrap-the-cli/`,
`docs/capabilities/cli/install-from-pypi/`,
`docs/capabilities/plugin/diagnose-the-install/` — via `tcw capabilities`, not by
hand. **REQUIRED SUB-SKILL: use `tcw-capabilities`.**

Deltas are specified in spec §Capability changes. All three stay `Supported`; no
additions, no removals, no taxonomy change. `bootstrap-the-cli` must name the
no-network case, since that is the new user-visible failure.

**Verified by:** spec criterion 10 — all three, read back through
`tcw capabilities show`.

### 4-7. Documentation Sync block

Evaluated at this stage against `CLAUDE.md` §Documentation Sync: **all four
entries fire.** One pass over the finished diff at the end of `implement`, not
interleaved above.

| # | Entry | Trigger | Task |
| --- | --- | --- | --- |
| 4 | `skills/tcw-plugin/` | `[Skill-Driven-Component]` | The component the skill drives — the install/repair procedure — is exactly what changed. Update `SKILL.md` (frontmatter `description`, `when_to_use`, `compatibility`; body 61-86), `references/setup.md` (title, opening, step 2, step 4's fallback ladder → `pip install --user tcw-cli`, step 6's now-void drift warning), and `references/doctor.md` per spec §"What `/tcw-doctor` diagnoses instead" — drop the `sort -V` cache scan, replace the source-comparison repair with present/ours-to-touch + `pipx upgrade tcw-cli`. Then `commands/tcw-doctor.md`, which routes into `doctor.md` and repeats its version-match promise in frontmatter. |
| 5 | `README.md` | `[Public-API]` | Lines 118-128, 137, 143-152, 943. The install route is the public surface here. Must state the offline regression **in the install section** (spec criterion 11), and invert the "don't also `pip install tcw-cli`" warning — it is now the same package. |
| 6 | `docs/release-notes/upcoming.md` | `[Public-API]` | Plain language: the plugin now installs the published CLI; the first session after installing or updating needs network. |
| 7 | `docs/changelogs/upcoming.md` | `[Any-Code-Change]` | Grouped entries — Changed (install source, floating version), Internal (sentinel semantics clarified in comments, two test assertions). |

**Verified by:** spec criteria 7-9, 11, 14 — the greps are the check, because a
missed paragraph is the likely failure mode, not a broken script.

## Verification

Beyond `pytest`:

1. **The four greps** in spec criteria 7-9. Criterion 7's pattern is deliberately
   wider than "own clone": the first draft of the spec passed a narrow grep while
   four "plugin clone" phrasings survived.
2. **The real-pipx migration block** (task 2) — the one claim the suite cannot
   reach.
3. **Read `doctor.md` and `commands/tcw-doctor.md` together after task 4.** The
   command is a router into the reference; they can each be individually correct
   and jointly inconsistent, and no test covers either.
4. **Full suite** (`pytest`), including `test_plugin_manifests.py` and
   `test_documented_cli_surface.py` (spec criterion 13).

Not verifiable here, stated rather than faked: that a real plugin install on a
real user's machine picks up `tcw-cli` from PyPI at session start. Every layer
below that is covered — argv assertion, real-pipx migration check, live PyPI
package — but the end-to-end path runs only under an actual harness session.
This is the item's genuine residual risk and belongs in `verify`.

## Notes

- No new blockers. `2026-08-11-publish-tcw-to-pypi-with-automated-releases` is
  `completed` and `tcw-cli` 0.20.1 is live, so nothing gates `start`.
- The repo split (the request's ask #2) is filed as a follow-up item at closeout,
  per spec §Non-goals — not tracked here.
- Version choice is deferred to closeout, per `stage-verify.md` step 9.
