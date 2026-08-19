# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Stage instructions name the file your item actually has

When you ask `tcw work stage spec` or `tcw work stage plan` what to do, the
instructions used to tell you to read `initial-request.md` — a file many items
do not have. An item created by piping text into `tcw work new`, or accepted
from the inbox, starts life with its raw arrival in `intake.md`, and the request
only gets written when you run the `request` stage.

Now the instructions name whichever one the item really has, and explain the
difference: the intake is what arrived, kept word for word, and the request is
the written-up version. On an item that has only an intake, the instructions say
to read that as the request instead of drawing conclusions from the missing
request. On an item with neither, they name no file at all rather than sending
you after one.

The post-mortem instructions read the intake too — on an item that came from the
inbox it is the earliest thing in the item's history, which is usually where a
post-mortem is headed.

The guides that ship with the plugin carried the same assumption and have been
corrected. The most visible one: issue triage used to write the request for you
at the moment it accepted an issue, which made every triaged item look like a
stage had run that had not. Triage now files the reporter's words as intake and
leaves the request to the stage that writes it.

