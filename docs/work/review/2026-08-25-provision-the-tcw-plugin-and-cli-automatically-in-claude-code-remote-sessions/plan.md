# Provision the tcw plugin and CLI automatically in Claude Code remote sessions — Plan

Three code tasks, then one documentation block. The suite is green at every
commit boundary: Task 1 adds a script nothing references yet, Task 2 adds the
tests for it, Task 3 wires the hook and tests the wiring in the same commit.

## Task 1 — the provisioning script

**Creates:** `scripts/remote_session_setup.sh` (mode 0755).

Contract, mirroring `scripts/session_bootstrap.sh`: every path exits 0, only a
failure prints, and it prints to **stdout** because SessionStart stdout reaches
the agent's context while stderr does not. A file-header comment states the
contract, the gate, and how to run it by hand, as that script's header does.

Behavior, in order:

1. `usage`/argument handling for one optional flag, `--force`. Any other
   argument prints one line and exits 0.
2. **Gate:** exit 0 unless `${CLAUDE_CODE_REMOTE:-}` is `true` or `--force` was
   passed.
3. **Root:** `root="${CLAUDE_PROJECT_DIR:-}"`, falling back to the script's own
   `..` when unset, so a hand run needs no environment. Exit 0 if
   `$root/pyproject.toml` is absent — nothing identifies this as the checkout.
4. **Guard:** skip the install when `command -v tcw` succeeds *and* a
   `python3 - "$root"` heredoc reports that `tcw`, `pytest`, and `jsonschema`
   all import and that `tcw.__file__` resolves under `$root`. The heredoc strips
   `""`, `"."`, and `os.getcwd()` from `sys.path` first, for the reason
   `scripts/session_bootstrap.sh:38-46` gives.
5. **Install:** `python3 -m pip install -e "$root[dev]"`, retried once with
   `--break-system-packages` on failure. Both attempts failing prints one line
   naming the command and exits 0.
6. **PATH repair:** if `tcw` is still not on PATH, and
   `python3 -m site --user-base`'s `bin` holds one, append that directory to
   PATH through `$CLAUDE_ENV_FILE` when the harness set it.
7. **Plugin:** if `claude` is on PATH, run
   `claude plugin marketplace add "$root"` then `claude plugin install tcw@tcw -y`,
   each redirected to a variable so only a failure prints. Neither ever gets
   `--scope project` or `--scope local`, so no tracked file changes. A missing
   `claude` prints one line and exits 0.

**Proves it:** `bash -n scripts/remote_session_setup.sh` parses; the file is
executable; `CLAUDE_CODE_REMOTE=true scripts/remote_session_setup.sh` in this
container leaves `tcw --version` equal to `tcw/__init__.py`'s version,
`python3 -c "import pytest"` working, `claude plugin list` showing `tcw@tcw`,
and `git status --porcelain` empty.

## Task 2 — tests for the script

**Creates:** `tests/test_remote_session_setup.py`.

Hermetic in the same way `tests/test_session_bootstrap.py` is: every run gets
`PATH=tmp_path/bin:/usr/bin:/bin` with stub `python3` and `claude` executables
that append their argv to a log file and exit with a scripted status, so no test
runs a real `pip` or a real `claude`. Each run gets a throwaway `root`
containing a `pyproject.toml`, and `CLAUDE_ENV_FILE` pointed inside `tmp_path`.

Cases, one per acceptance criterion:

- gate: no `CLAUDE_CODE_REMOTE`, no flag → exit 0, empty log.
- gate: `CLAUDE_CODE_REMOTE=true` → pip install and both plugin commands, in
  that order, exit 0.
- gate: `--force` with `CLAUDE_CODE_REMOTE` unset → same as above.
- gate: `CLAUDE_CODE_REMOTE=false` → empty log.
- root: no `pyproject.toml` under root → exit 0, empty log.
- guard: stub `python3` reporting "already installed" → no `pip install` in the
  log, plugin commands still run.
