# Record a blocker naming a resolved item as a slug, not as free text

## What happened

On 2026-09-16, opening the children of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`,
the coordinating session ran:

```sh
tcw work edit <child> --blocked-by 2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments
```

That item was already completed and its folder removed from the board
(`tcw work show` reports it `(resolved)`, "last present in commit 4002ffb3").
The edit wrote:

```yaml
blocked_by:
- external: 2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments
```

An `external:` blocker is free text and never resolves, so the child could never
have started. The same slug written as `slug:` by the request stage on the epic
itself resolved correctly and `tcw work start` on the epic passed.

## Cause (read, not yet tested)

`WorkStore._entry_for` (`tcw/store/base.py`, around line 3150) decides the entry
kind with `self.get(ref) is not None`, which only sees items still on the board.
A slug the store has resolved and recorded in `graveyard.yaml`
(`self.tombstone(slug)`) is treated as unknown text.

## What is wanted

- A ref naming a resolved item the store has a record of is written as
  `slug:`, the same as a live item. Probably also worth a message saying the
  blocker is already resolved, since blocking on finished work is usually a
  mistake.
- Check every other caller that classifies a ref the same way (`new
  --blocked-by`, `edit --blocks`, `--unblocked-by` matching) for the same shape.
- Existing `external:` entries whose text is exactly a recorded slug: decide
  whether `tcw validate` should report them.

## Related

- `2026-09-09-resolve-a-cross-node-external-blocker-against-the-node-that-owns-it`
  — a different case (another node's item written as `external:`), same symptom.

## Origin

Found by the coordinating session while implementing the epic above;
the requester asked for it to be filed as a work item on 2026-09-16.
