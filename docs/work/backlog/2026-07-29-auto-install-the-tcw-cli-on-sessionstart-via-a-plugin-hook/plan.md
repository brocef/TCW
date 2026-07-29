# Plan — Auto-install the tcw CLI on SessionStart via a plugin hook

Ordering principle: the script exists and is tested before anything is wired to
it, and before any document is rewritten to point at it. The riskiest behavior
(force-installing over a dev checkout) is covered by tests written in the same
task that introduces the install path, not bolted on later. The suite is green at
every commit boundary.

## Task 1 — `scripts/session_bootstrap.sh` and its tests

**Changes:** new `scripts/session_bootstrap.sh` (mode 755); new
`tests/test_session_bootstrap.py`.

Implement the check order from `spec.md` → Design: unresolvable clone root →
editable install → sentinel match *and* `tcw` on PATH → pipx absent → otherwise
`pipx install --force`, then write the sentinel. Every path exits 0; only a
failed pipx run prints, and it prints one line to **stdout** (not stderr, not
exit 2 — `SessionStart` only surfaces stdout to the agent).

Signature: `session_bootstrap.sh [clone-root] [sentinel-path]`, defaulting to
`${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}/installed-version`. The
explicit arguments are what make it runnable under Codex, where neither variable
is set — do not let the script depend on the variables being present.

Detect the editable install the way `skills/tcw-plugin/references/doctor.md:11-14`
already prescribes (`direct_url.json` → `dir_info.editable`), so the hook and the
doctor procedure agree on what "leave it alone" means.

**Verified by:** `tests/test_session_bootstrap.py`, pytest over `tmp_path` with a
fake `pipx` shim prepended to `PATH` that records its invocation and can be made
to fail. One test per acceptance criterion 4–8:

- sentinel matches + `tcw` present → exit 0, no output, fake pipx never invoked;
- editable install → exit 0, no output, fake pipx never invoked;
- sentinel differs + no pipx on PATH → exit 0, no output, sentinel unmodified;
- failing pipx → exit 0, exactly one stdout line containing `/tcw-doctor`,
  sentinel unmodified;
- succeeding pipx → sentinel byte-identical to the clone's `tcw/__init__.py`, and
  a second run takes the silent path.

The fake-pipx shim is what keeps this hermetic: no test may invoke real pipx or
touch the developer's actual install.

## Task 2 — Wire the hook

**Changes:** new `hooks/hooks.json`; `.claude-plugin/plugin.json` gains
`"hooks": "./hooks/hooks.json"`; new test in `tests/test_plugin_manifests.py`.

Single `SessionStart` command hook, shell form, calling
`"${CLAUDE_PLUGIN_ROOT}"/scripts/session_bootstrap.sh` with the quoting the
plugins reference specifies.

**Verified by:** a `test_plugin_manifests.py` test asserting `hooks/hooks.json`
parses, that the manifest's `hooks` path resolves to an existing file, and that
the command's script exists and is executable — the mode-755 guard from
acceptance criterion 3, which a `git`-committed permission bit can otherwise lose
silently. Plus `claude plugin validate .` run by hand (criterion 1; see
Verification).

## Task 3 — Collapse `setup.md` and `doctor.md` onto the script

**Changes:** `skills/tcw-plugin/references/setup.md`,
`skills/tcw-plugin/references/doctor.md`.

Both become "run `scripts/session_bootstrap.sh <clone-root>`" plus only the
judgment the script deliberately does not encode: `setup.md` keeps the pipx
fallback ladder for when the script reports pipx missing; `doctor.md` keeps
install-kind classification, the `sort -V` cache-version scan, and the Node /
`tcw serve` diagnosis.

This is the task that makes the behavior identical under both harnesses — a Codex
agent reaches the same code path by instruction that a Claude session gets from
the hook. It is not a documentation touch-up; treat a regression here as a
functional regression.

**Verified by:** review against `spec.md` → Non-goals — neither document may
describe reconcile steps the script now owns, and neither may drop the judgment
the script does not own. No automated check; carried in Verification below.

## Task 4 — Delete `/tcw-init`

**Changes:** delete `commands/tcw-init.md`.

Only the command file. Its prose references live in README and the skill router,
which the documentation block below handles in one pass.

