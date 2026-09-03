# Refined outcome — An auto-delete step with hooks

_Accepted._

## Decision

Accepted. Both named scenarios are exercised as real commands rather than as
fixture stand-ins, and the failure path — the one that decides whether a
consumer can trust this with their only copy — keeps the item and says so.

## Evidence

- **Suite:** 2303 passed; the established environmental failures only.
- **The S3 shape works**: a `pre` that tars `$TCW_ITEM_PATH` produces an archive
  containing the item's `state.yaml`, and the item is gone afterwards. That is
  the whole feature, checked end to end.
- **The folder-move shape works**: a `pre` that `mv`s the item away completes
  without error, and the record still names the commit. This is the case that
  would otherwise have been reported as a bug later.
- **A failing archive costs nothing.** The item stays resolved, recorded and
  committed; the message names `tcw work delete <slug>`; and the follow-up verb
  finishes it. Three separate tests.
- **The retained path is untouched**: a status the project keeps runs no
  `auto-delete` bindings at all.
- **`skill:` is reported, not run**, and the removal proceeds — so the
  documentation's "a guarantee belongs in a `command:`" is a true statement about
  the code, not advice.

## Deferred follow-ups

- **`tcw serve` says nothing about a pending removal.** Deferred with reasons
  recorded at the payload builder: the DTO is versioned, closed, fully required,
  and shared with the CLI's `--json`. Worth its own item, together with whatever
  else the next schema version carries.
- **Nothing verifies a consumer's archive actually happened**, and nothing can.
  Stated in the capability and the README rather than left implied.
- **No timeout guidance is enforced.** A slow upload will hit the binding timeout
  and keep the item, which is the safe direction; the documentation says to raise
  the timeout rather than remove the hook.

## Closeout choices

- **Merge route:** the session branch.
- **Documentation:** README with both worked examples; release notes; changelog;
  the `tcw-work` transitions reference gains an `auto-delete` section (a parity
  test requires one); the commands reference gains `tcw work delete`.
- **Capabilities:** `work/archive-a-resolved-item-before-it-is-deleted`
  (`cap-240fde`) `Missing` → `Supported`; `work/configure-the-work-lifecycle`
  updated for the two new variables and the new step.
- **Version:** deferred to the end of the run — the last of five items, so the
  cut is now due.
- **Originating GitHub issue:** none.

## Notes

The correction that matters is architectural: item 4 put the deletion in the
store and item 5 had to take it out again. The plan for item 5 assumed the hook
points could be threaded into the store's transition; they could not, because the
codebase has an explicit rule against a store method that shells out. Splitting
retention and its hooks across two items is what let that go unnoticed until the
second one — the alternative, one larger item, would have found it at spec time.
