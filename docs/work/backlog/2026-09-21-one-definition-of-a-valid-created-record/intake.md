# One definition of a valid created record

`created_record` in `tcw/tracker/intake.py` and `_created_key` in
`tcw/store/base.py` both decide whether a `created` record is usable. One works
over raw sidecar text, the other over already-parsed data, and both require a
non-empty `key` and `id`.

They agree today. If either loosens — accepting a key without an id, say — the
resume path in `tcw work tracker create` and the row the board renders would
start disagreeing about the same file: one would resume against a half-record
while the other showed nothing, or the reverse. `created_record` could delegate
to the shared rule after its `yaml.safe_load`.

## Origin

Found by a reviewer during the review rounds on
`2026-09-15-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item`,
which added both. Classified there as needing its own change rather than being
folded in, because the duplication is not a defect today and collapsing it
touches a path that item had already reworked four times.

## References

- `docs/work/completed/2026-09-15-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item/refined-outcome.md` — where it is recorded as a follow-up
