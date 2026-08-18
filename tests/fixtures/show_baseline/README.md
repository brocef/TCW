# `tcw work show` baselines

Captured from the CLI **before** `_show` was touched by
`2026-08-12-project-a-work-item-as-json`, so that item's criterion 7 — "output
without `--json` is byte-identical to before this change" — is checked against
bytes the implementer could not have edited into agreement.

`{slug}` and `{started}` are the only substitutions; the test formats them from
the item it builds. Everything else is literal, including blank lines.
