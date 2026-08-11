# Refined outcome: make the TCW marketplace syncable from the claude.ai web app

**Accepted.** The user ran AC-7 against the pushed `main` and reported the
marketplace syncs from <https://claude.ai/code>. All seven acceptance criteria
are met.

## The decision and its evidence

| AC | Result |
| --- | --- |
| 1 — only `CLAUDE.md` is a tracked symlink | met, also verified on the pushed remote tree |
| 2 — Codex installs from a scratch clone | met — 8 skills, version read from `pyproject.toml` |
| 3 — `claude plugin validate .` zero warnings | met — was one |
| 4 — Claude CLI marketplace add | met — local clone and remote URL |
| 5 — `pytest tests/` green | met — 1193 passed |
| 6 — no functional `plugins/tcw` reference | met, criterion amended during `implement` (`819d3a1`) |
| 7 — adding `brocef/TCW` at claude.ai/code | **met — user-confirmed after push** |

## What AC-7 settled beyond the fix

`spec.md` carried an unresolved confound: both failing repositories belonged to
the user and the working control did not, so an uninstalled Claude GitHub App
would have explained the failure with nothing in this repo at fault. **A
user-owned repository now syncs, which rules that out.** The cause was in the
repository, and the spec's Grade-B inference — that `brocef/TCW` and
`brocef/skill-cefailures` failed for the same reason — is corroborated rather
than merely assumed.

## What is still unknown, and deliberately so

**Which of the two changes satisfied the validator.** The self-symlink removal
and the manifest metadata shipped together; identification was an explicit
non-goal (`spec.md` → Non-goals) because no goal depended on it and isolating it
would have cost the user a second manual web test. Both changes are justified
independently: the symlink cost three workarounds and pointed where `"."`
already pointed, and the manifests were genuinely under-described.

## Post-acceptance work completed

The three artifacts `plan.md` withheld pending AC-7 all landed in `16078bd`:

- `docs/release-notes/upcoming.md` — plain-language note that TCW can now be
  added from the web and desktop plugin directories
- `README.md` — a web/desktop directory line alongside the CLI install
- `docs/capabilities/plugin/install-as-a-plugin/description.md` — the body now
  distinguishes adding the marketplace from the command line versus the plugin
  directory, plus the `capabilities.yaml` `changed:` back-pointer

Status stays **Supported** — it was already Supported, and the item made the
existing claim true in a harness where it had silently been false. `tcw
capabilities check` and `tcw validate` both pass.

## Corrections to `outcome.md`

`outcome.md` recorded that `python -m build` was unavailable (neither
interpreter had `build` or `setuptools`), so the wheel check ran via
`pip wheel --no-deps` under build isolation. The user then had `build 1.5.0` and
`setuptools 84.0.0` installed globally, and **the check was re-run with the
originally specified tool** — same result: the wheel contains only `tcw` and its
dist-info, confirming `exclude = ["plugins*"]` was redundant with
`include = ["tcw*"]`. The finding was a missing tool, not a wrong check.

## Follow-ups

- **[brocef/skill-cefailures#3](https://github.com/brocef/skill-cefailures/issues/3)**
  — the diagnostic twin has both defects on `main` (`plugins/skill-cefailures → ..`
  and the same three missing marketplace fields). The issue carries the verified
  remediation, the causation caveat, and one repo-specific warning: it has **no
  `LICENSE` file**, so it must not copy TCW's `license: "Apache-2.0"`
  declaration. Fixing one defect at a time there would answer the causation
  question this item left open.
- **The fork probe is retired unrun.** It existed to test the ownership
  hypothesis, which AC-7 disproved. No follow-up item needed.

## Closeout

- **Route:** committed directly to `main` and pushed, consistent with this
  repo's history. No PR.
- **Documentation:** current — the changelog landed in `implement` (`0a128bf`),
  the three gated artifacts in `16078bd`.
- **Version:** minor bump, at the user's direction, cut after this item closes.

## Notes

- Two other items sit in `review` from earlier sessions
  (`2026-06-22-concurrency-safe-work-claims-…` and
  `2026-08-10-repair-invalid-playwright-taxonomy-fixture`). They were not
  assessed here and carry no acceptance decision from this session.
- No post-mortem offered: verification surfaced no unforeseen problem. The two
  planning defects (T1's under-specified scope, AC-6's over-literal wording)
  were both caught and corrected during `implement` and are recorded in
  `outcome.md`.
