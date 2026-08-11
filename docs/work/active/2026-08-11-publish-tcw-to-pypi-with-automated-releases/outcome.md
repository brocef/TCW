# Outcome — Publish TCW to PyPI with automated releases

**Suite:** 1201 passed in 192.08s. `tcw validate` OK, `tcw capabilities check` OK.
Baseline at spec time was 1193; the delta is +7 probe tests and +1 from
`test_documented_cli_surface.py`, which parametrizes per documented file and
picked up the `cli/install-from-pypi` description seeded at the spec stage.

## What shipped, task by task

| Task | Commit | Result |
| --- | --- | --- |
| 1 — editable guard under either name | `ccfb2ca` | shipped, plus a duplication removed |
| 2 — rename to `tcw-cli` | `d7a2c0a` | shipped |
| 3 — pipx upgrade path | — | verified; no code change needed |
| 4 — test workflow | `93b923f` | shipped, matrix corrected |
| 5 — release workflow | `3479f37` | shipped, gate implemented differently |
| 6 — wheel verification | — | verified; first attempt was invalid |
| 7–10 — documentation | `3b87848` | shipped, one addition beyond plan |

### Task 1 — `scripts/session_bootstrap.sh`, `tests/test_session_bootstrap.py`

The probe now tries `("tcw-cli", "tcw")`, first name found deciding. Confirmed
the bug was real before fixing it: the old single-name probe, run against a
synthetic editable `tcw-cli` dist-info, exits 1 — "not editable" — which is the
answer that triggers `pipx install --force` over a developer's checkout.

**Deviation from plan.** The plan said to change both copies of the probe and add
a test asserting they stay identical. Instead the test file no longer holds a
copy: `_editable_probe()` extracts the heredoc from the shell script and asserts
exactly one `<<'PY'` block exists. Removing the duplication is strictly better
than policing it, and it guarantees the text under test is the text that ships.

Seven parametrized cases now run the probe under `python -S` against synthetic
`dist-info` trees. `-S` is load-bearing: this interpreter has a real editable
`tcw` installed, which would answer for every case if site-packages were visible.
The last two cases pin precedence in both directions, which is the property that
justified choosing the ordered loop over a name-agnostic entry-point lookup.

Worth recording why this coverage was missing: the pre-existing fixture tests
stub the owning interpreter with `exit 0`/`exit 1`, so they prove the script's
*branches* without running the Python that chooses between them. The only test
that ran the probe was `test_real_editable_checkout_is_left_alone`, and on this
machine it takes an earlier branch (see Notes) and never reaches it.

### Task 2 — `pyproject.toml`

`name = "tcw"` → `name = "tcw-cli"`, one line. Clean build produces
`tcw_cli-0.19.0-py3-none-any.whl` with the 5 tracked `tcw/serve/dist` files and
`tcw = tcw.cli:main`.

### Task 3 — pipx upgrade path: **verified, no change**

The spec's highest-uncertainty risk, resolved in the direction the spec reasoned.

Method: `pipx install <pre-rename clone>` (package `tcw`, from a `git archive` of
the pre-rename tree), then `pipx install --force /Users/brian/Projects/TCW`
(package `tcw-cli`) — exactly what `session_bootstrap.sh:82` runs.

Observed:

- `--force` **repointed** `~/.local/bin/tcw` from `venvs/tcw/bin/tcw` to
  `venvs/tcw-cli/bin/tcw`.
- Both packages then existed; the old `tcw` venv was orphaned.
- The orphan **cannot reclaim the link**: `pipx upgrade tcw` printed
  "…points to venvs/tcw-cli/bin/tcw, not venvs/tcw/bin/tcw. Not modifying."
- Both install specs are local paths, so `upgrade` resolves from the path and
  never reaches PyPI's unrelated `tcw` project.

No migration step was added — the plan's conditional ("if it refuses the link,
add `pipx uninstall tcw`") did not fire. Machine restored: both packages
uninstalled, `~/.local/bin/tcw` gone, `command -v tcw` back to the pyenv shim
reporting 0.19.0.

**Unplanned finding folded in:** the orphan is observable in `pipx list` and
would puzzle anyone diagnosing an install, so `doctor.md` gained a step covering
it — report as clutter, do not remove for the user. This stays consistent with
the script's own philosophy (`session_bootstrap.sh:76-78`): choosing what to do
with someone's Python environment is a judgment call that does not happen
silently.

### Task 4 — `.github/workflows/test.yml`

