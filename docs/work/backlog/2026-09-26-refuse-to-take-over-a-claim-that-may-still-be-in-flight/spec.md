# Spec — Refuse to take over a claim that may still be in flight

## Capability changes

None. Recovering an interrupted claim is an existing capability; this makes it
refuse a claim that is not interrupted, and stops a lost race from publishing an
item under the wrong owner.

## Reproduction

Against `c5cfcd94`: make an interrupted claim the way
`tests/test_interrupted_claim.py::interrupt` does (the item's folder moved to
`.claiming/<slug>-<32 hex>`), start a thread standing in for a live claimant that
100 ms later stamps `owner: alice` into that folder's `state.yaml` and renames it
to `active/<slug>`, and at once call `FsWorkStore.start(slug, owner="me",
take_over=True)`.

- **Happens:** the take-over succeeds immediately; the claimant's `state.yaml`
  write raises `FileNotFoundError` (its folder is gone); the item is active with
  `owner: me`.
- **Should happen:** the take-over sees the claim publish within the 500 ms window
  and refuses; the item is active with `owner: alice`.

Script: the session scratchpad's `repro1.py`; the same shape becomes the first
test below.

## Problem

`FsWorkStore.start` (`tcw/store/fs.py:4202`) claims an item in two renames:
`backlog/<slug>` → `.claiming/<slug>-<hex>` (fs.py:4343), a stamp of `owner` and
`started` into that folder's `state.yaml` (fs.py:4346–4349), then
`.claiming/…` → `active/<slug>` (fs.py:4352).

Its take-over branch (fs.py:4224–4254), reached by `--take-over` and by the web
app's Recover (`start(..., recover=True)`, `tcw/serve/__init__.py:1006`), acts on
the claim folder **at once and in place**: it writes the recoverer's owner into
the claimant's own `state.yaml` (fs.py:4240–4247) and then renames the folder to
`active/` (fs.py:4249). Nothing checks whether the claimant is still alive. `get`
by contrast calls a claim interrupted only after 500 ms without it publishing
(fs.py:5886–5891).

Three consequences:

1. **A live claimant is robbed** (the reproduction above).
2. **The wrong owner can be published.** If the claimant's second rename lands
   between the recoverer's write and its rename, the item is published under the
   recoverer's owner while the claimant reports "started", and the recoverer's
   rename raises `FileNotFoundError` — an uncaught error from the CLI, a 500 from
   the web app (`serve/__init__.py:1017`).
3. **Either side can crash rather than report a lost race.** The claimant's stamp
   (fs.py:4346–4349) is outside every `try`, so a folder taken from under it
   raises a bare `FileNotFoundError`; its rollback (`os.replace(private, src)`,
   fs.py:4355) raises another if the folder is gone, hiding the first. And
   `dump_yaml` (fs.py:1378) truncates then writes, so a writer that opened the
   file before the folder moved still writes into it afterwards — a reader can
   see an empty or partial `state.yaml` and write back only `owner`/`started`.

**Sibling sweep, repo-wide.** Every other writer that moves an item acts through
`_mv` and git on a settled folder; `.claiming/` is written only by `start`
(`grep -n claiming tcw/`), and read by `_claiming_dirs`, `interrupted_claims`,
`get` and `_lost_the_claim`. The only other path that reaches the take-over branch
is `tcw work tracker claim --take-over` (`tcw/tracker/ownership.py:92`), which
calls the same `start`. No sibling defect outside `start`.

## Goals

1. Recovery waits the same 500 ms publication window `get` uses; a claim that
   publishes (or leaves `.claiming/`) meanwhile is refused, never taken.
2. Recovery takes the claim by an atomic rename into a staging folder of its own
   **before** it writes anything into it, so it never writes into a folder
   another process may still publish.
3. Every write of `owner`/`started` into a claim folder replaces `state.yaml`
   atomically, from a temporary file outside the item folder, so a writer whose
   folder was taken fails instead of writing into it.
4. A claimant or recoverer that loses the folder at any step reports the lost
   race through the existing `_lost_the_claim` (which names the winner once it
   publishes), never a bare `FileNotFoundError`.

## Non-goals

