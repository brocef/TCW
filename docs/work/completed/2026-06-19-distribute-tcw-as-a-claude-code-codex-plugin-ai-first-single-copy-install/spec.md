# Spec — Distribute tcw as a Claude Code / Codex plugin

Package this repo so it installs as a Claude Code / Codex plugin shipping the `tcw`
skills, and — Claude-Code-side — bootstraps the `tcw` CLI from the plugin's *own
clone*. Mirror `skill-cefailures`' dual-ecosystem layout **field-for-field** (copy
its manifests, don't author from abbreviated descriptions).

## Mental model (corrected)

There is **no single literal copy.** Claude Code copies the repo into a
version-namespaced cache dir (a flat tree, **no `.git`**); pipx then builds a
*second*, isolated venv from that dir. So:

> **Single source of truth = the active cache version dir; the pipx venv is a
> built copy that `/tcw-doctor` keeps reconciled to it.** "No drift" is the goal
> doctor *enforces*, not a property of the layout.

**Live baseline (this machine, verified):** `tcw` currently resolves to an
**editable** pyenv install (`direct_url.json: editable=true`, v0.0.1) and **pipx
is not installed.** So the "edge cases" below — pipx-absent, and an editable dev
install shadowing the pipx one on PATH — are the *default* path here, not
afterthoughts.

## Resolved cruxes

1. **CLI install = pipx the clone.** `/tcw-init` resolves the plugin clone root,
   then `pipx install <clone>` (one isolated venv on PATH; pipx owns its venv →
   sidesteps PEP 668; needs Python ≥ 3.11, already constrained).
   - **Resolve the clone root** by, in order: (a) `$CLAUDE_PLUGIN_ROOT` if Claude
     Code sets it at command/skill runtime (verify during impl); (b) else the
     ancestor of the running command/skill file that holds `pyproject.toml`. Do
     **not** reconstruct a hardcoded `cache/.../<version>/` path.
   - **pipx-absent fallback ladder** (primary path on this machine): detect
     `command -v pipx`; if missing, instruct install via the platform package
     manager, else fall back to `python3 -m pip install --user <clone>` or a
     dedicated venv — never a bare `pip install` into a PEP-668 managed base.
