# Provision the tcw plugin and CLI automatically in Claude Code remote sessions — Outcome

## What shipped

**Task 1 — `scripts/remote_session_setup.sh`** (`d118074`). Gate
(`CLAUDE_CODE_REMOTE=true` or `--force`), checkout resolution with a fallback to
the script's own `..`, the already-installed guard, `pip install -e "$root[dev]"`
with one `--break-system-packages` retry, PATH repair through `$CLAUDE_ENV_FILE`,
then `claude plugin marketplace add "$root"` and `claude plugin install tcw@tcw -y`
at user scope. Every path exits 0; only failures print, on stdout.

**Task 2 — `tests/test_remote_session_setup.py`** (`fd9f43c`). 18 tests over stub
`python3`, `claude`, and `tcw` executables on a scratch PATH, with the same
hermeticity assertion `tests/test_session_bootstrap.py` makes — a run that
reached the real `python3` would install into the developer's own interpreter,
so `_run` proves it cannot.

**Task 3 — the hook** (`52e020e`). `.claude/settings.json` gains a `SessionStart`
entry running `"${CLAUDE_PROJECT_DIR}"/scripts/remote_session_setup.sh`, plus two
tests: the registration exists, and `enabledPlugins` still carries `tcw@tcw`.
20 tests total in the file.

**Documentation** (`857290c`). `docs/changelogs/upcoming.md` under `### Internal`;
a `## Development environment` section in `AGENTS.md` (`CLAUDE.md` is a symlink
to it) giving the `--force` invocation for Codex and local shells. README and
release notes did not fire — no public CLI surface or user-facing behavior
changed. No driving skill fired: no component's CLI surface, model, lifecycle, or
guardrails moved.

## Test result

`pytest tests/test_remote_session_setup.py tests/test_session_bootstrap.py
tests/test_plugin_manifests.py` → **55 passed**. `tcw validate` → `validate OK`.

The full suite in this container is **1975 passed, 6 failed**, and all six fail
identically on the commit *before* this work (`git stash` + rerun, verified):

- `tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path`
  and both `tests/test_store_editor.py` atomic-write tests — the container runs
  as uid 0, so a `chmod`-unwritable directory is still writable and the expected
  failure never happens.
- `tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel` —
  `pip wheel --no-deps --no-build-isolation` exits 1 in this image.
- both `tests/test_generate_hook.py` cases — same, pre-existing.

None of the six touch anything this item changed. CI runs on a non-root runner
with build isolation available, which is where the suite is green.

## Live verification, in this container

Torn down and rebuilt for real, not simulated: `claude plugin uninstall tcw@tcw`,
`claude plugin marketplace remove tcw`, `pip uninstall -y tcw-cli` — then one
`./scripts/remote_session_setup.sh --force`:

- **5.2 s**, silent, exit 0, from nothing installed.
- `tcw --version` → `tcw 1.0.3`, matching `tcw/__init__.py`.
- `import pytest, jsonschema` succeeds.
- `claude plugin list` → `tcw@tcw`, version 1.0.3, user scope, enabled.
- `known_marketplaces.json` → `{"source": "directory", "path": "/home/user/TCW"}`.
- `git status --porcelain` → empty.
- A second run: **2.0–2.7 s**, guard hit (no pip install), both plugin commands
  reporting already-done. Run through the exact registered hook command string
  with `CLAUDE_PROJECT_DIR` and `CLAUDE_CODE_REMOTE=true` set, not just the bare
  path.

Still unverifiable here, as `plan.md` said: that a *fresh* remote container fires
the hook at session start. This container was provisioned before the hook
existed. The first session on this branch is the real check, and the script
prints on failure so that session will say so.

## What the plan or spec got wrong

- **The red-first rule was only half honored, and the gap is real.** The plan
  ordered the script before its tests, so those 18 tests were green on first
  run — a test that has never been red proves nothing. Rather than claim
  otherwise, the tests were mutation-checked: dropping the remote gate failed
  exactly the two gate tests, and appending `--scope project` to the install
  failed the ordering test and the scope invariant. Only Task 3's registration
  test was genuinely red first (`KeyError: 'hooks'`) before the settings edit.
  A better plan would have specified the mutations up front instead of leaving
  the ordering to imply a discipline it could not deliver.
- **The spec's cleanliness claim was narrower than it reads.** `claude plugin
  install` does not touch project settings, which is what the hook runs and what
  the criterion covers. But `claude plugin uninstall` **does**: it strips the
  plugin from `.claude/settings.json` at every scope and rewrites the file with
  2-space indentation, against the repository's 4-space prettier config. Nothing
  the hook runs does this; it surfaced only because teardown for the cold-start
  test used it, and it cost one `git checkout --` each time. Worth knowing before
  anyone runs an uninstall inside a checkout.
- **The plan's test list was short.** It named ten cases; twenty shipped. Added
  beyond the plan: the guard is not consulted when no `tcw` is on PATH, no PATH
  repair when the user base holds nothing, a failing `marketplace add` skips the
  install rather than piling a second error line on the first, and an invariant
  that the script's body never mentions `pipx` or `tcw-cli` — the published
  install path staying the plugin bootstrap's job is a property worth failing a
  test over, not a comment.
- **`docs/changelogs/upcoming.md` needed a formatting pass the plan did not
  anticipate.** Continuation paragraphs under a list item need 4-space indents
  under `.prettierrc.json`'s `tabWidth: 4`. Also found: `AGENTS.md` at HEAD
  already fails `prettier --check` (table padding, and `*how*` for `_how_`).
  That is pre-existing and was left alone; the added section was verified clean
  by normalizing both sides and diffing, and the deviation is not this item's to
  fix.

## Notes

- `documentation-sync` could not be invoked as a skill this session: the plugin
  that ships it is not loaded, which is the exact gap this item closes. The
  entries were read from `tcw work docs` and `skills/documentation-sync/SKILL.md`
  in the checkout and evaluated by hand, entry by entry, as `plan.md` records.
- PyPI's newest `tcw-cli` is 0.21.1 against this tree's 1.0.3. Nothing here
  depends on that, but it is why installing the published distribution in a
  contributor session would have been the wrong answer.
