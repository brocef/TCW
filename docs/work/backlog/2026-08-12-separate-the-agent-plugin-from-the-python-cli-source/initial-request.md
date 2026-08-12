# Separate the agent plugin from the Python CLI source

## Product changes

The agent plugin stops carrying Python code. Installing the plugin gets skills,
commands, and agents; the `tcw` CLI comes from PyPI, as it already does.

## Technical changes

Split the plugin packaging from the Python package — a second repo, or one repo
with two publishable roots — and repoint the marketplace entries at whichever
carries the plugin.

## Meta changes

Completes the separation that
`2026-08-11-install-the-plugin-s-cli-from-pypi-instead-of-its-own-clone`
started, and shrinks what a plugin install downloads to what a plugin install
needs.

---

## Requested outcome

This is **ask #2** of
`2026-08-11-install-the-plugin-s-cli-from-pypi-instead-of-its-own-clone`, quoted
from that item's request:

> **Separate them entirely**, so the AI-agent plugin contains no Python code and
> installing `tcw` from PyPI is mandatory rather than optional.

Ask #1 shipped on 2026-08-12: `scripts/session_bootstrap.sh` installs `tcw-cli`
from PyPI and nothing installs from the clone any more. The clone still *exists*
inside every plugin install, carrying the whole Python package, `tests/`, and the
web client — it is simply no longer the install source.

## What ask #1 already unblocked

The welding is gone. The bootstrap no longer installs from `$root`; it reads the
plugin root only for a version marker (`tcw/__init__.py`), and
`skills/tcw-plugin/references/{setup,doctor}.md` and `commands/tcw-doctor.md` all
prescribe `tcw-cli` rather than a clone path. Nothing in the install path depends
on the Python source being co-located any more.

## Open questions for spec

- **Second repo, or one repo with two packaging manifests?** Undecided at the
  time of the split, and still undecided. What does
  `.claude-plugin/marketplace.json` / `.agents/plugins/marketplace.json` point at
  afterwards, and what happens to users who added the current marketplace?
- **The version marker.** The bootstrap's steady-state check reads
  `$root/tcw/__init__.py` — a Python file that would not exist in a Python-free
  plugin. `.claude-plugin/plugin.json` is the obvious replacement and was
  explicitly deferred to this item: swapping it during ask #1 would have traded a
  proven marker for an unverified one whose failure mode is a silent `exit 0`
  with no CLI installed. Verify it, don't assume it.
- **Versioning across the split.** `CLAUDE.md` §Versioning keeps 5 files in
  lockstep and `scripts/cut_version.py` bumps them together. If the plugin and
  the package live apart, do they still share a version string, and what cuts
  them?
- **Tests and CI.** `tests/test_plugin_manifests.py` guards manifest/version
  agreement across both plugin manifests and `pyproject.toml`; a split has to
  decide where that test lives and what it can still see.

## Constraints

- Both harnesses stay first-class. Claude gets `session_bootstrap.sh` via a
  `SessionStart` hook; Codex has no hook and runs the same script through the
  `tcw-plugin` skill. Neither may be left behind.
- Existing plugin users must have a migration path. Changing what the marketplace
  points at cannot silently strand someone who added it under the old layout.

## Non-goals

- Anything about the install source — ask #1 shipped that.

## Notes

- Filed 2026-08-12 at closeout of ask #1, at the requester's direction.
- Priority 30, below the two active-work items above it: this is a packaging
  cleanup with no user-visible behavior change, now that the install source has
  already moved.
