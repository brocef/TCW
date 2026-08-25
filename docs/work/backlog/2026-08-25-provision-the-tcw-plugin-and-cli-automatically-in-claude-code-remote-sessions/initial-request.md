# Provision the tcw plugin and CLI automatically in Claude Code remote sessions

## Request

Change the repository so that **the tcw plugin and the Python package are
installed automatically when a Claude Code remote session starts**.

The request came out of a diagnosis run in a remote session on this repository:
the session began with neither the plugin nor `tcw` available, and provisioning
both by hand was possible but entirely manual. The requester wants a session
that starts on this repository to arrive with both already in place, so nobody
has to run the install steps before doing any work.

"Remote sessions" means Claude Code on the web / Claude Code Remote — the
managed container sessions described in `docs/lifecycle/harness.md` terms as a
Claude-only harness surface. No behavior was requested for local sessions.

## Notes

- The requester was not asked for reference material; the request arrived as a
  direct instruction in a session already holding the diagnosis. The references
  below are the evidence gathered during that diagnosis, not material the
  requester supplied.
- Two readings of "the Python package" were left open by the request and are
  resolved in the spec rather than here: the **published** `tcw-cli` from PyPI,
  or **this checkout** installed editable. Likewise for the plugin: the
  published marketplace at `brocef/TCW`, or the checkout the session is working
  in. Both are recorded as assumptions in the spec, with the evidence that
  decided them.
- Explicitly not requested: provisioning the Node/pnpm toolchain used by the
  web app and the prettier/eslint/vitest checks.

## References

- `scripts/session_bootstrap.sh` — the plugin's own SessionStart bootstrap;
  whatever this item builds has to coexist with it rather than fight it.
- `.claude/settings.json` — already enables `tcw@tcw`, which is why the gap is
  surprising: the plugin is declared but nothing installs it.
- `.github/workflows/test.yml` — how CI provisions the same repository, and
  therefore the closest existing statement of "a working checkout".
- `README.md` "Install" — the documented install paths for both the plugin and
  the package, which this item automates rather than replaces.
