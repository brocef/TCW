# Separate the Agent Plugin from the Python CLI Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a self-contained, Python-free plugin root while keeping the CLI as the separately installed `tcw-cli` distribution.

**Architecture:** Move agent-facing assets beneath `plugin/`, leave only marketplace discovery metadata at the repository root, and point both harnesses at the new root. Use a plain VERSION token for bootstrap and retain lockstep release automation across package and plugin metadata.

**Tech Stack:** Claude/Codex JSON manifests, Agentskills Markdown, Bash bootstrap, Python release tooling and pytest.

---

### Task 1: Define the plugin payload boundary in tests

**Files:**
- Modify: `tests/test_plugin_manifests.py`
- Modify: `tests/test_session_bootstrap.py`

- [ ] **Step 1: Add failing marketplace-source assertions**

Assert the Claude marketplace plugin source is `./plugin` and the Agents marketplace local path is `plugin`; resolve both to the same directory.

- [ ] **Step 2: Add payload allow/deny assertions**

Assert `plugin/` contains `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `skills`, `commands`, `agents`, `hooks/hooks.json`, `scripts/session_bootstrap.sh`, and `VERSION`. Walk the payload and reject `*.py`, `pyproject.toml`, `tests`, `tcw`, and web source directories. Assert the SessionStart hook still resolves its bootstrap command within the payload.

- [ ] **Step 3: Repoint bootstrap fixtures to VERSION**

Change fixture plugin roots to write `VERSION` and assert sentinel bytes match it. Add a regression assertion that a root containing only VERSION plus bootstrap is sufficient.

- [ ] **Step 4: Run tests red and commit**

Run: `pytest tests/test_plugin_manifests.py tests/test_session_bootstrap.py -q`

Expected: FAIL because `plugin/` does not exist and bootstrap requires `tcw/__init__.py`.

```bash
git add tests/test_plugin_manifests.py tests/test_session_bootstrap.py
git commit -m "test: define a python-free plugin payload"
```

### Task 2: Move the authoritative plugin assets

**Files:**
- Create: `plugin/`
- Move: `.claude-plugin/plugin.json` → `plugin/.claude-plugin/plugin.json`
- Move: `.codex-plugin/plugin.json` → `plugin/.codex-plugin/plugin.json`
- Move: `skills/` → `plugin/skills/`
- Move: `commands/` → `plugin/commands/`
- Move: `agents/` → `plugin/agents/`
- Move: `hooks/` → `plugin/hooks/`
- Move: `scripts/session_bootstrap.sh` → `plugin/scripts/session_bootstrap.sh`
- Create: `plugin/VERSION`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.agents/plugins/marketplace.json`

- [ ] **Step 1: Move files with Git history**

Use `mkdir -p` and `git mv`, preserving executable mode on bootstrap. Write the current version plus newline to `plugin/VERSION`.

- [ ] **Step 2: Repoint marketplace sources**

Set Claude `plugins[0].source` to `./plugin` and Agents `plugins[0].source.path` to `plugin`. Keep names and installation policy stable.

- [ ] **Step 3: Repair internal relative links**

Run `rg` for root-assuming `skills/`, `commands/`, `agents/`, and `scripts/session_bootstrap.sh` references. Update only paths whose base changed; keep plugin-internal links relative.

- [ ] **Step 4: Run manifest tests**

Run: `pytest tests/test_plugin_manifests.py -q`

Expected: marketplace and payload tests pass; version/bootstrap tests may remain red until later tasks.

- [ ] **Step 5: Commit the structural move**

```bash
git add -A plugin .claude-plugin .agents skills commands agents hooks scripts/session_bootstrap.sh
git commit -m "refactor: isolate the installable agent plugin"
```

### Task 3: Switch bootstrap to the plugin VERSION token

**Files:**
- Modify: `plugin/scripts/session_bootstrap.sh`
- Modify: `tests/test_session_bootstrap.py`
- Modify: `plugin/skills/tcw-plugin/references/setup.md`
- Modify: `plugin/skills/tcw-plugin/references/doctor.md`
- Modify: `plugin/commands/tcw-doctor.md`

- [ ] **Step 1: Replace every Python marker operation**

Change root validation, `cmp`, and sentinel `cp` from `$root/tcw/__init__.py` to `$root/VERSION`. Preserve ordering and all ownership/editable/pipx safety branches.

- [ ] **Step 2: Update setup and repair instructions**

Name VERSION as the trigger token and `plugin/scripts/session_bootstrap.sh` as the repository path while keeping runtime examples relative to the installed plugin root.

- [ ] **Step 3: Run bootstrap tests**

Run: `pytest tests/test_session_bootstrap.py -q`

Expected: PASS, including empty root, steady state, editable install, foreign wrapper, failure/retry, and sentinel tests.

- [ ] **Step 4: Commit bootstrap independence**

