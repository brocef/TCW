# Separate the agent plugin from the Python CLI source — Specification

## Capability changes

No taxonomy or capability-ledger changes are required. Installation behavior remains: the plugin supplies agent guidance and ensures the separately published `tcw-cli` is available.

## Problem

The repository root is simultaneously the Python distribution and both harnesses' plugin source. Marketplace manifests point at the root, so installing the plugin downloads `tcw/`, tests, and web sources even though bootstrap installs the CLI from PyPI (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `scripts/session_bootstrap.sh:1-8`). The bootstrap also uses `tcw/__init__.py` as its plugin-version token, preserving an unnecessary runtime dependency on Python source (`scripts/session_bootstrap.sh:83-93`).

A separate repository would provide the strongest physical boundary, but cannot be delivered atomically from this repository and would strand existing marketplace coordinates during migration. A publishable plugin root within this repository provides the required installed artifact boundary while retaining one migration commit.

## Goals

- Make a dedicated `plugin/` tree that contains no Python package, Python tests, web source, or Python packaging metadata.
- Point Claude and Codex marketplace entries at that tree.
- Keep all skills available to both harnesses, commands/agents as harness-specific enhancements, and the Claude SessionStart hook that bootstraps the CLI.
- Replace the bootstrap's Python-file version token with a plugin-owned plain `VERSION` file.
- Keep release automation and tests verifying every duplicated version.
- Preserve existing marketplace repository coordinates and provide an upgrade path for current users.

## Non-goals

- Moving the plugin to a second repository in this change.
- Changing the PyPI package name or CLI installation policy.
- Adding slash-command support to Codex.
- Removing agent definitions that accelerate workflows while corresponding skills remain standalone.
- Decoupling CLI and plugin release numbers yet; lockstep releases remain the simplest supported contract in a monorepo.

## Design

### Publishable plugin root

Create `plugin/` containing the installable agent assets:

- `plugin/.claude-plugin/plugin.json`;
- `plugin/.codex-plugin/plugin.json`;
- `plugin/skills/`, `plugin/commands/`, `plugin/agents/`, and `plugin/hooks/`;
- `plugin/scripts/session_bootstrap.sh`;
- `plugin/VERSION`.

The root marketplace descriptors remain discovery metadata and change their source/path to `./plugin`. Root development copies of skills, commands, and agents must not remain independent duplicates. Move the authoritative assets into `plugin/` and update repository references/tests to use that location. Repository-level `AGENTS.md` remains development guidance, not plugin payload.

The plugin tree must be self-contained: relative links and script paths resolve from `plugin/`, and a packaging test rejects Python source/package markers under that tree.

### Bootstrap version token

Read and compare `plugin/VERSION` rather than `tcw/__init__.py`. The sentinel stores the exact VERSION contents. Keep all current safeguards: no root means no action, steady state avoids Python/network work, editable installations are not overwritten, pipx is not bootstrapped automatically, and failed installation leaves the sentinel stale.

### Versions and release automation

Continue one lockstep version across `pyproject.toml`, `tcw/__init__.py`, the two plugin manifests, the Claude marketplace plugin entry, and `plugin/VERSION`. Update `scripts/cut_version.py`, manifest tests, and AGENTS versioning guidance as one change. The added plain marker increases the duplicated set; tests remain the source of enforcement.

### Migration

Keep both marketplace files at their current repository locations so users do not re-add a marketplace. Their plugin source moves to `./plugin`; the next update installs the smaller root and its bootstrap reconciles against `VERSION`. Release notes must call out that direct consumers of root-relative skill paths need to use `plugin/skills/...`.

## Acceptance criteria

- Both marketplace descriptors resolve their TCW plugin source to `plugin/`.
- `plugin/` contains every skill required by Claude and Codex, Claude commands/agents/hooks, both plugin manifests, bootstrap, and VERSION, but no `tcw/`, `tests/`, `pyproject.toml`, Python files, or web-client source.
- Claude manifest validation and Codex/Agentskills manifest validation pass from the dedicated root.
- Running bootstrap with the dedicated root uses `VERSION` for steady-state comparison and sentinel writes, with all existing safety tests still passing.
- `cut_version.py` changes every version-bearing file in lockstep and its tests prove drift is rejected.
- Documentation and skill-relative links contain no stale paths to the old root layout.
- A clean plugin installation still obtains `tcw-cli` from PyPI, never from the plugin tree.

## Risks

- Moving many documentation assets can leave stale links. A repo-wide link/path audit and plugin-manifest tests are required.
- Some consumers may invoke root `scripts/session_bootstrap.sh` directly. Release notes and setup/doctor guidance must name the new path.
- Monorepo source remains larger in Git, although the marketplace-installed plugin root becomes small. A future second-repository move remains possible without changing the internal plugin layout.
- Lockstep versions couple releases, but avoid introducing a two-product release protocol during the packaging move.