**Verified by:** full suite green (nothing references the command file
programmatically); `git status` shows the deletion.

## Documentation Sync

All four entries in `AGENTS.md` → Documentation Sync fire. Scope is concrete, so
each is a named task. Scheduled as one block after the code tasks, per
`stage-plan.md` step 4 — one pass over the finished diff.

### Task 5 — `skills/tcw-plugin/SKILL.md` [Skill-Driven-Component]

The component this skill drives — how `tcw` gets installed — changes outright.
Update the frontmatter `description` (line 3 names `/tcw-init` explicitly) and the
"Installing & repairing" router so it describes an automatic install with the
script as the manual entry point, and mentions only `/tcw-doctor`.

### Task 6 — `README.md` [Public-API]

Remove `/tcw-init` from the Claude install snippet (line 104) and state that the
CLI installs itself at the next session start; drop it from the command inventory
(line 108) and the routing note (line 114); rewrite the Codex paragraph (lines
127-128) to name the `tcw-plugin` skill without referring to the deleted command;
fix the skills list entry (line 835). Do **not** touch `docs/changelogs/v0.2.0.md`,
`docs/changelogs/v0.9.0.md`, or `docs/release-notes/v0.2.0.md` — archive.

### Task 7 — `docs/release-notes/upcoming.md` [Public-API]

Plain language: the `tcw` command now installs and updates itself when a session
starts, so there is nothing to run after installing or updating the plugin;
`/tcw-init` is gone; `/tcw-doctor` remains for when something looks wrong. Note
that a dev checkout installed with `pip install -e .` is left alone.

### Task 8 — `docs/changelogs/upcoming.md` [Any-Code-Change]

Grouped entries: **Added** — `hooks/hooks.json` `SessionStart` hook,
`scripts/session_bootstrap.sh`, `tests/test_session_bootstrap.py`; **Changed** —
`tcw-plugin` references delegate to the script, `.claude-plugin/plugin.json`
declares `hooks`; **Removed** — `commands/tcw-init.md`.

### Task 9 — Capability flip (at `tcw work complete`)

`capabilities.yaml` records `changed: [plugin/bootstrap-the-cli]`. Rewrite
`docs/capabilities/plugin/bootstrap-the-cli/description.md` to describe the
automatic install with no mention of `/tcw-init`; status stays `Supported`. Run
`tcw capabilities check`. Per `tcw-capabilities` this belongs to the ledger flip
at `complete`, not to implementation — it is listed here so it is not forgotten.

## Verification

Beyond the suite:

1. **`claude plugin validate .`** — acceptance criterion 1, and the only check of
   the unverified assumption in `spec.md` → Notes that a `hooks` key may point at
   a file path. If it rejects the key, fall back to root auto-discovery and drop
   the manifest line (criterion 2 changes accordingly).
2. **Real update round trip** — install the plugin from this branch, confirm the
   CLI appears at the next session start; then bump the version, update, restart,
   and confirm the reinstall fires exactly once and is silent on the session after.
   The test suite exercises the script's logic with a fake pipx, never the actual
   hook firing.
3. **This repo's own checkout stays untouched** — after the hook is live, confirm
   sessions in `/Users/brian/Projects/TCW` still resolve `tcw` to the editable
   pyenv shim and that the sentinel was never written. This is the highest-impact
   risk in `spec.md` and the machine it would break first is the maintainer's.
4. **Deleted-command propagation** — check whether `/tcw-init` disappears from an
   already-installed plugin on update or lingers until reinstall (`spec.md` →
   Risks). If it lingers, say so in the release notes; the stale command routes to
   the rewritten `setup.md`, so the fallback is redundant-but-correct.
5. **Steady-state cost** — confirm the hot path runs no Python and invokes no
   pipx, so the every-session-every-project cost stays one `command -v` and one
   `cmp`.

## Notes

No blockers: nothing in the backlog gates this, and it gates nothing.

`tests/test_session_bootstrap.py` tests a shell script from pytest. That is a
departure from the suite's Python-only habit, and it is deliberate — the script
must be shell so the hook can invoke it with no interpreter assumption, while the
behavior around a maintainer's dev install is exactly what must not go untested.
