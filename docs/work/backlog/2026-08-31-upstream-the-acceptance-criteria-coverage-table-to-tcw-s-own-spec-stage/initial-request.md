# Upstream the acceptance-criteria coverage table to TCW's own spec stage

## The request

This repository now requires a **Coverage** table in every spec — each acceptance
criterion crossed against whatever the Design section numbers, each cell either a
test name or `n/a` **with the `file:line` that makes it n/a**. It lives in
`docs/lifecycle/templates/spec.md`, bound to the `spec` stage by
`tcw-config.yaml`, and applies to this project only.

Consider making it part of TCW's own `spec` stage, so every TCW user gets it.

## Why it might belong upstream

It came out of a post-mortem across two children of
[the store-home-repository epic](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it),
where the same defect shape shipped four times: an acceptance criterion written as
a general property, verified only against the handful of cells its own text or its
test fixtures happened to reach. In all four, the uncovered axis was already
written down as a numbered list in the same spec's Design section, one or two
sections away from the criterion that contradicted it.

Nothing about that is specific to this codebase. Any project whose spec numbers
its resolution rules, command steps, or failure modes can write a criterion that
silently skips one.

## Why it is deliberately not upstream yet

**It has survived zero items.** A rule that ships to every TCW user should have
been used in anger first. Child C of the same epic
([Publish provisioned-store writes to their remote](tcw://W/2026-08-26-publish-provisioned-store-writes-to-their-remote))
is its first real test, and is a good one — its axes are
{pull, push} × {unreachable, refused, diverged, rejected, conflicted, partial} ×
{which ladder rule resolved the store}, which is a far larger grid than the 3×3
the post-mortem was derived from.

Things to learn from that use before upstreaming:

- **Does it scale, or does it produce a table nobody reads?** A 3×3 is free; C's
  grid is not. If the honest answer is "collapse the axes first", then the rule
  needs to say how, and that guidance is the actual deliverable.
- **Is the `file:line` requirement on `n/a` sustainable?** It is the load-bearing
  half — without it the table records beliefs, and in all four occurrences the
  belief *was* the bug. But a citation that goes stale is worse than none, and
  nothing revalidates them.
- **Does it catch anything it was not designed for?** Retrofitting to one known
  pattern is easy; the question is whether it earns its cost on an unrelated item.

## Shape of the change, if it is taken

TCW's built-in `spec` stage instructions are what a project without its own
bindings gets. The seam is there rather than in the template, since the template
is this project's. Worth deciding at spec whether it is a required section, a
conditional one ("if the Design section numbers anything"), or advisory — the
current wording is conditional, and that conditionality is doing real work: a spec
with no numbered lists has no axes to cross, and demanding a table there would
produce ceremony.

## Out of scope

- The two testing rules that landed alongside it in
  `docs/lifecycle/implementation.md` (no defaulted axes in shared fixtures; one
  property, one assertion helper). Those are about tests rather than specs, and
  should be judged separately.
- Changing `tcw validate` to check the table's shape. Tempting, and a plausible
  later item, but the table's value is in the thinking rather than the syntax, and
  a validator that checks the shape would mostly confirm cells were filled in.

## Notes

- The full reasoning, the four occurrences, and the reason the previous
  countermeasure failed are in child B's `post-mortem.md`. That file lives in
  `docs/work/completed/`, which this node gitignores by design, so it is on disk
  and read with `tcw work show` rather than in the tracked tree.
- Do not upstream this until child C completes and its Coverage table has been
  looked at with the question "did this earn its cost?"
