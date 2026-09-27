# Spec — Stop an item reaching implement without a spec and plan, and say how to plan an item started too early

## Capability changes

None planned. The ledger has no row for stage legality; if the capabilities
step at implement finds one, it is `changed`.

## Reproduction

In any node: `tcw work new "X"`, then `tcw work start <slug>` with no spec or
plan. `start` prints only `started <slug>`. `tcw work stage gate spec <slug>`
exits 1 with "'spec' is not legal for an item in 'active'; it runs in backlog",
as does `plan`. `tcw work stage gate implement <slug>` exits 0.

## Problem

- `STAGE_STATUSES` (`tcw/store/base.py:2243`) makes `spec` and `plan` legal only
  in `backlog`; no verb moves `active → backlog`, so the two gates can never pass
  again. `tcw work scaffold` uses the same table (`tcw/work/cli.py:2222`).
- `_start` (`tcw/work/cli.py`) never reports the missing documents, although
  `skills/work/references/transitions.md:61` calls `plan.md` a check at start.
- The `implement` gate checks only status; this repo binds nothing to it
  (`tcw-config.yaml` binds `require_artifact.py spec` only to `plan`).

## Goals

1. `spec` and `plan` are legal in `backlog` and `active`; their bound `pre`
   checks run as usual. `scaffold spec|plan` follows.
2. `tcw work start` (success path) prints a warning to stderr naming whichever
   of `spec.md`/`plan.md` is not present (as `store.artifacts()` reports), and
   how to write them now (`tcw work stage gate spec|plan <slug>`). Exit code is
   unchanged.
3. `tcw work stage gate implement` prints the same kind of warning when either
   is absent, before running bound checks; it does not refuse on its own.
4. This repo binds `python scripts/require_artifact.py spec` and `... plan` as
   `pre` on `implement`, so here the gate refuses.
5. `STAGE_NEXT_STEPS["plan"]`, the plan prompt, transitions.md and the work
   skill say what to do for an item already active.

## Non-goals

- A verb that moves an item back to `backlog`.
- `request` in `active` (an item cannot exist without some request text; not
  reported).
- Refusing `start` without a plan: small items skip planning on purpose.

## Design

Warnings are computed in the CLI from `st.artifacts(bare)` (`present` flags,
so whitespace-only reads as missing). One helper builds the sentence for both
call sites. The next-step test's no-overlap rule gets a written exception for
`plan`, whose text names both branches.

## Abstraction litmus test

No new operation. `artifacts()` is already on the store interface; the legality
table is lifecycle contract data.

## Acceptance criteria

1. On an active item, `stage gate spec` and `stage gate plan` exit 0 when their
   checks pass; `plan`'s bound check still refuses without a spec.
2. `scaffold spec` on an active item writes a draft.
3. `start` of an item with no spec/plan exits 0 and stderr names both missing
   documents and the gate commands; with both present, no warning.
4. `stage gate implement` on an item missing plan warns on stderr; with no
   bound checks it exits 0; in this repo's config it exits non-zero.
5. `review`/`completed` items still refuse `spec`/`plan`.
6. Full suite passes.

## Risks

Tests that spell the legality table out literally must change with it.
