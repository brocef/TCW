# Implementation plan

Five tasks. The parity test lands **before** the documents it guards, so the
documents are written against a failing check rather than blessed by one written
afterwards to fit them.

## Task 1 — the parity test, red

`tests/test_skill_lifecycle_parity.py`, written against `LIFECYCLE_STEPS` and the
directory layout the spec describes. It fails at this point; that is the point.

Helpers it needs, kept small and local:

- `sections(path) -> dict[str, str]` — split a Markdown file on `## ` headings.
- `artifacts_in(text) -> set[str]` — every `<name>.md` mentioned.

Assertions: one document per id and no orphans; `Produce` covers the table's
`produces`; `Inputs` covers the table's `inputs`; five sections in order; every
marker one of the four; no ordinals; no reference to a deleted filename; the
router lists every stage document once and is ≤60 lines.

Mark it `xfail(strict=True)` for this commit only, so the suite stays green at
the boundary and the *next* commit is what flips it. A test that is simply
failing invites someone to weaken it; an `xfail` that must become a pass does
not.

## Task 2 — the seven stage documents

`stage-inbox.md`, `stage-request.md`, `stage-spec.md`, `stage-plan.md`,
`stage-implement.md`, `stage-verify.md`, `stage-postmortem.md`.

Five sections each: Purpose / Inputs / Produce / Steps / Exit. Every step carries
an actor and a marker. Every document carries the harness-neutral methodology
step — *run `tcw work lifecycle --stage <id>` and honor any binding* — and, where
relevant, its own harness fallback rather than deferring to the router.

Two are not the common shape and must not be forced into it: `inbox` produces no
artifact, `verify` produces one of two depending on the verdict.

Content comes from `task-lifecycle.md` and `epic-lifecycle.md`, **read against
what children 1–2b actually shipped** rather than copied. Both predate the
`review` status, `submit`/`rework`, transition auto-commit, and bindings.

Remove the `xfail` marker. The suite going green here is the deliverable.

## Task 3 — the cross-cutting references

`transitions.md` (all five, each with its gates and markers), `hooks.md`,
`delegation.md`, `epic-deltas.md`, `cross-node-deltas.md` (from
`cross-node-epic.md`), `tags.md`, `commands.md`.

`epic-deltas.md` and `cross-node-deltas.md` are **deltas only** — what differs
for an epic or a cross-node slice, never a second copy of the lifecycle. That is
the whole reason `epic-lifecycle.md` could drift from `task-lifecycle.md`.

## Task 4 — the router, and the deletions

Rewrite `SKILL.md` to ≤60 lines against the destination table in the spec. Then
delete `lifecycle.md`, `task-lifecycle.md`, `epic-lifecycle.md`, and
`process-inbox.md`, and grep the whole repository for each name — commands,
skills, README, and the other references all link to them.

Rename the tcw-capabilities "planning gate" to "planning check" wherever it
appears.

## Task 5 — commands, the agent, and doc sync

`tcw-process-inbox` and `tcw-verify-work` are new; `tcw-plan-work` and
`tcw-drive-work-to-completion` are retargeted at the new documents. Each names
its stage range and stays thin. Every command's workflow must also be reachable
by invoking the skill directly, because Codex has no slash commands.

`tcw-verifier`: read-only, `agents/` plus the Claude manifest key. **Drop it and
record why if it needs more than that** — it is the least load-bearing item here
and the epic's own rule is that a custom agent earns its place only by needing a
different tool set.

Doc sync: `README.md` (skill/command surface), the changelog, and release notes.
`plugin/work-lifecycle`'s capability text.

## Verification

1. The parity test passes, and fails when a stage document's `Produce` is edited
   to disagree with `LIFECYCLE_STEPS`. Prove the second by hand.
2. `tcw validate`; the full suite; the plugin-manifest tests.
3. `grep -rn` for each deleted filename returns nothing.
4. Manual sign-off on the two prose criteria — no rule stated twice, and every
   stage document followable by a Codex agent with no injection, no custom
   agents, and no slash commands. **Not claimed as test-verified.**
