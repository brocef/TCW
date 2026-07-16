# Refined outcome

## Verification decision

Approved for closeout by the user after an independent code review and two
resulting fixes. Resolution: **done**. Landed on `main` (no branch/PR route).
Patch release **v0.11.4**. One follow-up item created (see below).

## Refinements after the initial implementation

An independent `targeted-code-reviewer` pass (run against `013a25e..HEAD`) found
the core fix sound — one shared resolution for both writers, null semantics
matching `_apply_override`, a stable revision that leaves local capabilities
byte-identical, and no path that clobbers a local capability or the upstream
node. It surfaced two edge defects, both reproduced directly before fixing and
both fixed in commit `85d4474`:

1. **A second alias exporting the same path was permanently un-settable.** The
   collision guard was `_is_capability(d)` — true for *override* folders too, not
   just local capabilities — so once `one/a/thing` had an override at the
   mirrored `a/thing`, `set two/a/thing` hit that folder and refused, with a
   message that was factually wrong (no local capability there) and advice that
   was impossible (`set a/thing` resolves to the *other* alias). That reinstated
   this item's own bug one level in: `show` accepted the path, `set` refused it,
   hand-authoring was the only route. The refusal existed only for want of an
   alternative location, so it now falls back to `<alias>/<upstream-path>`. A
   local declaration is still never clobbered, and no path `show` accepts is
   refused. This is a shape the reporter's 5-node federation could plausibly hit.

2. **`update_capability(body=None)` on an inherited capability silently
   re-inherited.** It wrote an empty `description.md`, which `_apply_override`
   reads as "no body delta", so the upstream body returned with no signal the
   clear was ignored, and a stray file was left behind. The re-inherit is
   *intended* — an empty override body is what makes append-only overrides work,
   and an existing test pins it — so an empty override body is inexpressible by
   design. Kept that behavior, dropped the stray file, and documented the
   asymmetry (`None` clears a *field* but re-inherits an *override body*;
   `Status: Omitted` is how a node says "we deliberately don't have this").

## Key decisions about deferred work

- **Drop-an-override gap → follow-up item created.** `set` can now create an
  override but nothing reverts one to the upstream value except deleting the
  folder by hand — the same complaint this item fixes, one level down. Captured
  as a new backlog item (`tcw capabilities reset` / `remove --override`; design
  decided when planned).
- **Redundant no-op override** (setting an inherited capability to the status it
  already inherits writes an override asserting the same value) — left alone;
  harmless and arguably an intentional local assertion.

## Final verification evidence

- **Full suite: 572 passed** (`python -m pytest tests/ -q`), up 5 from the
  pre-fix 567 across three test files; no regressions across the review fixes.
- `tcw validate` and `tcw capabilities check` clean on this node, including after
  the ledger flip.
- The reviewer's two repro scripts re-run directly after the fix: `set two/a/thing`
  succeeds without disturbing `one`, and `body=None` leaves no stray file and
  re-inherits.
- The reporter's original transcript (issue #3) succeeds end-to-end against two
  scratch git repos, upstream node untouched. Pre-fix baseline captured first
  confirmed the report against v0.11.3.

## Capabilities reconciled (ledger flip)

- `capabilities/set-a-capabilitys-status` `Partial` → `Supported`; stale `Gaps`
  dropped (commit `9030e42`).
- `capabilities/override-inherited` stays `Supported`; empty `description.md`
  given a body naming the `set`-driven route.

## Closeout choices

- Resolution `done`, on `main`, no PR.
- Documentation sync: README, `skills/tcw-capabilities/SKILL.md`, changelog, and
  release notes updated across the implementation and review-fix commits.
- Version: patch → v0.11.4 (`scripts/cut_version.py patch`).
- Follow-up: drop-an-override backlog item created.

## Evidence caveat

Independent review is a single `targeted-code-reviewer` pass. The mandated local
`bllm-review-many` round was skipped at the user's direction; the reviewer's own
`bllm` attempt was inconclusive (tty constraint). Both defects above were found
by reading and confirmed by execution, not inferred.
