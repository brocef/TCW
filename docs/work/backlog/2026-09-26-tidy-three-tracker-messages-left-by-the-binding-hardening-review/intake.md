# Tidy three tracker messages left by the binding hardening review

From the review of `2026-09-15-harden-tracker-binding-reads-and-writes-and-jira-response-parsing`,
each judged to need a separate change:

1. `tcw work complete`'s merge-back hint lists staged files from
   `git diff --cached --name-only`. With git's default `core.quotePath`, a
   non-ASCII path is printed escaped, and with `diff.relative=true` paths come
   back relative to the node, so the item's-own-record comparison misses. Use
   `-z` and `--no-relative`.
2. A `create_issue` answer that is not a mapping now raises the generic
   "unexpected shape" error, losing `create.py`'s "it may exist; look for a
   ticket titled…" warning — although the ticket may have been made.
3. The filing hook prints the placeholder "(creating it did not succeed)" when
   creation succeeded and only the binding failed (`_ticket_on_filing` in
   `tcw/work/cli.py`): `_tracker_link` never appends to `reasons`.

Added at verify of the same item:

4. Values inside a Jira response are not type-checked: `{"status": {"name": 5}}`
   makes `tcw work tracker show` crash with `AttributeError: 'int' object has no
   attribute 'strip'` (`_print_ticket` → `assess`). The shape checks cover lists
   and objects only.
5. Strict `drop` refuses an item whose `tracker.yaml` cannot be read with "is, or
   was, bound to a ticket", which overstates it; say the binding cannot be read.
