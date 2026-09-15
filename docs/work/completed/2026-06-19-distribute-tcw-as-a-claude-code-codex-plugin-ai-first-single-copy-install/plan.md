# Plan — Distribute tcw as a Claude Code / Codex plugin

Ordered implementation. Source of truth = `spec.md` (dual-reviewed). Version on all
manifests = current `tcw.__version__` / pyproject (`0.1.1`).

## Phase 1 — Manifests + symlink (copy skill-cefailures field-for-field)
1. `.claude-plugin/plugin.json` — `name: tcw`, `version`, description, `author`,
   keywords, `"skills": "./skills/"`, `"commands": "./commands/"`.
2. `.claude-plugin/marketplace.json` — `owner` (not author), single plugin
   `source: "./"`, per-plugin description + `version`.
3. `.codex-plugin/plugin.json` — `"skills": "./skills/"`, homepage, repository,
   full `interface` (displayName, shortDescription, longDescription, developerName,
   category, `capabilities: ["Read","Write"]`, defaultPrompt). No commands.
4. `.agents/plugins/marketplace.json` — `interface.displayName`; per-plugin nested
   `source: {source:"local", path:"./plugins/tcw"}`, `policy` (no auth needed →
   drop/relax `authentication`), `category`. No version.
5. `ln -s .. plugins/tcw` (relative); `git add` and verify `git ls-files -s
   plugins/tcw` → mode `120000`.

## Phase 2 — Skill + thin commands
6. `skills/tcw-plugin/SKILL.md` — inline **setup** (resolve clone root via
   `$CLAUDE_PLUGIN_ROOT` → else ancestor-`pyproject.toml`; `pipx install <clone>`;
   pipx-absent fallback ladder; verify `tcw --version`; warn vs separate pip) and
   **doctor** (realpath of `tcw`; `direct_url.json dir_info.editable` → leave dev
   installs alone + warn on PATH shadow; active cache version via sibling scan +
   `sort -V`; mismatch → `pipx install --force`; on force-fail, report + stop).
7. `commands/tcw-init.md`, `commands/tcw-doctor.md` — thin pointers to the skill.

## Phase 3 — Capabilities (Missing)
8. Add `plugin#install-as-a-plugin`, `plugin#bootstrap-the-cli`,
   `plugin#diagnose-the-install` via `tcw capabilities add`, status `Missing`,
   each with a `Subject:` (use `cli` or a new `plugin` term); `tcw capabilities check`.

## Phase 4 — Test
9. `tests/test_plugin_manifests.py` — all manifest JSON parses; all **5** version
   fields (`pyproject.toml`, `tcw/__init__.py`, 3 manifests) equal each other.

## Phase 5 — Docs
10. README — add `### As a plugin` under `## Install` (Claude + Codex + warning);
    update `## Skills` two→three.
11. AGENTS.md *Versioning* — list all 5 version-bearing files.
12. `docs/release-notes/upcoming.md` (plain: installable as a plugin) +
    `docs/changelogs/upcoming.md` (Added, with `git rev-parse --short HEAD` range).

## Phase 6 — Verify + complete
13. `python -m pytest -q` (incl. new test) green.
14. Invoke `skill-cefailures:documentation-sync`; confirm `tcw-work`/`tcw-capabilities`
    SKILL.md unchanged (no-op, stated).
15. Ledger flip: `tcw capabilities set` the three `plugin#…` → `Supported`.
16. `tcw work complete <slug> --resolution done --confirm` (atomic with the final
    code/docs commit).

## Notes / risks carried from review
- Cache path is `cache/<repo>/<plugin>/<version>/` (likely `TCW/tcw/…`, capital) —
  **discover, never hardcode**.
- Live machine: editable `tcw` (0.0.1) + no pipx → exercise both branches manually
  when sanity-checking the skill text.
