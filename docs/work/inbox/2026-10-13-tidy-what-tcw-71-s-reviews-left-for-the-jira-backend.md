# Tidy what TCW-71's reviews left for the Jira backend

Separate-change findings from TCW-71's verify review (2026-10-13), none of
them blocking:

1. **A dropped connection while posting a note invites a duplicate.** After a
   move with no screen, the note is posted on its own (`_post_note` in
   `tcw/work/jira/backend.py`). If that request drops after Jira received it,
   `MovedWithoutNote` says posting failed, which suggests posting again and so
   duplicating the comment. It could say the note may have been posted, or
   check the newest comments first.
2. **Two shapes of Jira's answers were never seen live.** `TCWTEST` has only
   global transitions and never needed a second results page, so
   `tests/work/jira/recorded/` has no `links.*.fromStatusReference` in the
   workflow definition, no `nextPageToken` from a search, and no transition
   screen that lists fields. The fake's versions of these are unchecked against
   Jira. A transition restricted to some statuses and a search over more than
   100 tickets on `TCWTEST` would record them.
3. **The user objects in `recorded/` keep `timeZone` and `locale`.** Not
   identifying on their own, but `capture.py` could replace them too.
