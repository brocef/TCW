# Outcome: Refuse web writes to sidecars a command generates

## What shipped

1. **Refusal** — `fde5b11e`. `WORK_SIDECARS`' `generated` value names the owning
   command (`tcw work reconcile`; `tcw work tracker import, link or unlink`) instead
   of `"yes"`. `PUT /api/work/<slug>/sidecars/<name>` returns 409 with
   "`<name>` is written by `<command>`, not edited; run that command instead." right
   after the registered-name check, in every mode. The strict-only `tracker.yaml`
   check in the route and its branch in `_strict_refuses` are removed. Tests: new
   `test_write_generated_sidecar_refused` (both sidecars; folder bytes unchanged;
   discovery still reports `generated` true/true/false) in
   `tests/test_serve_write.py`; the strict web test asserts the `tracker.yaml` PUT
   separately, by its new message.
2. **Docs and capability** — `1c88aeb0`: `web/editing` capability, changelog
   (Fixed), release note; `capabilities.yaml` declares `web/editing`.
3. **Review fixes** — `d226e503`: `skills/work/references/commands.md` said the
   server refuses a `tracker.yaml` write only under strict mode, and its strict table
   listed the PUT as strict-only; `work/require-tracker-backed-work` now points at
   `web/editing` for that refusal.

## Evidence

- The new test failed first (200, not 409) for both sidecars.
- Mutation: replacing the refusal with `if False:` turns both new cases and the
  strict web test red; restored.
- Targeted: `tests/test_serve_write.py tests/test_tracker_strict.py
  tests/test_serve.py` — 207 passed.
- Hands-on: a `TcwServer` on a scratch project, `curl -X PUT` — `rollup.md` 409 and
  `tracker.yaml` 409 with the messages above; `capabilities.yaml` 200 and written;
  no `rollup.md` or `tracker.yaml` created.
- Full suite at `79bef735` (this item plus the Codex-gaps and taxonomy-rm items as
  first committed): 3625 passed. Later commits do not touch this item's files.

## What the plan or spec got wrong

- **The plan's Documentation Sync said no skill fires.** `skills/work/references/commands.md`
  described the strict-only refusal and became false; found by code review, fixed.
- My first hands-on script passed a string root to `TcwServer`, which needs a
  `Path`, and every request 500ed — a harness mistake, rerun correctly.

## Autonomous decisions

Run unattended under `autonomous-work`; these replace the human checkpoints.

- **No advisor consulted for design** — the request fixed the shape (refuse in the
  server, name the command) and left no open question.
- **409 vs 403/422 for the refusal.** Chose 409, the status the route already used
  for the strict refusal. Review noted the web client shows any 409 as a stale write;
  not reachable for generated sidecars today (no edit control), so filed as
  `2026-09-17-the-web-client-shows-any-409-as-a-stale-write` rather than changing
  the status here.
- **Review findings accepted:** `skills/work/references/commands.md` and
  `work/require-tracker-backed-work` described the refusal as strict-only (fixed in
  `d226e503`).
- **Review findings rejected:** none. Noted without action: `POST …/actions/tracker.yaml`
  under strict mode now answers 400 "unknown action" instead of the old strict 409 —
  arguably more correct.
- **Verifier note: backticks around the command in the message** differ from the
  spec's literal wording. Kept — the criterion asks that the command be named, and
  TCW's other refusals format commands the same way.
- **Verify decision:** accept. Verifier: criteria 1-5 met with its own hands-on
  run; criterion 6 met by the 3625-test run.
- **Interruption:** the machine crashed during the first combined suite run and
  verification; both were rerun from scratch.
