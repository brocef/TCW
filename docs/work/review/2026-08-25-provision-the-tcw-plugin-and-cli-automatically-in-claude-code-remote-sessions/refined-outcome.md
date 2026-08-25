# Provision the tcw plugin and CLI automatically in Claude Code remote sessions — Verification

## Decision

**Accepted** by the requester in session, on the assessment presented at the end
of `implement`: "Sounds good, merge and push." The two design calls the
assessment put up for veto — installing **this checkout** editable rather than
the published `tcw-cli`, and sourcing the plugin from **the checkout** rather
than `brocef/TCW` — were accepted as they stand.

## Evidence

Against `spec.md`'s acceptance criteria, from commands run at implement time and
recorded in `outcome.md`:

- `scripts/remote_session_setup.sh` exists, is mode 0755, and `bash -n` parses it.
- Gate, `--force`, root check, guard, pip retry, both plugin failure paths, the
  `CLAUDE_ENV_FILE` PATH repair, and the never-`--scope project` invariant are
  each covered by a test; `pytest tests/test_remote_session_setup.py` → 20
  passed.
- `pytest tests/test_remote_session_setup.py tests/test_session_bootstrap.py
  tests/test_plugin_manifests.py` → 55 passed. `tcw validate` → `validate OK`.
- Real teardown and rebuild in the session's container: 5.2 s cold, silent,
  exit 0 → `tcw 1.0.3` matching `tcw/__init__.py`, `pytest`/`jsonschema`
  importable, `claude plugin list` showing `tcw@tcw` enabled at user scope,
  `git status --porcelain` empty. Second run 2.0–2.7 s with the guard hit.
- `.claude/settings.json` parses, registers the `SessionStart` hook, and still
  enables `tcw@tcw`.

## Capability ledger

Reconciled: unchanged, as `spec.md` said it would be. Nothing shipped that a
user of the published plugin can newly do — `plugin/install-as-a-plugin`,
`plugin/bootstrap-the-cli`, and `cli/install-from-pypi` all describe the
published paths, and none of them moved.

## Deferred

Recorded here rather than fixed, none of them blocking:

- **The one criterion that could not be checked here**: that a *fresh* remote
  container fires the hook at session start. This session's container predates
  the hook. The first session on `main` after this merges is the check, and the
  script prints on failure so that session reports it. If it does not fire,
  that is a rework of this item, not a new one.
- **Six pre-existing suite failures in this container** (uid 0 defeats the
  `chmod`-unwritable-directory tests; `pip wheel --no-build-isolation` exits 1),
  all reproducing on the commit before this work. Not this item's; CI is the
  authority and runs non-root.
- **`AGENTS.md` fails `prettier --check` at HEAD** (table padding, `*how*` for
  `_how_`), pre-existing and left alone. The section added here was verified
  clean.
- **`claude plugin uninstall` rewrites a checkout's `.claude/settings.json`** —
  strips the entry at every scope and reformats to 2-space indent against this
  repo's 4-space config. Nothing the hook runs does this; worth knowing before
  anyone runs an uninstall inside the checkout.

## Closeout

Resolution `done`. Merged to `main` as a fast-forward, matching the repository's
linear history. No version cut taken with this item: it ships no user-facing
change, and `docs/changelogs/upcoming.md` now carries the `Internal` entry for
whenever the next cut happens.
