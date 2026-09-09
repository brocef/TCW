# Validate a slug before the claiming lookup globs with it

## What is wanted

A slug reaching the claiming lookup should be bounded the way every other
identifier entering the store is, so that what a lookup matches is decided by
the identifier's meaning rather than by the characters it happens to contain.

## The observation

`FsWorkStore._claiming_dirs(slug)` builds a glob from the caller's `slug`
without validating it, so glob metacharacters in a slug change which claim
directories the lookup matches. Separately, the take-over branch constructs
`active/<slug>` and `backlog/<slug>` directly rather than deriving them from
`_find`, so a path-shaped value reaching the store API is not bounded the way a
`_find` result would be.

Reachable through the store API, and through `tcw serve`, which passes request
values into store methods. Not reachable from the CLI in the same way, since a
slug there is usually resolved before use.

## Why it matters, and how much

Deliberately scoped down. The requester confirms `tcw serve` runs on localhost
for a single user, so no untrusted caller reaches the store API today. This is
therefore a correctness and hardening item, not a live exposure — an identifier
that means one thing and matches another is a latent defect wherever it sits,
and the existing mechanism for exactly this question is already in the codebase
and simply not used here.

It is recorded at low priority for that reason. What would change the
assessment is a deployment where someone other than the operator can reach a
running `serve`.

## Constraints

- **This is identifier validation, not symlink containment.** `_safe_store_id`
  is the existing mechanism for the question, and the claiming paths do not use
  it. Reaching for containment instead would be solving a different problem.
- **Claim recovery has to keep working.** `_claiming_dirs` is part of how a
  stale claim is found and cleared. A stricter lookup that matches nothing is
  its own failure mode, and a change that hardens the lookup while stranding
  recoverable claims is not an improvement. The recovery semantics need
  deciding before the validation is tightened, not after.

## Out of scope

The symlink containment shipped by the item this was found during. That work is
complete and this is explicitly a different mechanism, which is why it was
recorded separately rather than folded in.

## References

- [Resolve taxonomy refs against symlinks, not just lexically](tcw://W/2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically)
  — the item whose adversarial review found this and classed it as needing a
  different mechanism; its containment work is the thing this is not.

## Notes

- Asked for further reference material; none provided beyond what the intake
  already cites.
- Found by adversarial review (Codex, round 2) and recorded to the inbox on the
  requester's decision rather than folded into the item that found it.
- The exposure assessment above is the requester's answer at the request stage,
  not an inference from the code.