- A per-slug lock file (Codex's alternative). It closes the same race with
  operating-system locking semantics this adapter does not otherwise depend on;
  the rename-then-write order already makes the corruption impossible.
- A claimant that stays suspended for more than 500 ms between its renames is
  indistinguishable from a dead one and may lose its claim to a recovery. It then
  gets an honest lost-race error instead of reporting "started"; making it *win*
  would need a lock and is out of scope.
- Any change to taking over an **active** item (`--take-over` on a published
  claim), or to the CLI and web messages beyond the error they already map.

## Design

In `FsWorkStore.start`'s take-over branch, after the single claim folder is
found:

1. **Wait.** Poll `_get_now(slug)` every 10 ms for 500 ms (the loop `get` and
   `_lost_the_claim` already use). If the item appears, refuse — `AlreadyClaimed`
   with its owner and start time; under `recover=True` too, since the item is no
   longer an interrupted claim. If the found folder disappears without the item
   appearing, go to `_lost_the_claim(slug)`. Refusing publication discovered here
   does **not** fall through to taking over an active item: that needs a fresh,
   explicit `--take-over`.
2. **Steal.** `os.replace(found, .claiming/<slug>-<new hex>)`. On
   `FileNotFoundError`, `_lost_the_claim(slug)`.
3. **Stamp and publish** from the recoverer's own folder, exactly as the
   claimant does: atomic stamp, then `os.replace` to `active/<slug>`; a failure
   there is also a lost race.

For the claimant, route the stamp, the publishing rename and a failed rollback
through `_lost_the_claim`. The rollback stays: if the private folder still exists
the item returns to `backlog/` as today.

The atomic stamp is one private helper used by both: write the YAML to a
uniquely named temporary file directly in `.claiming/` (same filesystem, not
inside any item folder, and not matching the `<slug>-<32 hex>` claim pattern that
`interrupted_claims` and `_claiming_dirs` read), then `os.replace` it onto
`<claim folder>/state.yaml`. On any failure the temporary file is removed. A
crash can leave one stray temporary file in `.claiming/`; nothing reads it.

The stamp reads the existing `state.yaml` first. If the folder has gone by then,
`load_yaml` answers `{}` for an absent file, so the helper must treat a missing
folder as a lost race rather than stamping an empty state.

## Abstraction litmus test

No new store-interface operation. `start(take_over=…, recover=…)` keeps its
contract ("recover an interrupted claim, or refuse"); what counts as interrupted,
the staging folder, the wait and the atomic write are all private details of the
filesystem adapter's claim protocol, which a transactional store would implement
as a conditional update.

## Acceptance criteria

1. With a live claimant that publishes 100 ms after a take-over begins (the
   reproduction), `start(slug, owner="me", take_over=True)` raises
   `AlreadyClaimed` and the item reads `active` with `owner: alice`.
2. The same with `recover=True` raises (an `IllegalTransition` or `ValueError`),
   and the item reads `owner: alice`.
3. A genuinely interrupted claim (nothing publishes within 500 ms) is still
   recovered by `--take-over` and by the web app's Recover: every existing test in
   `tests/test_interrupted_claim.py` passes unchanged.
4. When the claim folder is taken from under a claimant between its first rename
   and its stamp (simulated by patching the stamp step to move the folder and
   publish it under `owner: bob` first), the claimant's `start` raises
   `AlreadyClaimed` naming `bob`, not `FileNotFoundError`, and the item reads
   `owner: bob`.
5. The same for a take-over whose steal loses (the found folder vanishes and
   publishes under another owner between the wait and the steal): `AlreadyClaimed`,
   no `FileNotFoundError`, the item's owner is the winner's.
6. A stamp never truncates `state.yaml` in place: after any successful start or
   take-over, `.claiming/` holds no temporary file, and the item's `state.yaml`
   keeps every field it had besides `owner` and `started`.
7. The full test suite passes.

## Risks

- Every recovery is 500 ms slower, including every existing take-over test
  (about ten). Accepted: recovery is rare and manual.
- The claimant's changed error handling touches the hot path of every `start`.
  The existing concurrent-start tests in `tests/test_work_start.py` guard it.

## Notes

- Advisors, 2026-09-29: Codex and an Opus subagent agreed on the steal-first
  order, the atomic stamp and routing every lost step through `_lost_the_claim`.
  They split on the 500 ms wait (Codex: keep; Opus: unnecessary for correctness).
  Kept, because the request asks that a claim which may still be in flight not
  be taken, and the wait is what stops a live claimant losing in the normal case.
