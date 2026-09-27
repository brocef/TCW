# Outcome: make start --take-over recover an interrupted claim from the CLI and the web app

## What shipped

- **Store + CLI** — `55580e40`: `WorkStore.interrupted_claims()` (default `[]`;
  `FsWorkStore` lists `.claiming/<slug>-<32 hex>` folders whose slug is not
  settled, each as the item it was, status `backlog`). `_start` uses the
  interrupted claim as the item for the `pre` hook, `before` and `previous`
  under `--take-over`.
- **Web** — `db04bdbe`: `GET /api/work/interrupted-claims`; the start action's
  `recover: true`; `_strict_refuses` reads an interrupted claim; the
  `InterruptedClaims` notice with a Recover button; `tcw/serve/dist` rebuilt.
- **Docs** — `00e3c7b6`, `4ac1d0cc`; the notice's inset — `4e9980ab`.
- **Review round 1** — `c648c966`: `start(..., recover=True)` in the store
  (refuses a settled item against the read it acts on); strict recovery runs the
  ticket claim with the binding from the claimed item; descendants' claims
  listed; tests for each; docs corrected. Spec revised to match.
- **Review round 2** — `0ca061b9`: `bound_from_value` beside `binding_value`;
  one `_board_roots` for the board and the claims list; a blocked strict
  recovery test; the race wording.

## Tests

- New tests went red on the old code for the stated reasons (the `get` raise;
  404 for the route; the hook not seeing the item's tag), and the round-1 and
  round-2 tests went red under the matching mutation (strict claim skipped,
  recover-only check removed, blockers early-return restored).
- `tests/test_interrupted_claim.py`: 16 passed; with strict and serve tests, 279.
- vitest 69 passed; tsc, eslint, prettier clean. Playwright 14 passed.
- Full Python suite on the final code: see `refined-outcome.md`.
- Hands-on: a scratch node with an item moved into `.claiming/` by hand. The
  CLI recovered it with `--take-over --owner`. In a headless browser (the
  extension was connected only to the default Chrome profile, which this run
  must not drive) the web app showed the notice, Recover made the item active
  for `TCW_WORK_OWNER`, and the notice went away.

## What the plan or spec got wrong

- **Strict mode.** The spec skipped the ticket claim on recovery, assuming the
  interrupted start had already claimed it. Review showed it may not have
  (strict mode turned on later, or the ticket changed hands). Recovery now
  claims like any strict start. The spec was revised.
- **The web's own check raced the store.** Checking "is it an interrupted
  claim?" in the handler and then calling a take-over could take a
  just-published item from its owner. The check moved into the store
  (`recover=True`), so the web refusal is 422, not 409 as first specified.
- **The spec's race statement was wrong**; corrected, and the remaining
  in-flight race filed as
  `2026-09-26-refuse-to-take-over-a-claim-that-may-still-be-in-flight`.
- `interrupted_claims` has no descendants test; the listing shares
  `_board_roots` with the board, which is tested.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | No | — |
| `docs/guide/jira.md` [Tracker-Change] | Yes | Strict start row: recovery claims first. |
| `docs/guide/<topic>.md` | Yes | `work.md`: recovery from the CLI and the web app. |
| `docs/release-notes/upcoming.md` | Yes | One line. |
| `docs/changelogs/upcoming.md` | Yes | Two Fixed entries. |
| `skills/<component>/SKILL.md` | Yes | `skills/work/references/commands.md`. |
| `skills/configure/references/` | No | — |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Spec: CLI — catch the error and pass no item (A), or a store read for an
  interrupted claim (B)? Web — accept the flags only (C), or list and offer
  Recover (D)?** Codex: B, D; warned against catching error text and against a
  web flag that could take over active items. Opus: B, D; noted strict mode
  would otherwise start with no claim, and that the web picks no owner today.
  Chose B and D, web recovery-only, owner from the server's identity.
- **Strict recovery (first pass): skip the ticket claim.** Decided by the
  coordinating session, not an advisor; the review showed it wrong and it was
  reversed.
- **Code review round 1** (adversarial-code-reviewer): NOT DONE — S1 web race,
  S2 strict recovery, S3 descendants. All fixed.
- **Round 2**: DONE. Folded in the minor notes; filed the in-flight race; left
  the Recover button without an in-flight state (a second click is refused
  harmlessly) and moving `_local_owner` out of the CLI module, both judged not
  worth their own change now.
