# Report a leftover pre-2.5.0 store config file instead of silently dropping its extends

Since 2.5.0, `docs/capabilities/.config.yaml` and `docs/taxonomy/config.yaml` are no
longer read. A well-formed leftover is ignored without a word, so a project that
federated through one silently loses every inherited entry. Nothing in `tcw
capabilities check`, `tcw taxonomy check`, `tcw validate` or `tcw provision` points
at the cause. Only an *unparseable* leftover is reported today, yet the well-formed
one is the case that actually loses data. The migration guide
(`docs/migration-guide-2.4.X-to-2.5.0.md`) admits that nothing warns you; this item
closes that gap.

## What happened

In proposit-app, the CLI changed from 2.4.0 to 2.5.0 partway through a session. In
a consumer node, `tcw capabilities list` went from about 128 rows, including
inherited `proposit-shared/...` ones, to 32 rows with none inherited.
`tcw capabilities show proposit-shared/...` and `set` refused with "no such
capability". `check` reported 128 problems, 71 of them
`overrides → unknown alias 'proposit-shared'`. The reporter spent a while ruling out
their own branch (stash test, `tcw provision` saying "already available",
`tcw validate`) before learning the cause: `extends: [proposit-shared]` still in
apps/mobile and apps/server's `docs/capabilities/.config.yaml`. There were five such
files across three nodes.

## What is wanted

- `tcw capabilities check`, `tcw taxonomy check` and `tcw validate` report an inert
  legacy config file as a problem, e.g. "docs/capabilities/.config.yaml is no longer
  read — move `extends` into tcw-config.yaml as capabilities.extends". The same
  applies wherever `<component>.path` puts the store.
- Possibly: `tcw provision` (or a dedicated command) migrates it.
- The `overrides → unknown alias '<id>'` message names the likely cause when the
  alias is not in `<component>.extends`, so it describes the cause rather than only
  the effect.

## Origin

Reported 2026-09-21 by the Claude session working in proposit-app, after the 2.5.0
upgrade. The requester asked for it to be tracked at high priority.

## References

- `docs/migration-guide-2.4.X-to-2.5.0.md`: the break, and the admission that
  nothing warns.
- The v2.5.0 changelog ("A leftover file is inert: not parsed, not reported by the
  component `check()`, not deleted"): the decision this item revisits.
