# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`tcw work tracker import <ticket> [--part <id>] [--title <title>]`**, **`link
  <slug> <ticket> [--part <id>]`** and **`unlink <slug> --reason <text>`**, for
  claiming a Jira ticket and binding it to a work item.
  - The claim (`tcw/tracker/intake.py`, `read_ticket` then `claim`): refuse a done
    or someone else's ticket; apply the `transitions.claim` transition; `assign`
    only after it applied and only if unassigned; re-read and require the landing
    status (the matched transition's destination) and this account's `accountId`.
    Every outcome carries a row id (`1a`–`1f`, `3a`–`3f`) matching the spec's
    decision tables. Transition errors are carried as `detail`, never interpreted;
    auth, permission, rate-limit and not-found errors on the transition propagate.
  - A ticket assigned to this account that no longer offers the claim is bound
    without a transition (row `1e`), which is how an interrupted import completes.
  - The binding: new `tracker.yaml` entry in `WORK_SIDECARS` (`yaml_mapping`,
    `generated`), keyed by `(project, provider, ticket id, part)`. `find_binding`
    queries unresolved items only and raises `BindingProblem` on a malformed binding
    or two items holding one key. `unlink` moves the binding into an `unlinked`
    history and makes no tracker call.
  - `import` drops the item it created if the binding write fails, and names the
    item with `tcw work drop <slug> --confirm` if the drop fails too.
- **`JiraClient.apply_transition`, `assign`, and `description`**, the last reading
  the v2 endpoint so a description arrives as a wiki-markup string rather than a
  rich-text document tree.

## Changed

- **`JiraClient.issue` URL-quotes the key** it puts in the request path.
- **`tracker.yaml` is in `OWNED_YAML_NAMES`**, so `tcw validate` reports one that is
  not a mapping, as it does for `state.yaml`.
- The `tcw work tracker` group's help no longer says read-only.

## Fixed

- **Two `tcw work tracker show` notes overstated what one ticket can show**
  (GitHub issue #36). Both are `Assessment.detail` strings in
  `tcw/tracker/claim.py`.
  - The `CLAIM_NOT_OFFERED` note named two explanations, a wrong
    `transitions.claim` name or a ticket past the claim, and missed a ticket that
    has not reached it yet (for example, one still in Triage). It now names all
    three.
  - The note for an offered claim said exclusivity "can only be read from a
    ticket already in that status". On an exclusive workflow that is false: `show`
    never passes `landing_status` to `assess()`, so the landed ticket still reports
    `NOT_DETERMINED`. The note now says a landed ticket can reveal a workflow that
    is not exclusive, never one that is, and that exclusivity is confirmed only
    when a claim is made or from the workflow definition.
  - `docs/guide/work.md` and `skills/tcw-work/references/commands.md` repeated both
    two-case explanations and are corrected to match. Two tests in
    `tests/test_tracker_claimability.py` assert the new wording and the absence of
    the old.
