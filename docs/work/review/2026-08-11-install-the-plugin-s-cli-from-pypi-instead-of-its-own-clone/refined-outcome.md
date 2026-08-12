# Refined outcome — Install the plugin's CLI from PyPI instead of its own clone

**Accepted** by the requester on 2026-08-12, on the assessment presented at
`review`. Resolution: `done`.

## What was accepted

`scripts/session_bootstrap.sh` installs the published `tcw-cli` from PyPI rather
than the plugin's own clone. The version floats. There is no offline fallback —
a deliberate choice made by the requester at `spec`, overriding the fallback the
first draft recommended.

All 14 acceptance criteria met; full suite green (1229 passed). Evidence is
tabulated criterion-by-criterion in `outcome.md` and not repeated here.

## Evidence the user weighed

- **The one behavioral line**, and the fact that everything else in the diff is
  comments, documentation, and capability wording.
- **The migration verified against real pipx**, not asserted: one venv,
  `package_or_url` flipping from the local path to `tcw-cli`. Existing plugin
  users need no manual step.
- **The guard fired for real.** The first migration attempt ran the script rather
  than raw pipx and it refused, because this machine carries an editable dev
  checkout — `test_real_editable_checkout_is_left_alone` happening in the wild.
- **One unplanned file change, disclosed rather than absorbed.**
  `tests/test_documented_cli_surface.py`'s parser matched `tcw` inside `tcw-cli`
  and read `pipx install --force tcw-cli` as a `tcw` invocation. Fixed at the
  parser rather than by rewording the docs around it, with a regression test and
  a changelog entry. The spec's "only one test file changes" prediction was
  wrong; the reason was a latent bug, not scope drift.
- **The residual risk, accepted with eyes open:** nothing here exercises a real
  harness session installing from PyPI end to end. Every layer beneath it is
  covered — argv assertion, real-pipx migration, live package — but the hook path
  runs only under an actual Claude or Codex session. First real verification is
  the first session after v0.21.0 ships.

## Closeout decisions

| Decision | Choice |
| --- | --- |
| Merge / PR route | None needed — the work was committed directly to `main`. |
| Documentation | Complete at `implement` step 6: README, `tcw-plugin` SKILL + `setup.md` + `doctor.md`, `commands/tcw-doctor.md`, release notes, changelog. All four Documentation Sync entries fired. |
| Capabilities | Three records reworded, all `Supported`; `capabilities.yaml` records them as `changed`. `tcw capabilities check`, `drift`, and `tcw validate` all clean. |
| Version | **Minor → 0.21.0.** The install route changed and offline support was removed; in 0.x that is the minor slot, and patch would undersell the regression. Folding into `v0.20.1` was not available — that tag is pushed and published to PyPI. |
| Follow-up | The repo split (the request's ask #2) filed as a backlog item. |
| Push | After the version cut, so commits and the `v*` tag go together and the release workflow publishes `tcw-cli` in one pass. |

## Notes

- **This change is inert until released.** A plugin version change is what makes
  the sentinel go stale and trigger the reinstall, so 0.21.0 is not incidental to
  the work — it is what turns it on.
- **Ordering that matters at release:** the release workflow publishes `tcw-cli`
  0.21.0 to PyPI from the same tag that ships the plugin. A user updating the
  plugin before that upload finishes floats to 0.20.1 instead and records it as
  current until the next plugin version. Known, documented in the changelog, and
  surfaced to users through `/tcw-doctor`'s currency report.
- No post-mortem offered: verification surfaced no unforeseen problems. The one
  deviation was found during implementation, fixed at root, and disclosed before
  review.