**Correction to the plan.** The plan specified a 3.11 + 3.13 matrix, calling 3.13
"the current release". Local Python is **3.14.6** — so that matrix would have
topped out *below* the interpreter the maintainer develops on, testing a
configuration nobody runs. Shipped as **3.11 + 3.14**.

`push` is scoped to `branches: ['**']`; a bare `push:` also fires on tags and
would run the suite twice per release.

### Task 5 — `.github/workflows/release.yml`

**Deviation from plan.** The plan's gate compared the tag against
`tcw.__version__`. Shipped comparing against `project.version` in
`pyproject.toml` instead: that is the version the wheel actually carries, so it
is the one the tag must match. `tcw/__init__.py` agreeing with it is already
`tests/test_plugin_manifests.py:36-45`'s job, and that runs in the gating `test`
job. Still one comparison, not five.

Verified locally: `GITHUB_REF_NAME=v0.19.0` → exit 0; `v9.9.9` → exit 1 with
`tag '9.9.9' does not match pyproject version '0.19.0'`. Both workflow files
parse, and `publish` declares `environment: pypi` and
`permissions: {id-token: write, contents: read}`.

### Task 6 — wheel verification: **verified, no change**

**The first attempt was invalid and is recorded because it nearly passed.** The
check resolved the installed package's location by running the venv's Python
with cwd set to the repo, so `import tcw` found `/Users/brian/Projects/TCW/tcw`
— the source checkout — and "verified" the repo rather than the wheel. Re-run
from a neutral cwd. This is the same trap the probe's `sys.path` filter exists to
prevent, which is a decent argument that the filter's comment is not paranoid.

Valid result: import resolves to the venv's `site-packages/tcw`,
`serve/dist/server.cjs` (1372999 bytes) and `serve/dist/client/index.html` are
present, `tcw --version` prints `tcw 0.19.0`, and `tcw --help` runs.

### Tasks 7–10 — documentation

All four Documentation Sync entries fired, as predicted. Beyond the planned
edits, `README.md` gained the **Releasing** section (cut-and-push ritual, the
one-time pypi.org pending-publisher and GitHub environment settings as a table,
and the warning that a PyPI version number is spent on upload regardless of what
the job does afterwards). `skills/tcw-plugin/SKILL.md` was checked and names no
distribution — unchanged, as the plan guessed.

## What the spec and plan got wrong

1. **Matrix ceiling below the development interpreter** (plan §Task 4). Corrected
   to 3.14.
2. **The tag gate's version source** (plan §Task 5). `pyproject.toml`, not
   `tcw.__version__`.
3. **"Add a test asserting the two probe copies stay identical"** (plan §Task 1).
   Extracting the probe removes the duplication instead.
4. **Spec Risks §5 — "untracked-but-packaged files"** — resolved as a non-issue.
   `tcw/serve/dist/client/.vite/manifest.json` is not packed, because setuptools'
   `dist/**/*` glob skips dot-directories.
5. **Spec Risks §4 — stale `build/`** — confirmed real. The pre-work wheel
   contained 7 `serve/dist` entries including two asset files no longer on disk;
   a clean build has exactly the 5 tracked files. `rm -rf build/` is mandatory
   before any local pre-release check.

## Still unproven, deliberately

- **Both CI legs green.** Nothing here has run on GitHub — there is no `.github/`
  in any pushed commit yet. First push proves it.
- **Trusted Publishing authenticates.** Unrehearsable: the first successful run
  of the release workflow is also the first real upload. Mitigated by the
  pending-publisher values being written into `README.md` rather than recalled.
- **Acceptance criterion 7's other half.** The gate logic was exercised both
  directions locally, but "a mismatched tag fails the publish job" has not been
  observed in CI.

## Notes

- `session_bootstrap.sh` is inert on this machine: `tcw` is
  `/Users/brian/.pyenv/shims/tcw` with a `#!/usr/bin/env bash` shebang, so
  `tcw_interpreter()` returns 1 and the script exits before the probe; and
  `pipx` was absent until Task 3 required installing it. Everything about Tasks 1
  and 3 therefore had to be constructed rather than observed.
- PATH order here puts pyenv shims (position 5) ahead of `~/.local/bin`
  (position 26), so the Task 3 pipx installs never shadowed the real `tcw`.
- Scope held. The plugin/PyPI separation the requester raised mid-planning went
  to `2026-08-11-install-the-plugin-s-cli-from-pypi-instead-of-its-own-clone`,
  which is `blocked_by` this item.
