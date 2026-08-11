# Plan — Publish TCW to PyPI with automated releases

## Ordering rationale

The distribution rename (Task 2) is the change that breaks things, and what it
breaks — the editable-checkout guard in `scripts/session_bootstrap.sh` — fails
**silently**: the probe raises `PackageNotFoundError`, reads as "not editable",
and force-installs over a developer's checkout (spec §2). So the guard is
repaired *before* the rename, accepting both names, with its tests written
first. That makes Task 1 green on today's tree and Task 2 green on tomorrow's,
with no commit in between where the guard is wrong.

Everything after that is additive: two new workflow files touch nothing that
exists, and the documentation block runs last as one pass over the finished
diff.

---

## Task 1 — Make the editable-install guard survive a distribution rename

**Changes:** `scripts/session_bootstrap.sh` (the `tcw_is_editable` heredoc,
lines 47-55), `tests/test_session_bootstrap.py` (the `_EDITABLE_PROBE` copy at
lines 227-231).

Try `tcw-cli` then `tcw`, skipping `PackageNotFoundError`, so one guard covers
installs made either side of the rename. Keep the `sys.path` filter at line 50
— it is load-bearing (a `tcw.egg-info` in the cwd would otherwise answer instead
of the real dist-info).

The two copies of this probe are a known duplication. Do **not** refactor them
into one shared file in this task: the shell script must stay self-contained
(it runs from a plugin cache with no repo around it). Change both, and add a
test asserting they stay identical so the next drift is loud.

**Verify:**

- New test: a fake editable install named `tcw-cli` is detected as editable, and
  `session_bootstrap.sh` exits 0 without invoking `pipx install`. It must not
  depend on the developer's own machine having an editable install — the
  existing `_this_machine_has_an_editable_tcw()` gate is exactly the pattern
  that would let this skip silently.
- New test: the probe text in the script and in the test file match.
- `pytest tests/test_session_bootstrap.py` passes.
- Full `pytest` passes (baseline: 1193 tests, ~197s).

_Acceptance criteria 3, 4._

## Task 2 — Rename the distribution to `tcw-cli`

**Changes:** `pyproject.toml:6` only — `name = "tcw"` → `name = "tcw-cli"`.

Nothing else in `[project]` moves. `[project.scripts]` (line 14) keeps the
command `tcw`; `[tool.setuptools.packages.find] include = ["tcw*"]` keeps the
import package `tcw`; `tcw --version` reads `tcw/__init__.py:1` and is untouched.

`tests/test_cut_version.py:27` writes its own throwaway `pyproject.toml` fixture
and is deliberately left alone — it is testing the bump script, not this
project's name.

**Verify:**

- `python -m build --wheel` (after `rm -rf build/`, see Risks) produces
  `tcw_cli-<version>-py3-none-any.whl`.
- Full `pytest` passes — in particular `tests/test_session_bootstrap.py`, which
  Task 1 made rename-proof.

_Acceptance criterion 1 (build half)._

## Task 3 — Verify the pipx upgrade path, and add a migration step if needed

**Changes:** possibly `scripts/session_bootstrap.sh`; possibly nothing.

The spec's highest-uncertainty item (Risks §1). On a machine with the plugin's
existing pipx package `tcw`, run `pipx install --force <clone>` after the rename
and observe what happens to the `tcw` symlink in the pipx bin dir. Expected —
but **not verified** — is that `--force` repoints it to the new `tcw-cli` venv,
leaving the old `tcw` venv orphaned and harmless.

- If it repoints: record the observation in `outcome.md` and change nothing.
- If it refuses the link (leaving users on a stale `tcw`): add an explicit
  `pipx uninstall tcw` migration ahead of the install in `session_bootstrap.sh`,
  guarded so it only fires when a pipx package literally named `tcw` exists.

Do this **before** the workflows, not after: a discovered migration step changes
`session_bootstrap.sh`, which Task 1 just covered with tests, and it is cheaper
to extend those tests now than to reopen them later.

**Verify:** manual, on a real pipx install — recorded in `outcome.md` with the
observed `pipx list` output before and after. If a migration step is added, a
test in `tests/test_session_bootstrap.py` covering the guarded uninstall.

## Task 4 — Add the test workflow

**Changes:** new `.github/workflows/test.yml`. First file in the repo's first
`.github/` directory.

`on: [push, pull_request, workflow_call]`. `ubuntu-latest`, matrix over Python
3.11 and 3.13 (spec §3 — floor and ceiling; 3.12 omitted deliberately at ~197s
per run). Steps: checkout, `setup-python`, `pip install -e '.[dev]'`, `pytest`.

No `setup-node`: pytest never shells out to Node (verified — spec §3), and
`scripts/check_web_build.mjs` is out of scope for this item.

**Verify:** push the branch and confirm both matrix legs go green on GitHub.
This cannot be checked locally; it is the first thing in the repo that only CI
can prove.

_Acceptance criterion 5._

## Task 5 — Add the release workflow

**Changes:** new `.github/workflows/release.yml`.

`on: push: tags: ['v*']`. Job `test` → `uses: ./.github/workflows/test.yml`.
Job `publish` → `needs: test`, `environment: pypi`,
`permissions: {id-token: write, contents: read}`.

Publish steps: checkout · setup-python 3.11 · tag-vs-version gate · `python -m
build` · `pypa/gh-action-pypi-publish@release/v1` with no token input.

The gate is one comparison, because agreement across the five version-bearing
files is already guarded by `tests/test_plugin_manifests.py:36-45` in the `test`
job:

