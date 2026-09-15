# The init ignore guard probes fixed path names that a rule could collide with

## The request

`tcw work init` decides whether items written into a status folder would be
tracked by asking `git check-ignore` about a representative item path built from
fixed names — `<status>/an-item/state.yaml`, or `inbox/an-item.md`. A repository
whose ignore rules happen to name those exact paths gets an otherwise usable
store refused, with a message blaming the folder rather than the rule.

The intake filed this as "worth revisiting only if a better probe exists". One
does, so the requester asked for the fix rather than a `wontfix`.

## Constraints

- **Probe two differently-named representative paths and refuse only when both
  are ignored.** The requester named this approach. A rule naming two distinct
  literal item names is effectively impossible unless it is the broad rule the
  guard exists to catch, so the false refusal goes away without the guard
  getting weaker.
- **Do not weaken what the guard already catches.** The probe must still be a
  representative *payload* path, not the folder or its `.gitkeep`: `<status>/*`
  with a `!<status>/.gitkeep` negation is TCW's own shape, and asking about the
  folder makes TCW's scaffolding refuse itself. The existing comment in
  `tcw/store/fs.py` records why each rejected alternative was rejected.
- `completed/` and `discarded/` stay skipped — their contents are ignored
  deliberately.

## Out of scope

- Write-time ignore enforcement, which is a separate item
  (`2026-08-20-enforce-the-gitignore-trap-at-write-time-not-only-at-init`).

## References

- `docs/work/completed/2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository/refined-outcome.md`
  — "Deferred, with the user's agreement" item 2 is this request.
- `tcw/store/fs.py`, the `init` scaffolding guard — its comment block already
  documents the alternatives that were tried and why they failed, which bounds
  what a replacement probe is allowed to be.
- `intake.md` — the raw filing, including its own "narrow, and preferable to the
  alternatives" assessment.

## Notes

Asked for further reference material; none beyond the above provided.

The intake leaned toward leaving this alone. The requester overrode that on the
strength of the two-probe approach being a small change; if the spec finds it is
not small, say so rather than building it out.

Batched with the other four `bug`-tagged items into a single patch release.
