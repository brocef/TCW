# Plan — Refuse to take over a claim that may still be in flight

Worked in a `--worktree` branch, tested with a private virtual environment that
points at the worktree, so the shared `tcw` install (the primary checkout on
`main`) stays the stable CLI that drives this item's lifecycle.

## Tasks

1. **Failing tests first** — `tests/test_interrupted_claim.py`, a new section
   "a claim that may still be in flight". One shared helper,
   `live_claimant(private, owner, after)`, runs a thread that stamps `owner` into
   `private/state.yaml` and renames `private` to `active/<slug>` after `after`
   seconds, recording whether its rename succeeded.
   - AC1: take-over during a live claim → `AlreadyClaimed`; item owner `alice`.
   - AC2: `recover=True` during a live claim → raises; item owner `alice`.
   - AC4: claimant loses its folder at the stamp (monkeypatch the new stamp
     helper's first call to move the folder and publish it as `bob`) →
     `AlreadyClaimed` naming `bob`.
   - AC5: take-over's steal loses (monkeypatch the wait to return, then move and
     publish the found folder as `bob` before the steal) → `AlreadyClaimed`
     naming `bob`, no `FileNotFoundError`.
   - AC6: after a normal start and a take-over, `.claiming/` has no file other
     than claim folders, and `state.yaml` still carries `title`, `created`,
     `tags`.
   Proof: AC1 and AC2 are red on the current tree (the reproduction); AC4 red
   with `FileNotFoundError`. AC5 and AC6 name a helper that does not exist yet,
   so they are written against the tree after task 2 and then mutation-checked
   (revert the steal to an in-place write → AC5 red; swap the atomic stamp back
   to `dump_yaml` → confirm AC6 still has a way to go red, or say it cannot).
2. **Claim protocol** — `tcw/store/fs.py`, `FsWorkStore.start` and a new private
   `_stamp_claim(folder, owner, started, parent=None)`:
   - `_stamp_claim` reads `folder/state.yaml`, raising `FileNotFoundError` if the
     folder is gone; sets `owner`, `started` (and `parent` when given); writes a
     temporary file in `.claiming/` named `.stamp-<uuid hex>.yaml`; `os.replace`s
     it onto `folder/state.yaml`; removes the temporary file on any failure.
   - Claimant path: the stamp, the publishing rename and a failing rollback all
     go to `_lost_the_claim(slug)`.
   - Take-over path: the 500 ms wait (refuse on publication, lost race if the
     found folder vanishes), the steal into a fresh `.claiming/<claimed>-<hex>`,
     then `_stamp_claim` and the publishing rename, each loss routed to
     `_lost_the_claim`.
   Proof: task 1's tests green; `tests/test_interrupted_claim.py`,
   `tests/test_work_start.py`, `tests/test_tracker_ownership.py` green.
3. **Full suite** — `pytest -q -n auto` from the worktree with the private
   environment (the CI invocation is bare `pytest`).

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` — **fires** (Any-Code-Change): Fixed
  entry naming the claim protocol change.
- `docs/release-notes/upcoming/<slug>.md` — **fires** (Public-API, user-facing
  behavior): recovering a claim that is still being made is now refused rather
  than taking it; recovery takes half a second longer.
- `README.md`, `docs/guide/*` — evaluate: fire only if either describes
  recovering an interrupted claim in a way the wait contradicts
  (`grep -rn "take-over\|interrupted claim" README.md docs/guide`).
- `skills/work/SKILL.md` and its references — evaluate the same way; the
  take-over is described in `references/transitions.md` / `commands.md`.
- `skills/configure/references/*` — does not fire: no configuration key.

## Verification

The suite covers the race by threads and patches. Beyond it: run the
reproduction script against the worktree and confirm it now prints the
recoverer's refusal and `owner now: alice`; then drive a real interrupted claim
from the CLI (`tcw work start <slug> --take-over --owner me` in a scratch node)
and confirm it still recovers.
