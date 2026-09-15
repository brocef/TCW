# Refined outcome — Publish TCW to PyPI with automated releases

## Decision

**Accepted** by the requester on 2026-08-11, together with a minor version cut.

## Evidence

Suite: **1203 passed** (baseline 1193 at spec time; +9 = 7 probe cases, 2 seam
cases, and 1 from `test_documented_cli_surface.py` picking up the capability
description seeded at spec). `tcw validate` OK, `tcw capabilities check` OK,
`tcw capabilities drift` clean.

| # | Criterion | Verdict |
| --- | --- | --- |
| 1 | `tcw-cli` distribution; wheel installs a working `tcw` | met — clean build → empty venv → `tcw --version` = 0.19.0 |
| 2 | Wheel carries the prebuilt web app | met — `server.cjs` (1372999 B) + `client/index.html` under site-packages |
| 3 | Editable `tcw-cli` left alone; machine-independent test | met — closed during verify, see below |
| 4 | `_this_machine_has_an_editable_tcw()` true for `tcw-cli` | met — it consumes the extracted two-name probe |
| 5 | Test workflow matrix | **deviates, accepted** — 3.11 + 3.14, not 3.11 + 3.13 |
| 6 | Release workflow trigger and permissions | met — `v*` only, `id-token: write`, `environment: pypi` |
| 7 | Mismatched tag fails before upload | **half-met** — logic verified both directions locally, never in a job |
| 8 | Full suite passes | met |
| 9 | No stale old-name references | met — repo-wide sweep clean |
| 10 | `tcw validate` exits 0 | met |
| 11 | Release notes + changelog | met |

### Criterion 3 — a gap found and closed during verification

The assessment found criterion 3 only half-satisfied: the fixture tests stub the
owning interpreter's verdict, and the probe cases run the probe with no script
around it. Neither covered the **seam** — which is exactly where the rename bit,
since the script asked a question the probe could no longer answer for
`tcw-cli`.

Closed with `test_script_and_probe_together_decide_on_a_tcw_cli_install`
(`cc8b255`): a stand-in interpreter that is a shell script *named* `python3.11`,
so the script's real code path runs the real probe against a synthetic
site-packages. Parametrized both directions — the non-editable case is what
proves it discriminates rather than passing for free.

Proven non-vacuous: reverting the probe to its single-name form fails 4 tests,
including this one's editable case.

### Criterion 5 — the accepted deviation

The spec said Python 3.11 + 3.13, describing 3.13 as "the current release". The
maintainer develops on **3.14.6**, so that matrix would have topped out below the
interpreter the code is actually written against. Shipped as 3.11 + 3.14. The
criterion text is superseded rather than missed.

## What could not be verified, and is not claimed

Nothing in `.github/` has ever executed — it existed only in local commits at
closeout. Three things remain structurally unprovable until a push:

- **Both CI legs green.** First push of `main` proves it.
- **Trusted Publishing authenticates.** Unrehearsable by construction: the first
  successful release run is also the first real upload.
- **Criterion 7's other half** — the gate failing a *job*, not just a shell.

The pending publisher on pypi.org was reported configured by the requester;
it cannot be verified from here (authenticated page). Its values are written into
`README.md` §Releasing so they can be checked against `release.yml` by eye rather
than recalled.

## Capability reconciliation

- `cli/install-from-pypi` — `Missing` → **`Supported`**.
- `plugin/bootstrap-the-cli` — re-read; wording still true and now more reliably
  so. No edit.
- `plugin/diagnose-the-install` — extended: `/tcw-doctor` now also reports a
  leftover package left beside the current one, which is new user-visible
  behavior from the Task 3 finding.

## Closeout choices

- **Route:** committed directly to `main`. The item's lifecycle commits were
  already there from planning, so branching mid-item would have split its
  history — and this repo's recent history runs whole work items on `main`.
- **Documentation:** all four Documentation Sync triggers answered during
  implementation (`3b87848`), so review saw code and docs together.
- **Version:** minor → `v0.20.0`. Folding into `v0.19.0` was checked and refused
  by the gate — that tag is already on `origin`, and rewriting a published tag is
  off the table.

## Deferred follow-ups

- `2026-08-11-install-the-plugin-s-cli-from-pypi-instead-of-its-own-clone` —
  `blocked_by` this item; now unblocked. Switching the plugin's install source to
  PyPI and stripping the Python code from the plugin package.
- `2026-08-11-accept-comma-separated-tags-on-tcw-work-new` — unrelated papercut
  filed during this item's planning.

## Notes

- **The next push is the consequential one.** Pushing `main` alone exercises CI
  at no cost; pushing the tag spends `0.20.0` whether or not the upload succeeds.
  Doing them in that order separates "does CI work" from "does publishing work".
- No post-mortem offered: verification surfaced one coverage gap, closed in
  place, and no defect in the shipped behavior.
