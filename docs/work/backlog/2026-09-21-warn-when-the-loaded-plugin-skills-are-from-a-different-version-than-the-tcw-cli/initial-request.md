# Warn when the loaded plugin skills are from a different version than the tcw CLI

## Request

When the `tcw` CLI an agent runs and the plugin skills it follows come from
different releases, say so: which two versions disagree, and how to bring them
into line. In the reported case the CLI was 2.5.0 and the skills 2.4.0, and the
skills described behavior the CLI no longer has.

The requester chose **warn only** on 2026-09-21: a mismatch never blocks work.

It should reach both Claude and Codex users; Codex has no SessionStart hook.

## Constraints

- v2.5.1 (the release carrying v2.5.0's contents, whose tag never reached PyPI) is
  held until all five items filed from the proposit-app reports on 2026-09-21 are
  fixed and accepted. This is one of them.

## Notes

- Asked for reference material, deadlines and exclusions on 2026-09-21: none
  beyond the reporter's account in `intake.md` and the related items it names.