2. **Drift = doctor re-points.** `/tcw-doctor` ports the reference broker
   `health-check.md` **Check 5** algorithm (do not re-derive):
   - Resolve where `tcw` runs from: `command -v tcw` → realpath; read its source
     via `pipx list --json` (the venv's install spec) or
     `importlib.metadata.distribution('tcw').locate_file('')`.
   - **Editable dev-install detection** = read `tcw-<ver>.dist-info/direct_url.json`
     and check `dir_info.editable == true` (do *not* grep for `-e`). If editable,
     **report and leave alone** — and warn that the editable shim may shadow the
     pipx `tcw` on PATH.
   - **Active cache version** = list sibling version dirs under the plugin's cache
     parent and take the highest by **`sort -V`** (lexicographic sort is buggy:
     `1.9.0` > `1.12.0`).
   - On mismatch (installed source ≠ active cache dir): `pipx install --force
     <active clone>`. On `--force` failure (perms / conflicts / network): report
     and stop with manual-fix guidance — no silent retry.
3. **Codex shim = a skill, not a command.** Codex plugins expose skills, not slash
   commands (verified: no `commands` key in either Codex/agents manifest). The
   init+doctor *procedure* lives **inline** in a new skill **`tcw-plugin`**;
   `/tcw-init` and `/tcw-doctor` are thin Claude-Code command pointers to it.
   Keep it a single inline SKILL.md — do **not** split into broker's multi-doc
   form (that would be gold-plating). Consequence: neither ecosystem needs `tcw`
   on PyPI — both pipx-install the clone via the skill/command.

## Components

### Manifests (mirror skill-cefailures — copy field-for-field; 4 files + 1 symlink)
- `.claude-plugin/plugin.json` — name `tcw`, `version` (= `tcw.__version__`),
  description, **author**, keywords, `"skills": "./skills/"`, `"commands": "./commands/"`.
- `.claude-plugin/marketplace.json` — single-plugin marketplace, `source: "./"`,
  **`owner`** (not `author`), per-plugin `description` + `version`.
- `.codex-plugin/plugin.json` — `"skills": "./skills/"`, `homepage`, `repository`,
  and a full `interface`: `displayName, shortDescription, longDescription,
  developerName, category, capabilities: ["Read","Write"], defaultPrompt`. **No commands.**
- `.agents/plugins/marketplace.json` — top-level `interface.displayName`; per-plugin
  nested `source: { "source": "local", "path": "./plugins/tcw" }`, a `policy`
  block (decide `installation`/`authentication` deliberately — tcw needs no auth),
  and `category`. **Carries no version.**
- `plugins/tcw` — a **relative** symlink to repo root: `ln -s .. plugins/tcw`
  (absolute target breaks on other machines). Verify `git ls-files -s plugins/tcw`
  shows mode `120000` (a real symlink, not a copied dir).

### Skill — `skills/tcw-plugin/SKILL.md` (Codex shim + single source of init/doctor judgment)
Holds the **setup** and **doctor** procedures inline (per crux 1 & 2).

### Commands (Claude Code) — thin pointers
- `commands/tcw-init.md` → "run the `tcw-plugin` setup procedure."
- `commands/tcw-doctor.md` → "run the `tcw-plugin` doctor procedure."

### Capabilities (product delta — `Missing` now, flipped `Supported` at completion)
New `plugin` namespace under `docs/capabilities/`, each with a `Subject:` pointer
(else `tcw capabilities check` flags an unresolved ref — use `Subject: cli` or a
new `plugin` term):
- `plugin#install-as-a-plugin`
- `plugin#bootstrap-the-cli` (`/tcw-init`)
- `plugin#diagnose-the-install` (`/tcw-doctor`)

### Docs (every obligation AGENTS.md triggers)
- **README** `### As a plugin` under `## Install`: `/plugin marketplace add
  brocef/TCW` + `/plugin install tcw` + `/tcw-init`; Codex variant = `codex plugin
  marketplace add brocef/TCW --ref main`, install, then ask the agent to run the
  `tcw-plugin` setup; a **"don't `pip install tcw` separately if you used
  `/tcw-init`"** warning.
- **README `## Skills`** — currently says "**two** skills"; adding `tcw-plugin`
  makes it three. Update the prose + list.
- **AGENTS.md *Versioning*** — list all 5 version-bearing files.
- **release-notes/upcoming.md** (user-facing: installable as a plugin) +
  **changelogs/upcoming.md** (Added — *with* the `git rev-parse --short HEAD`
  hash range per AGENTS.md).
- Confirm `tcw-work`/`tcw-capabilities` SKILL.md need no change (they don't drive
  plugin install — a no-op, but state it to satisfy trigger-evaluation).
- **At completion:** invoke the `skill-cefailures:documentation-sync` skill, and
  run the tcw-capabilities ledger flip (Missing → Supported).

## Version-sync invariant + test
5 files carry the version and move together: `pyproject.toml`, `tcw/__init__.py`,
`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
`.codex-plugin/plugin.json`. (`.agents/plugins/marketplace.json` carries none.)

`tests/test_plugin_manifests.py`: every manifest JSON parses **and all 5 version
fields agree** (parse `pyproject.toml` too — not just the 3 manifests vs
`__init__`, so the pre-existing pyproject↔`__init__` drift is also guarded). This
guards **authoring** drift only; runtime cache-vs-installed drift is `/tcw-doctor`'s
job, not the test's.

## Out of scope
- Codex auto-install via a slash command (Codex has none); the `tcw-plugin` skill
  guides the pipx install instead.
- Publishing to PyPI — both ecosystems install from the clone.
- Unit-testing pipx/doctor runtime branching (environment-side; validated via
  `/tcw-doctor`). Keep the one manifest test.

## Resolved risks (were "open")
- **Clone-root / active-cache resolution** — solved by crux 1 (`$CLAUDE_PLUGIN_ROOT`
  / ancestor-`pyproject.toml`) and crux 2 (broker Check-5 sibling scan + `sort -V`).
- **pipx absent** — first-class fallback ladder in crux 1.
- **Editable shim shadowing** — detected and reported by doctor (crux 2).
