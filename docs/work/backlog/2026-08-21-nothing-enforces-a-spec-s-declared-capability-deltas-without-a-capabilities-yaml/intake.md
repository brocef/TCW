# Nothing enforces a spec's declared capability deltas without a capabilities.yaml

## Origin

Found at the `verify` stage of
`2026-08-19-key-work-documentation-uniqueness-on-path-trigger-so-one-file-can-carry-two-triggers`,
while checking the standing ledger before writing that item's own
`## Capability changes` section.

## What was found

`2026-08-18-serve-documentation-sync-entries-from-tcw-config-yaml-instead-of-scraping-the-agent-guide`
declared two new capabilities in prose, in its `spec.md:5-10`:

> **New.** Two capability records under `docs/capabilities/work/`:
> - *Declare which documents track which changes* …
> - *Read the documentation gate for a change* …

Neither record was ever written. The item completed anyway, and its
`refined-outcome.md:65` records `tcw capabilities drift` as reporting **no
capability drift** — which was true, and is the problem.

The two records have since been written by hand (`55b49c2`), so the ledger is
correct now. What remains is the hole that let it happen.

## Why nothing caught it

Three mechanisms could have, and none applies:

1. **`tcw capabilities drift`** looks for inherited-but-unreviewed entries and
   local entries still reading `Missing` whose `Planning doc` names a completed
   item. A capability that was never created has no record to read `Missing`, so
   it is invisible to drift **by construction**. This is arguably correct
   behavior rather than a bug — drift audits the ledger, and the ledger is where
   the entry is absent.
2. **The `capabilities.yaml` completion gate** does exactly the right check: it
   blocks `complete` when a path under `new:` still reads `Missing` or fails to
   resolve. But the item never had a `capabilities.yaml` — the file is the
   work→capability back-pointer, and nothing requires one even when the spec's
   `## Capability changes` section is non-empty. No file, no gate.
3. **The `spec` stage instructions** require a `## Capability changes` section,
   but its content is prose. `tcw` never reads it, so "New. Two capability
   records…" is a sentence, not a commitment.

So a spec can promise capability records in the one section built for it, and
the item can complete with the ledger untouched and every check green.

## Shape of a possible answer

Not a decision, just where the seam looks like it is: the `spec` (or `plan`)
stage is where a declared delta could be turned into the `capabilities.yaml`
back-pointer that the completion gate already knows how to enforce — either by
writing it, or by refusing to leave the stage with a non-empty
`## Capability changes` section and no corresponding file. Whether TCW should
parse that prose section at all is the open question, and it may be that the
honest fix is in the stage instructions rather than in the CLI.

Worth checking whether other completed items have the same gap before choosing.

Axis: work (and capabilities).