```sh
python -c "import tcw, os, sys; sys.exit(tcw.__version__ != os.environ['GITHUB_REF_NAME'].removeprefix('v'))"
```

**Verify:**

- Run the gate one-liner locally with `GITHUB_REF_NAME=v0.19.0` (exit 0) and
  `GITHUB_REF_NAME=v9.9.9` (exit 1). This is the only part of criterion 7
  checkable without pushing a bad tag.
- YAML parses; `environment:` value matches the pending-publisher config exactly
  (Task 7) — a mismatch here fails only on the first real upload.

_Acceptance criteria 6, 7._

## Task 6 — Verify the built wheel by hand, before any tag is pushed

**Changes:** none. Pure verification, recorded in `outcome.md`.

Nothing in the pipeline checks this: wheel smoke-testing was declined as a gate
at intake, and `pytest` runs from source, so it would never notice
`tcw/serve/dist` missing from a wheel.

1. `rm -rf build/ dist/` first — a stale `build/` demonstrably packs files that
   no longer exist on disk (spec Risks §4; observed here, two phantom asset
   files).
2. `python -m build`.
3. Install the wheel into an empty venv (not `-e`, not the repo cwd).
4. `tcw --version` matches `tcw/__init__.py`.
5. `tcw/serve/dist/server.cjs` and `tcw/serve/dist/client/index.html` are
   present under the venv's site-packages.

_Acceptance criteria 1, 2._

---

## Documentation Sync

Evaluated against `CLAUDE.md` §Documentation Sync. All four entries fire.

### Task 7 — `README.md` [Public-API]

The install surface changes, which is what this trigger is for.

- Line ~143: `pipx install tcw   # once published` → `pipx install tcw-cli`,
  hedge dropped.
- Lines ~123-124: the "don't also `pip install tcw` separately" drift warning
  restated against `tcw-cli`. The warning stays true; only the name changes.
- Add the release procedure: the one-time PyPI pending-publisher configuration
  (spec §6 — owner `brocef`, repo `TCW`, workflow `release.yml`, environment
  `pypi`), the new `cut_version.py` → `git push --tags` ritual, and the fact
  that a version can only be uploaded to PyPI once, so a failed publish after a
  successful upload is recovered by a patch bump, not a re-run.

### Task 8 — `skills/tcw-plugin/` [Skill-Driven-Component]

The component this skill drives — how `tcw` gets installed and diagnosed —
changes its distribution name.

- `references/setup.md:4` and `:42`: both `pip install tcw` restatements.
- `references/doctor.md`: the install-kind report (steps 1 and 6) must not
  report a `tcw-cli` install as missing, and must name both distributions where
  it currently names one.
- `SKILL.md` itself: check for drift; likely unchanged, but confirm rather than
  assume.

### Task 9 — `docs/release-notes/upcoming.md` [Public-API]

Plain language, no internal module names: TCW can now be installed from PyPI
with `pipx install tcw-cli`, for people who want the command without the agent
plugin. Say plainly that the name is `tcw-cli` rather than `tcw` because `tcw`
was already taken, and that the installed command is still `tcw`.

### Task 10 — `docs/changelogs/upcoming.md` [Any-Code-Change]

Grouped:

- **Added** — `.github/workflows/test.yml` and `.github/workflows/release.yml`;
  PyPI publishing via Trusted Publishing on `v*` tags.
- **Changed** — distribution renamed `tcw` → `tcw-cli` (command and import
  package unchanged).
- **Fixed** — `session_bootstrap.sh`'s editable-install guard now resolves the
  distribution under either name, so a rename cannot silently disarm it.

### Task 11 — Ledger flip at completion

`docs/work/.../capabilities.yaml` declares one `new:` and two `changed:` paths.
At `complete`: `tcw capabilities set cli/install-from-pypi --status Supported`,
and re-read `plugin/bootstrap-the-cli` and `plugin/diagnose-the-install` for
wording that Task 8's changes made untrue. The completion gate blocks on the
`new:` entry still reading `Missing`.

---

## Verification

**The suite covers:** the editable guard under both distribution names (Task 1),
the five-file version lockstep (`tests/test_plugin_manifests.py`, already
present), and everything else in the existing 1193 tests.

**The suite cannot cover, so these are explicit manual gates:**

| What                                                | How                                                     | Task |
| --------------------------------------------------- | ------------------------------------------------------- | ---- |
| Both CI matrix legs green                           | push the branch, read the GitHub checks                 | 4    |
| Wheel installs and carries the prebuilt web app     | clean build → empty venv → `tcw --version` + file check | 6    |
| pipx `--force` repoints an existing `tcw` symlink   | real pipx, `pipx list` before/after                     | 3    |
| Trusted Publishing actually authenticates           | **only provable by the first real tag push**            | —    |

The last row has no rehearsal. The first successful run of the release workflow
is also the first real upload, and the version it uploads is spent forever. The
mitigation is that the pending-publisher fields are written down in Task 7 and
checked against `release.yml` character by character, rather than recalled.

**Before the first tag push**, in order: Task 6's wheel check must have passed
locally, Task 4's workflow must be green, and the requester must have created
the pending publisher on pypi.org — the agent cannot do that step.

## Notes

- No blockers to record on this item. The reverse dependency is recorded:
  `2026-08-11-install-the-plugin-s-cli-from-pypi-instead-of-its-own-clone` is
  `blocked_by` this item, so `tcw work start` refuses it until this completes.
- Tasks 3 and 6 produce observations rather than diffs. They are tasks and not
  Verification-section bullets because each can change the code — Task 3 may add
  a migration step, Task 6 may expose a packaging gap — and a plan that hides
  that in a checklist mis-sequences it.
