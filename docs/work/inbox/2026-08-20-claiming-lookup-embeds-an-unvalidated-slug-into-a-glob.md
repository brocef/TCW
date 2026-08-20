# `_claiming_dirs` embeds an unvalidated slug into a glob

## Origin

Found by adversarial review (Codex, round 2) during
`2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically`, and
classed by that review as needing a different mechanism than the symlink
containment that item ships. Recorded here rather than folded in, on the user's
decision.

## Problem

`FsWorkStore._claiming_dirs(slug)` builds a glob from the caller's `slug`
without validating it, so glob metacharacters in a slug change which claim
directories the lookup matches. The take-over branch separately constructs
`active/<slug>` and `backlog/<slug>` directly rather than deriving them from
`_find`, so a path-shaped value reaching the store API is not bounded the way a
`_find` result would be.

Reachable through the store API and through `tcw serve`, which passes request
values into store methods. Not reachable from the CLI in the same way, since a
slug there is usually resolved before use.

## Shape

This is identifier validation, not symlink containment — `_safe_store_id` is
the existing mechanism for exactly this question, and the claiming paths do not
use it. The likely fix is routing the slug through it and deriving the
take-over paths from `_find`, but the claim-recovery semantics need thought
before that: `_claiming_dirs` is part of how a stale claim is found and cleared,
and a stricter lookup that matches nothing is its own failure mode.

Not a symlink bug and not urgent — it needs a caller passing a path-shaped or
metacharacter-bearing slug straight to the store API.
