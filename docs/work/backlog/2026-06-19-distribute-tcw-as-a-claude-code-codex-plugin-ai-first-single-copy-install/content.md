# Distribute tcw as a Claude Code / Codex plugin (AI-first single-copy install)

Package this repo so it can be installed as a Claude Code or Codex plugin, shipping
`tcw` skills + slash commands — and resolve the "two copies on one machine" risk that
plugin distribution creates.

**Reference implementation:** `/Users/brian/Projects/Proposit-App/skill-cefailures` ships
the same dual Claude/Codex plugin layout (and its `broker` CLI faces the *exact* single-copy
/ version-drift problem we are planning for). Mirror it.

## Product changes

- **New:** install this repo as a Claude Code / Codex plugin, exposing skills and slash
  commands that drive the three components (`taxonomy | capabilities | work`) from inside
  an AI coding agent.
- **New command `/tcw-init`:** runs the `pip install` of the plugin's own clone for the
  user, so the `tcw` CLI becomes available without a separate manual install step.
- **New command `/tcw-doctor`:** diagnose the install — is `tcw` on PATH, does its version
  match the active plugin-cache version, dev-install vs cache-install (mirrors
  `skill-cefailures`'s `broker:doctor`, which exists precisely because of version drift).

## Technical changes

Concrete manifest set to add (from the skill-cefailures layout — two ecosystems, four files):

- `.claude-plugin/plugin.json` — name, version, description, author, keywords, `"skills": "./skills/"`, `"commands": "./commands/"`.
- `.claude-plugin/marketplace.json` — makes the repo a single-plugin marketplace (`source: "./"`).
- `.codex-plugin/plugin.json` — adds an `interface` block (displayName, short/long description, category, capabilities, defaultPrompt). **Note:** skill-cefailures's Codex manifest declares `skills` *only, no `commands`* — so slash commands may be Claude-Code-only (see open questions).
- `.agents/plugins/marketplace.json` — Codex/agents marketplace; `source.path: ./plugins/tcw`, where `plugins/tcw` is a **symlink back to repo root** (the trick that lets the local source resolve).

Plus:

- A `skills/` and `commands/` layer at repo root carrying the driving skills/commands. This
  is the delivery vehicle for the deferred skill layer — coordinate scope with backlog item
  `2026-06-19-skill-layer-capabilities-process-work-spec-3` (likely **merge**, not duplicate).
- `/tcw-init` implementation: resolve the plugin's installed clone path, then
  `pip install <that path>` so the CLI and the plugin are the *same* checkout. Claude Code
  clones to a **version-namespaced cache**: `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`.
- Path/script resolution convention (per skill-cefailures): commands reference scripts by a
  path relative to the command file ("N directories up"); the binary is resolved from the
  versioned cache path, with the `doctor` command reconciling drift.

## Meta changes

- **Distribution strategy decision — AI-first, single copy.** When `tcw` is installed via the
  plugin system the agent clones the whole repo. If the user *also* `pip install`s the repo
  separately they get **two copies that can drift to different versions.** Plan: the plugin
  clone is the single source of truth — installing the plugin drives `pip install <plugin
  clone path>`, so there is one copy and updates flow through the AI app's plugin updater.
- **Wrinkle the cache layout forces:** because the Claude cache path is *per-version*
  (`.../<plugin>/<version>/`), "single copy" is not automatic — a one-time `pip install -e`
  pins to a version dir that the **next plugin update abandons**. So either `/tcw-init`
  re-points on every update, or we install non-editable per version, or we mirror the broker's
  approach (a `~/.local/bin` symlink into the active cache dir + a `doctor` that re-points).
  This is the crux to decide.
- **Version-sync burden:** the manifests add **three** version-bearing JSON files
  (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`)
  on top of `pyproject.toml` + `tcw/__init__.py` = **5 files** that must move together. Fold
  them into the documentation-sync cut-version flow so a release bumps all five.
- README install section to document: if you use the plugin, do **not** also `pip install
  tcw` separately.

## Open questions / risks

- **Editable vs per-version install, given the versioned cache dir.** `-e` keeps the CLI in
  lockstep *within* a version but breaks on update (new dir); non-editable needs a re-install
  per update. The broker sidesteps pip entirely with a symlink + doctor — evaluate that route.
- **Does Codex support slash commands / a `commands` dir at all?** skill-cefailures exposes
  skills only to Codex. If not, `/tcw-init` and `/tcw-doctor` must be expressed as **skills**
  on the Codex side (or init handled differently).
- **Target interpreter / PEP 668** "externally managed environment" — which Python does
  `/tcw-init` install into? May force `pipx` or `--user`/venv.
- **Detecting a dev install** (cloned, `pip install -e .` by hand) vs a plugin-cache install,
  so `/tcw-init` / `/tcw-doctor` don't clobber a developer's setup (broker's health-check
  branches on exactly this).
