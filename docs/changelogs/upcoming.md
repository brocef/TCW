# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Changed

- `scripts/session_bootstrap.sh` installs `tcw-cli` from PyPI
  (`pipx install --force tcw-cli`) instead of the plugin's own clone
  (`pipx install --force "$root"`). The version **floats**: the bootstrap
  resolves whatever PyPI has, rather than pinning to the plugin's version string.
  Both install routes — plugin and manual — now converge on one pipx package with
  one install spec, so they can no longer drift.
- Existing installs migrate with no action. pipx names the venv from the
  distribution metadata (`tcw-cli` for both the clone and the wheel), so the PyPI
  install replaces a clone install in place: one venv, `package_or_url` flipping
  from the local path to `tcw-cli`. Verified against real pipx in an isolated
  `PIPX_HOME`.
- The bootstrap's failure message names PyPI and suggests network as the likely
  cause. It stays one line and does not classify the failure (network vs. missing
  release vs. pipx internal) — diagnosis remains `/tcw-doctor`'s job.
- `skills/tcw-plugin/references/doctor.md`: the `sort -V` active-cache-version
  scan is **removed**, along with the installed-source-vs-active-clone
  comparison it fed. There is no clone to compare against. The repair is now
  "missing, or present but not ours to touch" → run the bootstrap, then
  `pipx install --force tcw-cli`; a CLI behind the latest release is *reported*
  with `pipx upgrade tcw-cli` rather than treated as breakage.
- `skills/tcw-plugin/references/setup.md`: the `pipx`-absent fallback ladder
  installs `tcw-cli` rather than `"<clone-root>"`. The step-6 warning about a
  separate `pip install tcw-cli` drifting from the plugin's copy is dropped —
  they are the same package now.
- `commands/tcw-doctor.md` tracks `doctor.md`; its `description` frontmatter no
  longer promises that `tcw` matches the active plugin-cache version.
- Capability records reworded: `plugin/bootstrap-the-cli` (PyPI source, network
  requirement), `cli/install-from-pypi` (convergence with the plugin route
  instead of a don't-do-both caveat), `plugin/diagnose-the-install` (reports
  version currency, not plugin-version equality). All three stay `Supported`.

## Internal

- The sentinel's meaning is documented where it lives. It was already only a
  trigger token for a plugin-version change; under a floating install it is
  emphatically *not* evidence about which `tcw-cli` was resolved, and the header
  and step-2 comments in `session_bootstrap.sh` no longer imply otherwise. The
  mechanism is unchanged: `cmp` against the clone's `tcw/__init__.py`, one `cmp`
  and one `command -v` in steady state, no network on the hot path.
- Consequence of floating + the sentinel: a plugin release that briefly outruns
  its own PyPI upload installs the previous `tcw-cli` and records it as current
  until the next plugin version. Surfaced to users through `/tcw-doctor`'s
  currency report rather than fixed in the script.
- `tests/test_session_bootstrap.py`: exactly two assertions changed — the
  expected pipx argv (215) and the failed-install `endswith` (203). Every other
  assertion, including the whole editable/unidentifiable-install probe suite,
  passes unmodified. No new tests: the failure path does not branch on *why*
  pipx failed, and nothing in the script branches on CLI-vs-plugin version skew.
  The suite's no-real-pipx rule is intact — the migration check is manual and
  scripted in the work item's spec.

## Fixed

- `tests/test_documented_cli_surface.py` read any backtick span *mentioning*
  `tcw` as a `tcw` invocation. `\btcw\b` matches inside `tcw-cli` (`-` is a
  non-word character), so `pipx install --force tcw-cli` parsed as `tcw` with a
  `--force` flag and failed as a nonexistent flag. Spans now require `tcw`
  followed by a space or tab — deliberately not `\s`, which would match a
  newline and let a span cross the line breaks the `[^`\n]` classes forbid,
  reuniting a wrapped `tcw\nwork …` and reading a sentence that *denies* a verb
  as one documenting it. Latent since the test was written; only reachable once
  a doc named `tcw-cli` alongside a flag.
