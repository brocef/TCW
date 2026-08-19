# 08 — Taxonomy and capabilities

The other two axes. Lower-risk than `work` for 1.0.0, but they share the store
substrate and the reference resolver, so a regression here is a regression
everywhere.

## Functionality covered

- `tcw taxonomy add|list|show|search|rm|check|extends`, `--kind`, `--parent`,
  `--vocab`, `--slug`
- `tcw capabilities add|list|show|set|reset|search|check|drift|extends`,
  `--status`, `--field`
- `tcw://` reference resolution and `tcw validate`

## What is tested — taxonomy

| # | Assertion |
| - | --------- |
| 1 | `tcw taxonomy add "Work Item" "A tracked change"` creates a vocabulary term; `description` is **positional**, not a flag. |
| 2 | `tcw taxonomy list` shows it as a tree, flagged by kind and origin. |
| 3 | `--slug custom` overrides the slugified name; `--parent <path>` nests the term and `list` renders the nesting. |
| 4 | `--kind feature` creates a feature; `--vocab <ref>` records the vocabulary it involves, repeatable. |
| 5 | `tcw taxonomy show <path>` prints the entry; an unknown path exits non-zero with empty stdout. |
| 6 | `tcw taxonomy search` matches on **name and description**, not name alone. |
| 7 | `tcw taxonomy rm <path>` removes a local entry; removing an inherited one is refused. |
| 8 | `tcw taxonomy check` passes on a clean tree and **fails** on a feature whose `--vocab` ref points at a term that does not exist. |
| 9 | The tree is built from real parentage, not by sorting path strings — asserted with two terms whose names sort in the opposite order to their nesting. |

## What is tested — capabilities

| # | Assertion |
| -- | --------- |
| 10 | `tcw capabilities add web/browse "Browse content"` creates the folder; `tcw capabilities list` shows it with its status. |
| 11 | `-s Missing` at creation and `tcw capabilities set web/browse --status Shipped` both take effect, and `show` reflects the change. |
| 12 | `--field K=V` sets arbitrary metadata; `--field Subject=a,b,c` splits into a list while other fields do not split on commas. |
| 13 | `tcw capabilities set` on an unknown path exits non-zero and creates nothing. |
| 14 | `tcw capabilities check` fails when a capability's `Subject` or feature ref points at a taxonomy entry that does not exist, and passes once it does. |
| 15 | `tcw capabilities drift` reports a Shipped-but-Missing / unreviewed-inherited capability, and reports nothing on a clean node. |
| 16 | `tcw capabilities reset <path>` drops a local override so the upstream value is inherited again — set up with a federated sibling node. |

## What is tested — federation and validate

| # | Assertion |
| -- | --------- |
| 17 | Two sibling nodes on disk: `tcw taxonomy extends add <id>` makes the parent's terms visible in the child's `list`, flagged with their **origin**. |
| 18 | `tcw taxonomy list --local` excludes them. |
| 19 | A qualified ref (`<project>/<term>`) resolves from the extending node. |
| 20 | `tcw capabilities extends <id>` and `--rm` do the same for capabilities. |
| 21 | `tcw validate` exits 0 on a clean node and non-zero on one with a broken `tcw://` link, naming the offending file. |
| 22 | `tcw validate` **recurses into registered descendants by default**; `--no-recurse` limits it to the active project. Proven by breaking a link in the child only and checking both forms. |
| 23 | `tcw validate <path>` narrows to one file or directory and disables recursion. |

## Refusals asserted

5, 7, 8, 13, 14, 21.

## Explicitly not covered here

Deep federation topologies (diamond inheritance, cycles). Worth a follow-up
scenario if review thinks the risk is real.

## Notes for the implementer

Assertion 22 is the one worth the setup cost: recursion-by-default is a 1.0.0
behaviour change, and a child node whose links are broken must fail the parent's
validate. Build the two nodes as siblings under the temp dir. **There is no registration
CLI** — see the note in scenario 10 — so write the reciprocal `connected-projects`
blocks into each `tcw-config.yaml` by hand, then verify the wiring through
`tcw work nodes` and `tcw validate`. An earlier draft of this document said to
register them through the CLI and never to hand-edit the config. That was wrong,
and following it would have blocked assertions 17–23 outright.
