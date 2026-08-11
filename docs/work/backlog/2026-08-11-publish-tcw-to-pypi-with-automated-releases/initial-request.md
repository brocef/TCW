# Publish TCW to PyPI with automated releases

## Product changes

A second, harness-independent way to get `tcw`: `pip install` / `pipx install`
from PyPI, for people who want the CLI without adopting it as a Claude Code or
Codex plugin. The plugin install path is unchanged; this adds a peer to it.

## Technical changes

Make the repo produce a publishable distribution, and add the repo's first
GitHub Actions workflows: a test workflow, and a release workflow that builds
and uploads to PyPI when a version tag is pushed.

## Meta changes

Moves publishing from "a human step, done by hand" (the current release ritual)
to "tag and push"; and establishes CI in a repo that has none today.

---

## Requested outcome

TCW is currently installable only as an agent plugin — via the Claude
`/plugin marketplace` flow, the Codex marketplace, or a manual clone. A user who
wants the `tcw` CLI on their PATH and nothing else has no clean path.

I made a PyPI account. Two coupled asks:

1. **Publish TCW to PyPI**, so `pipx install …` works for people who do not want
   the agent-plugin route.
2. **Automate it**, so pushing a new version to GitHub publishes it, rather than
   requiring a manual upload each release.

## The blocking discovery: `tcw` is taken on PyPI

`https://pypi.org/project/tcw/` is an unrelated package — "tiny contest winners
application" by J Leary, 23 releases, last published 2023-01. The name is not
available.

Checked and free at intake: `tcw-cli`, `tcw-framework`,
`taxonomy-capabilities-work`, `tcw-tool`, `tcwkit`.

The PyPI *distribution* name is independent of the import package and the
console-script name, so a differently-named distribution still installs `tcw` on
PATH and still supports `import tcw`.

## Decisions already made

- **Distribution name: `tcw-cli`.** `pip install tcw-cli` → `tcw` command,
  `import tcw`. Explicitly rejected: contesting the existing `tcw` name via
  PyPI's PEP 541 name-transfer process — slow, uncertain, and it would block
  publishing indefinitely. Not pursued in this item.
- **Auth: Trusted Publishing (OIDC).** GitHub Actions mints a short-lived token
  from PyPI; no long-lived API token stored in repo secrets, nothing to rotate.
  Requires a one-time publisher configuration on pypi.org that only the account
  owner can perform.
- **Trigger: push of a `v*` tag.** `scripts/cut_version.py` already creates that
  tag, so the release ritual becomes `cut_version.py` then `git push --tags`.
  Explicitly rejected: gating on a drafted GitHub Release, and a two-stage
  TestPyPI-then-promote flow — both add a human gate the request is trying to
  remove.
- **Gates before upload:** the publish job depends on (a) pytest passing and
  (b) the pushed tag matching `project.version` in `pyproject.toml`. Since the
  repo has no CI at all, the test gate also means standing up a test workflow
  that runs on ordinary pushes and PRs.

## Constraints

- The repo has **no `.github/` directory** — there is no existing CI to extend.
  Both workflows are new.
- `tcw/serve/dist/` (the prebuilt web client and server) **is committed to git**,
  so a wheel build needs no Node/pnpm step in CI. It does need to actually land
  in the wheel — `pyproject.toml` declares it as `package-data`, and that
  declaration is the only thing making it so.
- The five version-bearing files must stay in lockstep (see `CLAUDE.md`
  §Versioning). The tag-matches-version gate must not become a sixth thing to
  keep in sync by hand.
- The one-time PyPI-side publisher setup is the account owner's to do; the work
  item can prepare and document it but cannot perform it.

## Non-goals

- No PEP 541 claim on the `tcw` name.
- No TestPyPI staging flow.
- No change to the plugin install paths (Claude marketplace, Codex marketplace,
  or the session-start pipx install from the plugin clone).
- No release-signing, SBOM, or provenance-attestation work.

## Known drift to fold in

`README.md` already anticipates a PyPI release with the wrong name, and warns
against a conflict that will not exist as described:

- Line ~143: `pipx install tcw   # once published` — wrong distribution name.
- Lines ~123–124: "don't also `pip install tcw` separately, or the two can
  drift" — the collision advice needs restating against `tcw-cli`, and
  `/tcw-doctor`'s drift detection should be re-read against the real installed
  name.

## Open questions for spec

- How does the tag-vs-version check read the version without adding a sixth
  place the version lives? (`tcw/__init__.py`, `pyproject.toml`, and the built
  metadata are all candidates; `scripts/cut_version.py` already knows all five.)
- Does a pip-installed `tcw-cli` collide with the plugin's pipx-managed `tcw` on
  PATH, and does `/tcw-doctor` (per `skills/tcw-plugin/`) detect and report that
  correctly once the distribution name differs from the command name?
- Which Python versions and OSes does the test workflow run? `requires-python`
  is `>=3.11`; a matrix costs CI minutes the repo has never spent.
- Should the wheel be smoke-tested (install in a clean venv, run `tcw
  --version`) before upload? Considered at intake and **not** selected as a
  gate; noted here because pytest runs from source and would not catch
  `tcw/serve/dist/` missing from the wheel. Spec should decide whether to
  re-add it or accept the risk deliberately.

## Notes

- Asked the requester for reference material; none provided. Use the official
  PyPI Trusted Publishing documentation and `pypa/gh-action-pypi-publish` as the
  starting sources.
- Facts verified at intake on 2026-08-11: PyPI name availability (live API), the
  absence of `.github/`, and `tcw/serve/dist/` being tracked by git (5 files).