- failure: stub `python3` failing both attempts → exactly one stdout line, exit
  0, and the log shows the `--break-system-packages` retry.
- failure: no `claude` on PATH → exactly one stdout line, exit 0, pip still ran.
- scope: no logged `claude` argv contains `--scope project` or `--scope local`.
- `bash -n` parses the script, and its mode is executable.

**Proves it:** `pytest tests/test_remote_session_setup.py` passes, and
`pytest tests/test_session_bootstrap.py` still passes untouched.

## Task 3 — register the hook

**Modifies:** `.claude/settings.json` — add a `SessionStart` hook running
`"$CLAUDE_PROJECT_DIR"/scripts/remote_session_setup.sh`, keeping the existing
`enabledPlugins` block byte-identical and the file's 4-space indentation
(`.prettierrc.json`).

**Appends to:** `tests/test_remote_session_setup.py` — a test that
`.claude/settings.json` parses, that its `SessionStart` hook command names
`scripts/remote_session_setup.sh`, and that `enabledPlugins` still carries
`tcw@tcw`. This lands in the same commit as the settings change so the suite is
green at the boundary.

**Proves it:** `pytest tests/test_remote_session_setup.py` passes;
`python3 -m json.tool .claude/settings.json` succeeds.

## Documentation Sync

Evaluated against `tcw work docs`; every entry considered, two fire.

- `README.md` — **[Public-API]**: **does not fire.** No public CLI surface or
  user-facing behavior changes; the README's "Install" section describes how
  *users* get the plugin and `tcw-cli`, and this item changes nothing there.
- `docs/release-notes/upcoming.md` — **[Public-API]**: **does not fire**, same
  reason. A contributor-environment script is not a user-facing change.
- `docs/changelogs/upcoming.md` — **[Any-Code-Change]**: **fires.** Add an
  `### Internal` entry naming `scripts/remote_session_setup.sh`, the
  `.claude/settings.json` hook, and the fact that it is remote-gated and
  installs the checkout rather than the published distribution.
- `skills/<component>/SKILL.md` — **[Skill-Driven-Component]**: **does not
  fire.** No component's CLI surface, model, lifecycle, or guardrails change;
  `skills/tcw-plugin/SKILL.md` documents installing the *published* CLI for a
  user, which this item leaves alone (`spec.md` non-goals).
- `AGENTS.md` (`CLAUDE.md` is a symlink to it) — not a configured entry, but
  required by `docs/lifecycle/harness.md`: a mechanism a Claude hook fires
  automatically must be reachable by hand for a Codex or local contributor.
  Add a short subsection stating what a remote session provisions and giving
  the `scripts/remote_session_setup.sh --force` invocation.

## Verification

Beyond the suite, in this container:

1. `git stash` nothing — confirm `git status --porcelain` is empty immediately
   after a real `--force` run, proving the user-scope claim in `spec.md`.
2. `tcw --version` matches `grep __version__ tcw/__init__.py`, proving the
   editable install won over any PyPI copy.
3. `claude plugin list` shows `tcw@tcw` enabled at user scope, and
   `~/.claude/plugins/known_marketplaces.json` records the `directory` source
   pointing at the checkout.
4. A second consecutive run is a no-op on the pip step (guard hit) and reports
   the plugin already installed — idempotence, observed rather than argued.
5. `pytest tests/test_session_bootstrap.py tests/test_plugin_manifests.py`
   passes, confirming the plugin's own bootstrap and the version lockstep are
   untouched.

What cannot be verified here: that a *fresh* remote container runs the hook at
session start, since this session's container was provisioned before the hook
existed. The first session after this branch merges is the real check, and the
script prints on failure precisely so that session reports it.

## Notes

- No blockers; nothing in `docs/work/` overlaps this item.
- `tests/test_remote_session_setup.py` deliberately never invokes a real `pip`
  or `claude` — the same rule `tests/test_session_bootstrap.py` states for
  `pipx`, for the same reason: a test that did would rewrite the developer's own
  environment.
