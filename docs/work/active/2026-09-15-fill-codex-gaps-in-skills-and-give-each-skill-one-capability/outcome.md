# Outcome: Fill the Codex gaps in the setup and stage skills, and give each skill one capability

## What shipped

1. **Install command and `<plugin>`** — `a940740a`. `skills/setup/references/install.md`
   gives `bash <plugin>/scripts/session_bootstrap.sh <plugin>` for Codex, defines
   `<plugin>`, explains why the sentinel argument is left off, and says to check
   `tcw --version` afterwards because the script is silent. `skills/work-stage/SKILL.md`
   and `skills/documentation-sync/SKILL.md` define `<plugin>` in their fallbacks.
2. **One capability per skill** — `11258dde`. `work/run-a-lifecycle-stage` loses its
   two `work-stage` paragraphs; `skills/work-stage` gains what they said that it did
   not. The issue-closing rules live in `work/complete-a-work-item` (with the reason
   `superseded` is conditional); `skills/extras-triage-issues` links there.
   `capabilities.yaml` declares all four.
3. **Docs** — `652522e8`: changelog and release note.
4. **Review fixes** — `54fb93d9`: the `work-stage` capability said the item is
   optional for every stage (false for `inbox`) and had dropped how Codex receives
   the stage and item; `install.md`'s "three levels above this file" could be
   counted to `skills/`; the plugin path is to be quoted if it has a space;
   `cut-version.md` named `scripts/unpushed-version.sh` without saying it is the
   skill's folder, not the project's.

## Evidence

- Criterion 2: a scratch copy of the plugin (`skills/`, `scripts/`,
  `tcw/__init__.py`) with `PATH=/usr/bin:/bin` (no `tcw`, no `pipx`) — the command
  as written exits 0 and prints nothing. The reviewer separately ran it with a
  failing fake `pipx` (one line printed, exit 0) and a wrong root (silent, `pipx`
  never called), and confirmed installed copies under `~/.claude/plugins/cache` and
  `~/.codex/plugins/cache` both hold `scripts/`, `tcw/__init__.py` and the two
  fallback targets at the stated locations.
- Criteria 3-6: the relative paths resolve from `skills/work-stage/` and
  `skills/documentation-sync/`; `work-stage` appears in `run-a-lifecycle-stage` only
  in its `validate` paragraph; "only when the superseding item absorbed" is in one
  capability; `tcw capabilities check` OK.
- Skill tests (`test_skill_lifecycle_parity`, `test_shipped_procedures`,
  `test_plugin_manifests`): 209 passed after the review fixes.
- Full suite: combined run; result in `refined-outcome.md`.

## What the plan or spec got wrong

- **The spec's sweep searched for `<plugin>` only.** A skill-relative path with no
  placeholder (`scripts/unpushed-version.sh` in `cut-version.md`) is the same gap;
  found by review and fixed.
- **"The work item is optional for every stage"** came from the spec's own wording
  and was wrong for `inbox`.
- **Not verified:** whether Codex's default sandbox lets `pipx install` reach the
  network. The reviewer suspects not; nothing in `install.md` tells an agent to ask
  for that permission. Recorded, not filed — it was not observed.
