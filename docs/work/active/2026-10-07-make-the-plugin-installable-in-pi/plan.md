# Implementation plan

1. Add the official `pi` resource declaration in `package.json`, sharing `skills/` and disabling other resource types. Keep current web fields and all existing plugin manifests. Verify using the installed Pi package resolver and skill loader against an isolated local install.
2. Update `README.md`, `skills/setup/SKILL.md`, `skills/setup/references/install.md`, `skills/README.md`, `skills/work/references/procedures/delegation.md`, and `docs/lifecycle/harness.md` for Pi installation, setup and inline execution when delegation is unavailable. Preserve Claude enhancements and Codex instructions.
3. Update `docs/capabilities/plugin/install-as-a-plugin/description.md` and `docs/capabilities/plugin/bootstrap-the-cli/description.md`. Add this item's entries under `docs/changelogs/upcoming/` and `docs/release-notes/upcoming/`. Re-evaluate Documentation Sync triggers against the finished diff.
4. Run the existing plugin manifest tests, capability/taxonomy checks, node validation and `git diff --check`. Commit scoped implementation and record evidence in `outcome.md`; submit for user verification without closing or releasing.

## Documentation Sync

Public-API: README and the release note. Any-Code-Change: packaging changelog. Skill-Driven-Component: setup skill and install reference. Harness/delegation guidance and capability descriptions also change. Tracker-Change, Guide-Topic-Change and Configuration-Key-Change do not fire: no tracker, guide-topic or TCW configuration behavior changes.

## Verification

Use Pi 1.0.2 with a fresh `PI_CODING_AGENT_DIR` under `/tmp`, offline mode and telemetry disabled. Install the absolute checkout path, list it, resolve package resources and load all skills using Pi's own implementation. Assert the resolved skill paths equal every shipped SKILL.md and diagnostics are empty. This avoids personal configuration writes and model calls. Record that remote Git publication and model-driven lifecycle execution are not exercised. Existing manifest tests cover the preserved Claude/Codex contracts; no new tests mirroring static JSON are needed.
