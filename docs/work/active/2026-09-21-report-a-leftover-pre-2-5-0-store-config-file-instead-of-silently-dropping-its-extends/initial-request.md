# Report a leftover pre-2.5.0 store config file instead of silently dropping its extends

## Request

Since 2.5.0, `docs/capabilities/.config.yaml` and `docs/taxonomy/config.yaml` (or
their equivalents wherever `<component>.path` puts the store) are no longer read. A
project that federated through one loses every inherited entry, and nothing says
why. The requester wants that leftover **reported**: `tcw capabilities check`,
`tcw taxonomy check` and `tcw validate` should flag it as a problem, and name the
fix (move `extends` into `tcw-config.yaml` as `<component>.extends`).

The `overrides → unknown alias '<id>'` message should also point at the likely
cause, so it describes the cause rather than only the effect.

## Constraints

- v2.5.1 (the release carrying v2.5.0's contents, whose tag never reached PyPI) is
  held until all five items filed from the proposit-app reports on 2026-09-21 are
  fixed and accepted. This is one of them.

## Out of scope

- **Rewriting files.** The requester chose "report only" on 2026-09-21: nothing,
  including `tcw provision`, migrates the file automatically. The user makes the
  move by hand, following the message.

## Notes

- Asked for reference material, deadlines and exclusions on 2026-09-21: none
  beyond the reporter's account in `intake.md` and the related items it names.
