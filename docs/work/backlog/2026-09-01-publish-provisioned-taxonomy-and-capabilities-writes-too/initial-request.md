# Publish provisioned taxonomy and capabilities writes too

## The request

Extend publication from the work store to the other two component trees, so an
edit made to a provisioned taxonomy or capabilities tree survives the session
that made it.

## Why this exists as a separate item

Child B of
[the store-home-repository epic](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it)
made all three component trees declarable and provisionable. Child C
([Publish provisioned-store writes to their remote](tcw://W/2026-08-26-publish-provisioned-store-writes-to-their-remote))
adds publication, but its epic boundary is work transitions, so it leaves the
trees able to be *fetched* and not able to be *kept*.

The gap is real and has the same shape as the one the initiative was filed for. A
cloud session can provision a declared taxonomy, run `tcw taxonomy add`, and lose
the term when the container is reclaimed — with every command having reported
success.

## Why it is not simply "do the same thing again"

The work store's publication hooks into a **transition**: `_effect_transition`
(`tcw/store/fs.py:4154-4202`) is one function through which every status change
passes, so child C has exactly one seam and can define "before" and "after"
against it.

The tree stores have no such choke point. `tcw taxonomy add`, `rm`, `set`,
`extends`, and the capabilities equivalents each write through their own path,
and they are ordinary writes rather than a state machine's transitions. So the
questions child C answers by placement have to be answered differently here:

- **What is the unit of publication?** Every individual write, or something
  coarser? Pushing on each `tcw capabilities set --field` would mean a network
  round trip per field.
- **Where does the refresh go?** Child C refreshes before a transition because a
  transition reads state to decide. A tree write may not read anything first.
- **Is there a batch story?** Seeding a taxonomy writes dozens of terms. Under
  child C's per-transition model that is dozens of pushes.

An explicit "publish my pending changes" verb is worth considering here even
though child C rightly did not need one.

## What child C leaves ready

Child C's spec puts publication in the `WorkStore` ABC as a store property —
`publishes`, `refresh()`, `publish()` — rather than as a verb on each transition,
and its abstraction litmus table justifies that placement. The intent was that the
tree stores adopt the same three members without redesign; whether that survives
contact with the questions above is this item's first job to check.

Section A of child C's spec also settles which stores publish, by ladder rule
(rule 2 publishes; rules 1 and 4 do not). That answer should carry over unchanged
— it is about the declaration, not about the component.

## Constraints

- **Only publication may reach the network**, on top of the provisioning verb.
  The package-wide rule in `tests/test_subprocess_stdin.py` is where that is
  enforced.
- **A non-provisioned tree behaves exactly as it does today** — no network, no new
  failure modes, no new configuration.
- **Divergence is reported, never merged**, matching child C.

## Blocked by

Child C, recorded as a `blocked-by` so `tcw work start` refuses past it rather
than relying on this sentence. The dependency is real rather than a scheduling
preference: this item consumes the `publishes`/`refresh()`/`publish()` interface
child C defines, and child C may still change it.

## Notes

- Raised during child C's `spec` stage and deliberately scoped out there rather
  than silently omitted; child C's Non-goals section names it.
