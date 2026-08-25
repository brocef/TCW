# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Internal

- Claude Code **remote** sessions on this repository now provision themselves.
  `scripts/remote_session_setup.sh`, registered as a `SessionStart` hook in
  `.claude/settings.json`, installs the checkout with its dev extras
  (`pip install -e '.[dev]'`, the same provisioning
  `.github/workflows/test.yml` performs) and installs the `tcw` plugin from the
  checkout (`claude plugin marketplace add "$CLAUDE_PROJECT_DIR"` then
  `claude plugin install tcw@tcw`, always at **user** scope so a session start
  never dirties the working tree). It is gated to `CLAUDE_CODE_REMOTE=true`
  unless run with `--force`, which is how a Codex agent or a human provisions
  the same environment by hand.

    Contributor tooling only: nothing about how the **published** plugin or
    `tcw-cli` installs for a user changes. `scripts/session_bootstrap.sh` is
    untouched, and the two do not collide in either firing order — the bootstrap
    already declines to replace a `tcw` whose interpreter reports an editable
    install, which is what this leaves behind. On a stock remote container the
    bootstrap could never have acted anyway: it exits early when `pipx` is absent,
    by design.

    `tests/test_remote_session_setup.py` covers the gate, the already-installed
    guard, the `--break-system-packages` retry, both plugin failure paths, the
    `CLAUDE_ENV_FILE` PATH repair, and the never-`--scope project` invariant, with
    stub executables only — no test runs a real `pip` or a real `claude`.
