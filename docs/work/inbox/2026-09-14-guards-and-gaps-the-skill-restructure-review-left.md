# Guards and gaps the skill restructure's review left for separate changes

Found by the adversarial code review of
`2026-09-14-restructure-tcw-s-skills-setup-and-configure-skills-command-and-extras-skills-and-no-slash-commands`.
None is caused by that item's own requirements, and each needs its own decision.

1. **The removed-names test scans only part of the repository.** It covers
   `skills/`, the two manifest folders, `README.md`, `docs/guide/` and
   `docs/lifecycle/`, as the item's spec asked. `agents/`, `hooks/`, `scripts/`,
   `evals/`, `tests/`, `AGENTS.md` and `CLAUDE.md` are clean today, but nothing
   stops a removed skill or command name coming back there.
2. **Nothing checks that `EXCLUSIONS` and `PARTIAL` in `evals/coverage.py` name
   skills that still ship.** A stale key (say a deleted skill) passes
   `tests/test_eval_coverage.py`.
3. **`tcw-setup`'s `install.md` never says how to run the bootstrap script under
   Codex.** It says "Under Codex there is no hook, and you run it", without the
   path to `scripts/session_bootstrap.sh` or its two arguments. `README.md` says
   the skill "runs the same install script". This predates the restructure; the
   text moved from `tcw-plugin` unchanged.
4. **`tcw-work-stage`'s manual fallback writes `<plugin>` for the plugin folder**
   with no instruction for finding that folder under Codex.
5. **Small duplication in tests.** The "body after the frontmatter" slice and the
   frontmatter parse are written three times (`tests/test_skill_lifecycle_parity.py`,
   `tests/test_documentation_sync_wiring.py`, `tests/test_plugin_manifests.py`).
   A shared helper would keep the rule for what counts as a skill body in one place.
