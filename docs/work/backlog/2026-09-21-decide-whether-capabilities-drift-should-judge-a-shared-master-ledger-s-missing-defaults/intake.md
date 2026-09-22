# Decide whether capabilities drift should judge a shared master ledger's Missing defaults

In the proposit-app setup, a shared "master" ledger lists capabilities with
`Status: Missing` as its default. Each app project sets its own status by
overriding the entry. `tcw capabilities drift`, run on the master ledger, lists
those entries as shipped-but-Missing, because their Planning doc points at a
completed work item. For a master ledger, Missing is the default and not a claim
that nothing shipped, so this looks like a false positive. The alternative is
that the master's records really are behind. Decide which it is. If drift should
not judge a master ledger's defaults, find a way to tell that case apart (for
example, entries that projects extending it override), and change drift or its
documentation.

## Origin

Reported by the proposit-app agent on 2026-09-21 while running its usual workflow
on v2.5.1. It called this low priority. Possible bug.

## References

- `tcw capabilities drift` (skills/capabilities/SKILL.md, "find drift")
