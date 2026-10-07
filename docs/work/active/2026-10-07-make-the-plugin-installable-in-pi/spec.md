# Pi package support

## Capability changes

Change `plugin/install-as-a-plugin` to include Pi Git and local installation. Change `plugin/bootstrap-the-cli` to describe explicit setup in Pi. Existing CLI vocabulary applies; no new taxonomy entry is needed.

## Problem

README.md:84 documents Codex installation but has no Pi installation instructions. package.json:2 identifies the private web toolchain package and package.json:8 begins its scripts; it has no explicit Pi resources. Pi 1.0.2 currently accepts the local directory by convention and its loader finds all 17 skills without diagnostics, but this is not a documented supported path.

## Goals

Support Pi's official Git/local package format, reuse all shipped skills, and preserve Claude Code and Codex compatibility.

## Non-goals

No npm publication, new extension, automatic Pi hook, agent conversion, release, remote push, or Python CLI behavior change. No changes to the web dependency graph or existing plugin manifests.

## Design

Add an explicit `pi` manifest exposing `./skills` in the existing package.json. Keep its private name, package manager, dependencies and scripts. Pin other resource types to empty arrays to avoid accidental extension or prompt discovery. Do not add a sixth version field: Git refs identify versions.

Document Git installation, project-local installation, local checkout testing, `/skill:setup`, CLI installation, and `/skill:work` invocation. Pi does not execute the Claude hooks or dynamic shell injection: existing manual commands remain the required fallback. Keep existing Claude and Codex mechanisms intact. Explain that custom Claude agent files are not Pi resources, and stages run inline when delegation is unavailable; autonomous advisor requirements still apply.

Update shared harness/setup guidance and the installation capability descriptions. Packaging changes do not introduce store operations; all lifecycle behavior remains in the storage-abstracted CLI.

## Acceptance criteria

- An isolated Pi 1.0.2 local installation registers this checkout without changing personal settings.
- Pi's installed package resolver and skill loader expose exactly the shipped SKILL.md files, with no diagnostics and no extensions/prompts/themes.
- Existing plugin manifest tests pass, including Claude/Codex metadata and all five version fields.
- README provides Git and local installation, explicit CLI setup and invocation instructions, and accurately scopes agent/hook support.
- TCW capability, taxonomy and node validation pass; Git whitespace checks pass.

## Risks

Pi Git installation installs this root package's web dependencies. Keep this visible in documentation; splitting the package is outside this small integration. A local install does not prove remote publication; no claim of published changes until pushed. Loading skills proves discovery, not end-to-end model compliance.
