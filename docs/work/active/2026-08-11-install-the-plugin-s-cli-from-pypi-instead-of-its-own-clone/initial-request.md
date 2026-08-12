# Install the plugin's CLI from PyPI instead of its own clone

## Product changes

The plugin stops shipping and installing its own copy of the Python CLI.
Installing the plugin installs `tcw-cli` from PyPI; the guidance recommends the
PyPI install rather than the bundled clone.

## Technical changes

Point `scripts/session_bootstrap.sh` at PyPI, and find a way to separate the
agent-plugin packaging from the Python source so the plugin carries no Python
code at all.

## Meta changes

Turns PyPI from an alternative install route into *the* install route, and makes
the plugin a pure skills/commands/agents package.

---

## Requested outcome

Today the plugin **is** the Python repo: `scripts/session_bootstrap.sh:82` runs
`pipx install --force "$root"` against the plugin's own clone in the agent's
plugin cache, and the marketplace points at `brocef/TCW` wholesale. Two asks,
in increasing order of size:

1. **Change the guidance and the install source** to prefer PyPI —
   `pipx install tcw-cli` rather than a pipx install from the cached clone.
2. **Separate them entirely**, so the AI-agent plugin contains no Python code
   and installing `tcw` from PyPI is mandatory rather than optional.

## Why this is separate from the publishing item

Split out of `2026-08-11-publish-tcw-to-pypi-with-automated-releases` on
2026-08-11, at the requester's direction, for three reasons:

- **It is untestable until a release exists.** There is nothing on PyPI to
  install from until that item ships its first `tcw-cli`.
- **It is a behavioral regression risk, not a rename.** Session start currently
  works offline — everything it needs is already in the plugin clone. Installing
  from PyPI makes a network round-trip and PyPI's availability part of starting
  a session. That trade needs its own spec, not a paragraph in someone else's.
- **"Separate entirely" is a repackaging question with no obvious answer yet.**
  The plugin manifests, the marketplace entries, and the Python package all live
  in one repo; splitting them likely means a second repo or a packaging split,
  and that decision has not been made.

## Constraints

- Version coupling: the plugin version and the PyPI version are the same string
  today (see `CLAUDE.md` §Versioning — 5 files in lockstep). Installing from
  PyPI means deciding whether the bootstrap pins `tcw-cli==<plugin version>` or
  floats, and what happens when PyPI does not yet have the version the plugin
  claims.
- Both harnesses must work. Claude gets `session_bootstrap.sh` via a
  `SessionStart` hook; Codex has no hook and runs the same script through the
  `tcw-plugin` skill (`README.md:135-138`). Neither may be left behind.
- The editable-checkout protection in `session_bootstrap.sh:47-74` must survive
  whatever replaces it — a developer's `pip install -e .` must still be left
  alone.
- Existing installs must migrate. Users already have a pipx package installed
  from the clone; changing the source cannot leave them with two.

## Non-goals

- Nothing about publishing or CI — that is the blocking item.

## Open questions for spec

- Does the plugin still work offline / air-gapped, and if not, is that
  acceptable or does it need a bundled fallback?
- Second repo, or one repo with two packaging manifests? What does the
  marketplace entry point at afterwards?
- Pin or float the `tcw-cli` version, and how does the bootstrap behave when the
  requested version is not on PyPI yet (a freshly tagged plugin racing its own
  release workflow)?
- How does `/tcw-doctor` (`skills/tcw-plugin/references/doctor.md`) diagnose an
  install it no longer performs from a clone it can no longer see?

## Notes

- Filed 2026-08-11 as a decomposition, not from a cold request. The requester's
  words are quoted in "Requested outcome"; the rest is context recorded at the
  time of the split.
- Blocked by `2026-08-11-publish-tcw-to-pypi-with-automated-releases`.
