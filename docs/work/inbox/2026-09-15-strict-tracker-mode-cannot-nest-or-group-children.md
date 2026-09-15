# Strict tracker mode cannot nest or group children

Found while specifying
`2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes` (its Risk 6).

Under `work.tracker.strict: true`, `tcw work new` is refused for everything but an
epic, so `tcw work new --parent <slug>` and `tcw work new --initiative <epic>` are
unavailable. `tcw work tracker import` creates items but takes neither option. A
child for an initiative can still be made by importing and then setting
`initiative` with `tcw work edit`; nesting under a parent cannot be done at all.

Options: give `tracker import` `--parent` and `--initiative`, or let `new --parent`
and `new --initiative` through and require `tracker link` before the child starts
(the start gate already refuses an unbound child).
