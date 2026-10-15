# Notes for TCW-75 from the reviews of TCW-74 and TCW-77 (2026-10-15)

Things those items left in TCW-75's files on purpose. Plan a task for each.

1. **`tcw work procedure prompt` is refused by the 3.0 CLI but still named** in
   `skills/configure/references/work.md:117`, `README.md` (about :505 and
   :688) and `docs/guide/configuration.md:139`. TCW-74 added it to
   `REFUSED_VALUES` in `tests/doc_allowance.py`.
2. **When the last mention goes, nothing notices the allowance entry is dead.**
   `test_no_allowance_value_is_named_only_by_owned_text` passes vacuously
   (`not namers`). Add a check that each allowance entry is still named
   somewhere, then remove this one.
3. **The deleted procedure ids** (consolidate-plans, decompose, delegation,
   post-mortem) are still listed in `skills/configure/references/work.md`
   (about :101-117) and `docs/guide/configuration.md` (about :117, :137-138).
4. **The configure skill's Jira reference does not exist yet.**
   `skills/work/SKILL.md` and `skills/setup/references/jira.md` already point
   to it; TCW-75 replaces `tracker.md` with it. A version must not be cut
   between TCW-74 and TCW-75.
5. **`tcw serve` text from 2.x**: README (about :109-110 and :779-801) says it
   needs Node.js; the 2.x viewer is described in `docs/guide/work.md`,
   `docs/guide/jira.md`, `configuration.md` (about :252),
   `linking-and-validation.md` (about :26) and `multi-repo.md` (about :86).
   The 3.0 viewer is described in `docs/guide/web-viewer.md` (TCW-77).
6. **26 capability records still carry the retired `Planning doc` field**,
   including `web/choose-a-theme` (TCW-77's spec left that one unchanged).
   They fail the capabilities check once the config is 3.0. TCW-74's outcome
   lists 15 of them; check which item owns the clean-up (this one or TCW-76).
7. **`tests/doc_allowance.py`'s `--include-descendants` entry** is still needed
   by other guides; remove it once they are rewritten.
