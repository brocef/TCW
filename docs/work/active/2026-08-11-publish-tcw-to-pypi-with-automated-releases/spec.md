# Spec — Publish TCW to PyPI with automated releases

## Capability changes

Planned ledger deltas only; nothing is written to the ledger until `complete`.
Recorded in this item's `capabilities.yaml`.

**New — `cli/install-from-pypi`** ("Install the CLI from PyPI", `cap-f118a5`,
seeded `Missing`, `Subject: cli`, `Planning doc` set to this item). A user who
wants only the `tcw` command installs it with `pipx install tcw-cli` — no
harness, no marketplace, no clone. Seeded at spec time because the ledger's
existing install entries (`plugin/install-as-a-plugin`,
`plugin/bootstrap-the-cli`) describe only the plugin route; nothing in the
ledger contradicts a peer route.

No taxonomy work: `plugin/install-as-a-plugin` carries `Subject: cli` and no
`Feature`, and none of the seven registered Features covers installation. The
new entry follows that precedent rather than inventing a Feature.

**Changed — `plugin/bootstrap-the-cli`.** Its wording ("a developer's
`pip install -e` checkout … is left alone") stays true only if the
editable-install guard keeps working across the distribution rename; see
Design §2. The user-visible sentence should not need to change, but the
capability is listed as changed because the behavior behind it does.

**Changed — `plugin/diagnose-the-install`.** `/tcw-doctor` reports "how it was
installed (pipx / editable / missing)"; after the rename it must not report a
`tcw-cli` install as "missing".

## Problem

TCW is installable only as an agent plugin: the Claude `/plugin marketplace`
flow, the Codex marketplace, or a manual clone (`README.md:95-137`). A user who
wants the `tcw` CLI and nothing else has no supported path — `README.md:143`
already promises `pipx install tcw` "once published", and that promise is both
unfulfilled and, as written, unfulfillable.

Two things block it:

1. **The name `tcw` is taken on PyPI.** `https://pypi.org/project/tcw/` is
   "tiny contest winners application" by J Leary — 23 releases, latest `0.1.13`,
   last published 2023-01-01. Verified live against the PyPI JSON API on
   2026-08-11. `pyproject.toml:6` declares `name = "tcw"`, so the project as
   configured cannot be uploaded at all.
2. **There is no CI.** The repo has no `.github/` directory. Releases are cut by
   `scripts/cut_version.py`, which commits and tags but deliberately does not
   push — "publishing stays a human step" (`scripts/cut_version.py:8-9`).

## Goals

1. Publish TCW to PyPI under the distribution name **`tcw-cli`**, preserving the
   `tcw` console script and the `tcw` import package.
2. Publish automatically when a `v*` tag is pushed, gated on the test suite
   passing and on the tag matching the declared version.
3. Leave every existing install path working, and leave the editable-checkout
   protection in `scripts/session_bootstrap.sh` genuinely intact — not merely
   passing.

## Non-goals

- **No PEP 541 claim** on the `tcw` name. Slow, uncertain, and it would block
  publishing indefinitely.
- **No TestPyPI staging flow**, no release signing, no SBOM, no provenance
  attestation.
- **No change to how the plugin installs the CLI.** `session_bootstrap.sh` keeps
  installing from the plugin clone. Switching it to install from PyPI — and
  stripping `tcw/` from the plugin package entirely — is a follow-on item that
  this one blocks. It is untestable before a real release exists, and it trades
  today's offline session-start for a network dependency; that deserves its own
  spec. Scoped out deliberately on 2026-08-11 after the requester raised it.
- **No multi-OS CI.** See Design §4 for why Linux-only.

## Design

### 1. Rename the distribution to `tcw-cli`

`pyproject.toml:6` — `name = "tcw"` → `name = "tcw-cli"`. Nothing else in
`[project]` moves: `[project.scripts] tcw = "tcw.cli:main"` (`pyproject.toml:14`)
keeps the command named `tcw`, and `[tool.setuptools.packages.find]
include = ["tcw*"]` keeps the import package named `tcw`.

`tcw --version` is unaffected — it reads `tcw.__version__`
(`tcw/__init__.py:1`), not installed metadata, so no version source moves.

**Verified**: building a wheel from the current tree produces 7 `tcw/serve/dist`
entries (`server.cjs`, `client/index.html`, `client/theme-init.js`, and the
hashed `assets/*`), so the `[tool.setuptools.package-data] "tcw.serve"`
declaration at `pyproject.toml:20-21` does put the prebuilt web app in the
wheel. That claim in `README.md:150-152` holds.

### 2. Repair the editable-install guard, which the rename breaks

`scripts/session_bootstrap.sh:47-55` decides whether a `tcw` on PATH is a
developer's editable checkout by calling `importlib.metadata.distribution("tcw")`
(line 52). `importlib.metadata` looks distributions up by **distribution** name,
so after the rename that call raises `PackageNotFoundError` on every
`tcw-cli` install. The probe exits non-zero, `tcw_is_editable` reads false, and
step 3 (lines 71-74) proceeds to `pipx install --force` **over a developer's
editable checkout** — silently, every session. That is precisely the failure the
comment at lines 25-26 was written to prevent.

Fix: try both names, newest first, so the guard covers installs made either side
of the rename:

```python
for name in ("tcw-cli", "tcw"):
    try:
        raw = distribution(name).read_text("direct_url.json") or "{}"
    except PackageNotFoundError:
        continue
    ...
```

`tests/test_session_bootstrap.py:227-231` holds a **second copy** of the same
probe, used by `_this_machine_has_an_editable_tcw()` to decide whether to run
the real-install test. After the rename that copy returns `False`, so the test
*skips* rather than fails — the rename would disarm a guard test without any red
output. Both copies must change together.

### 3. Test workflow — `.github/workflows/test.yml`

New. Runs on push and pull_request, and exposes `workflow_call` so the release
workflow can depend on it rather than duplicating it.

- `ubuntu-latest`, matrix over Python **3.11** (the `requires-python` floor,
  `pyproject.toml:9`) and **3.13**. 3.12 omitted: the suite is 1193 tests at
  ~197s wall clock (measured locally, 2026-08-11), and testing floor + ceiling
  catches both back-compat and forward-compat breakage.
- `pip install -e .[dev]`, then `pytest`.
- No Node setup: `grep -rn "\"node\"|'node'|pnpm|npx" tests/*.py` returns
  nothing, and `tests/test_serve_runtime.py:23-39` monkeypatches
  `shutil.which`. The Node-dependent path is `scripts/check_web_build.mjs`,
  which is not part of pytest and stays out of CI in this item.

### 4. Linux-only, deliberately

Several tests shell out to bash scripts — `tests/test_session_bootstrap.py`
drives `scripts/session_bootstrap.sh`, and `tests/test_unpushed_version_script.py`
drives `skills/documentation-sync/scripts/unpushed-version.sh`
(lines 12-16). A Windows runner would fail on those for reasons unrelated to
what the workflow is meant to catch. macOS would pass but doubles the minute
spend on a repo that has never spent any.

### 5. Release workflow — `.github/workflows/release.yml`

New. `on: push: tags: ['v*']`.

- **Job `test`**: `uses: ./.github/workflows/test.yml`.
- **Job `publish`**: `needs: test`, `environment: pypi`,
  `permissions: id-token: write` (required for OIDC), `contents: read`.
    1. Checkout, set up Python 3.11.
    2. **Tag-vs-version gate**, one comparison:

        ```sh
        python -c "import tcw, os, sys; sys.exit(tcw.__version__ != os.environ['GITHUB_REF_NAME'].removeprefix('v'))"
        ```

        This answers the request's open question about a sixth version source:
        there isn't one. Agreement *across* the five version-bearing files is
        already guarded by `tests/test_plugin_manifests.py:36-45`, which runs in
        the `test` job. The release workflow therefore only needs to check the
        tag against one of them.
    3. `python -m build`, then `pypa/gh-action-pypi-publish@release/v1` with no
       token input — Trusted Publishing supplies the credential.

### 6. One-time PyPI-side setup (requester's, not the agent's)

On pypi.org, add a **pending publisher** for a project named `tcw-cli`:
owner `brocef`, repository `TCW`, workflow filename `release.yml`, environment
name `pypi`. Pending (rather than project-scoped) because the project does not
exist on PyPI until the first upload. The workflow's `environment:` value must
match this exactly or the first publish fails authentication.

This is written into the item's documentation deliverable so it is not lore.

### 7. Documentation

- `README.md:143` — `pipx install tcw` → `pipx install tcw-cli`, and drop the
  "once published" hedge.
- `README.md:123-124` — "don't also `pip install tcw` separately" restated
  against `tcw-cli`; the drift warning stays true, only the name changes.
- `skills/tcw-plugin/references/setup.md:4` and `:42` — same two restatements.
- `skills/tcw-plugin/references/doctor.md` — the install-kind report (step 1,
  step 6) must recognize `tcw-cli`; check whether the procedure names the
  distribution anywhere it now needs to name both.
- `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` per the
  CLAUDE.md Documentation Sync contract.
- A short release procedure note (README or `CONTRIBUTING`-equivalent) covering
  §6 and the new "cut, then `git push --tags`" ritual.

### 8. Sibling sweep

The rename's blast radius was enumerated repo-wide, not inherited from the
request: `grep -rn 'distribution("tcw")|pip install tcw|pipx install tcw|name = "tcw"'`
across `*.py *.sh *.md *.toml *.json` yields exactly eight sites — the eight
named in §1, §2, §7, plus `tests/test_cut_version.py:27`, which writes a
throwaway `pyproject.toml` fixture and is unaffected by the real name.

## Acceptance criteria

1. `pyproject.toml` declares `name = "tcw-cli"`; a wheel built from a clean
   checkout is named `tcw_cli-<version>-py3-none-any.whl`, and installing it in
   an empty venv puts a working `tcw` on PATH such that `tcw --version` prints
   the version in `tcw/__init__.py`.
2. That same installed wheel contains `tcw/serve/dist/server.cjs` and
   `tcw/serve/dist/client/index.html` under the venv's site-packages.
3. `scripts/session_bootstrap.sh`, run against a machine whose `tcw` is an
   editable install of a **`tcw-cli`**-named checkout, exits 0 without invoking
   `pipx install`. Covered by an addition to `tests/test_session_bootstrap.py`
   that does not depend on the developer's own machine having an editable
   install.
4. `tests/test_session_bootstrap.py`'s `_this_machine_has_an_editable_tcw()`
   returns `True` on a machine with an editable `tcw-cli` — i.e. the real-install
   test is not silently skipped after the rename.
5. `.github/workflows/test.yml` runs `pytest` on `ubuntu-latest` for Python 3.11
   and 3.13, on push and on pull_request, and is callable via `workflow_call`.
6. `.github/workflows/release.yml` triggers only on `v*` tags, and its publish
   job declares `permissions: id-token: write` and `environment: pypi`.
7. Pushing a tag whose name does not match `tcw.__version__` fails the publish
   job at the gate step, before any upload is attempted.
8. `pytest` passes in full (1193 tests at time of spec).
9. No file outside `docs/work/` and `docs/capabilities/` still says
   `pip install tcw` or `pipx install tcw` referring to this project's
   distribution; the eight sites from §8 are all resolved.
10. `tcw validate` exits 0.
11. `docs/release-notes/upcoming.md` describes the new install path in plain
    language, and `docs/changelogs/upcoming.md` records the rename under
    Changed.

## Risks

- **pipx app-name collision on upgrade.** A user with the plugin's existing
  pipx package `tcw` will, on their next session, have `session_bootstrap.sh`
  run `pipx install --force <clone>`, which now installs a package named
  `tcw-cli`. Both venvs provide a `tcw` binary in the pipx bin dir. `--force` is
  documented to modify files in `PIPX_BIN_DIR`, so the symlink should be
  repointed and the old `tcw` venv left orphaned but harmless — **this is
  reasoning, not a verified observation.** It must be verified against a real
  pipx before release, and if `--force` instead refuses the link, the bootstrap
  needs an explicit `pipx uninstall tcw` migration step. Highest-uncertainty
  item in this spec.
- **The publish gate cannot be rehearsed.** Trusted Publishing's first
  successful run is also its first real upload; a misconfigured `environment:`
  or workflow filename surfaces only then. Mitigated by the pending-publisher
  fields in §6 being written down and checked against the workflow file, not
  recalled.
- **A version can only be uploaded to PyPI once.** A failed publish after a
  successful upload cannot be retried at the same version — recovery is a patch
  bump, not a re-run. Worth stating in the release procedure note.
- **`python -m build` reuses a stale `build/` directory.** Building locally in
  this checkout produced a wheel containing two asset files that no longer exist
  on disk (`assets/index-CCR-WMWB.css`, `assets/index-D8ggAUL-.js`), left over
  from an earlier build. CI on a fresh checkout is unaffected, but any local
  pre-release verification must clear `build/` first or it verifies a fiction.
- **Untracked-but-packaged files.** `tcw/serve/dist/client/.vite/manifest.json`
  exists on disk and is gitignored (`.gitignore` `.vite/`), while
  `git ls-files tcw/serve/dist` tracks 5 files. CI builds from tracked content
  only, so the wheel CI produces is not byte-identical to a local one. Not
  believed to matter — `.vite/manifest.json` is a build-tool artifact, not a
  runtime asset — but it means "it worked when I built it here" is weak
  evidence.
- **Wheel smoke-testing was declined as a gate** at intake. Criteria 1 and 2
  therefore have to be met by a human or a test before the first tag is pushed,
  because nothing in the pipeline will check them. `pytest` runs from source and
  would not notice `tcw/serve/dist` missing from a wheel.

## Notes

- Facts verified on 2026-08-11 by direct inspection: PyPI name availability
  (live JSON API — `tcw` occupied; `tcw-cli`, `tcw-framework`,
  `taxonomy-capabilities-work`, `tcw-tool`, `tcwkit` all 404); absence of
  `.github/`; `tcw/serve/dist` wheel packaging (built and inspected); test-suite
  size and duration (`1193 passed in 196.61s`); the eight-site rename blast
  radius (repo-wide grep).
- **Assumption, unverified:** that `pipx install --force` repoints an existing
  same-named binary owned by a different pipx package. See Risks.
- The requester provided no reference material; sources are the PyPI Trusted
  Publishing documentation and `pypa/gh-action-pypi-publish`.