```bash
git add plugin/scripts plugin/skills/tcw-plugin plugin/commands/tcw-doctor.md tests/test_session_bootstrap.py
git commit -m "fix: version plugin bootstrap without python source"
```

### Task 4: Teach release automation the new layout

**Files:**
- Modify: `scripts/cut_version.py`
- Modify: `tests/test_cut_version.py`
- Modify: `tests/test_plugin_manifests.py`
- Modify: `AGENTS.md`

- [ ] **Step 1: Update version paths and add VERSION**

Point manifest substitutions at `plugin/.claude-plugin/plugin.json` and `plugin/.codex-plugin/plugin.json`; retain marketplace and Python versions in the drift check.

`plugin/VERSION` needs a second code path, not a new dict entry: `VERSION_FILES` maps a path to a `"version": "(…)"` regex and the bump reuses those patterns (`scripts/cut_version.py:22-27, 86-88`), while VERSION is a bare version string plus newline. Give it its own read (whole-file strip) and write (overwrite), and make sure the **drift check** covers it too — a marker the bump writes but the drift check ignores is the one that silently rots.

- [ ] **Step 2: Extend isolated cut-version tests**

Seed the new tree, run patch and explicit bumps, and assert all six version-bearing locations agree while Agents marketplace remains versionless.

- [ ] **Step 3: Update repository versioning instructions**

List the new paths and VERSION token accurately; keep `python scripts/cut_version.py ...` as the sole release command.

- [ ] **Step 4: Run release and manifest tests**

Run: `pytest tests/test_cut_version.py tests/test_plugin_manifests.py -q`

Expected: PASS.

- [ ] **Step 5: Commit version tooling**

```bash
git add scripts/cut_version.py tests/test_cut_version.py tests/test_plugin_manifests.py AGENTS.md
git commit -m "build: version the isolated plugin payload"
```

### Task 5: Repair repository-wide path consumers

**Files:**
- Modify: `tests/test_skill_lifecycle_parity.py:25-26` — `SKILL`/`REFS` are `REPO / "skills/tcw-work/…"` constants that break on the move; the only known-in-advance consumer, so fix it directly rather than waiting for the audit to rediscover it
- Modify: further tests and scripts found by the stale-path audit
- Modify: repository docs outside the final Documentation Sync set when they contain broken literal paths

- [ ] **Step 1: Audit stale paths**

Run: `rg -n '(\.claude-plugin/plugin|\.codex-plugin/plugin|skills/|commands/|agents/|hooks/|scripts/session_bootstrap)' --glob '!plugin/**'`

Expected: every match is classified as intentionally repository-root metadata, a development reference needing `plugin/`, or test fixture text.

- [ ] **Step 2: Update programmatic consumers**

Repair exact paths in tests/scripts and keep imports/package discovery untouched. Do not add symlink compatibility shims that would put duplicate plugin roots back into the install surface.

- [ ] **Step 3: Run the full suite and commit repairs**

Run: `pytest -q`

Expected: PASS.

```bash
git add -A
git commit -m "refactor: follow the isolated plugin layout"
```

### Task 6: Documentation Sync

**Files:**
- Modify: `README.md`
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`
- Modify: `plugin/skills/tcw-plugin/SKILL.md` and conditional references as needed

- [ ] **Step 1: Update installation and repository-layout guidance**

Explain that marketplace installs contain only agent assets and bootstrap obtains the CLI from PyPI. Document new development paths without implying users must re-add the marketplace.

- [ ] **Step 2: Add release and developer notes**

Release notes describe the smaller plugin update and migration plainly. Changelog Internal/Changed entries name the payload root, VERSION token, manifest paths, and release-tool changes.

- [ ] **Step 3: Align the driving skill**

Ensure Claude hook and Codex manual bootstrap routes both point at the installed-root script and never expect Python source in the plugin.

- [ ] **Step 4: Commit docs as one final block**

```bash
git add README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md plugin/skills/tcw-plugin
git commit -m "docs: describe the isolated agent plugin"
```

### Task 7: Final packaging verification

- [ ] **Step 1: Run all Python checks**

Run: `pytest -q`

Expected: PASS.

- [ ] **Step 2: Validate manifests from their actual roots**

Run the documented Claude plugin validator and Codex plugin/Agentskills validator against `plugin/`; if a harness CLI is unavailable, record that environment limitation and rely on schema tests rather than claiming the external check passed.

- [ ] **Step 3: Inspect the payload and diff**

Run: `git ls-files plugin && git diff --check && git status --short`

(`find -printf` is GNU-only and fails on the macOS BSD `find` this repo is
developed on; `git ls-files` is also the more honest listing, since untracked
files are not payload.)

Expected: only agent assets appear under plugin, no Python files are listed, and no unexpected changes remain.

## Verification

External marketplace installation cannot be fully proven offline. In addition to tests, install the marketplace from a disposable harness profile when available and confirm the resolved plugin root lacks Python source and `tcw --version` is supplied by pipx/PyPI.
