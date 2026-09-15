# Refined outcome — `load_yaml` reads a falsy YAML document as an empty mapping

## Decision

**Accepted.** On 2026-09-14 the requester said: "This is old, so let's just mark
it as verified and completed." The implementation was finished on 2026-09-11 but
the item was never taken through `verify`, and the change has been in every
release since **v2.1.0**. No formal review round was run for this acceptance.

## Evidence

- **Already published.** Every implementation commit (`7aaf66ae`, `b94ab11f`,
  `edfe5733`, `9e8b7e08`) is contained in the tags `v2.1.0` through `v2.2.0`, and
  the change is described in `docs/changelogs/v2.1.0.md`.
- **Tests, run at closeout on `main` at `086350ec`.**
  `python -m pytest tests/test_environment_hardness.py` gave **101 passed**.
  The full suite on `main` passed earlier the same day (3114, bare `pytest` at
  `ea2f06d4`).
- **Validate.** `tcw validate` printed `validate OK`, which `outcome.md`
  criterion 7 requires.

## Closeout

- `outcome.md` had `TBD` where the commit hashes for tasks 3 to 5 and the docs
  belonged. They are filled in: `edfe5733` and `9e8b7e08`.
- `RESUME.md` was working scaffolding from the unattended run. It is deleted, as
  it asked to be.
- **Capability ledger:** the item declared no capability changes, so there is
  nothing to reconcile.
- **Version:** none to cut. The change shipped in v2.1.0.
- **Follow-up still open:**
  `docs/work/inbox/2026-09-11-a-linked-worktree-under-dot-claude-makes-the-parity-test-fail.md`.
