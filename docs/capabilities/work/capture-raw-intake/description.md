As a user, the raw input a work item started from is preserved as its own
artifact, `intake.md`, instead of being folded into a request I did not write.
I pipe text into `tcw work new "<title>"` and it lands in `intake.md` verbatim;
I run `tcw work inbox accept <entry>` and the entry's body, its manifest of
preserved resources, and the note standing in for a binary primary all land
there too. Creating an item with nothing piped writes no body file at all.

`tcw work show` displays the intake as the item's body until a request exists,
and `tcw work list` marks it with a lowercase `i` ahead of `R`, so I can see at a
glance which items hold raw input and which have had their `request` stage
written. Editing an item's body always writes the request and never the intake:
on an item that has only intake, that edit promotes the item and says so, and
the intake is left byte-for-byte as it arrived.
