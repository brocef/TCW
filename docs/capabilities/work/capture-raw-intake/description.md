As a user, the raw input a work item started from is preserved as its own
artifact, `intake.md`, instead of being folded into a request I did not write.
I pipe text into `tcw work new "<title>"` and it lands in `intake.md` verbatim;
I run `tcw work inbox accept <entry>` and the entry's body, its manifest of
preserved resources, and the note standing in for a binary primary all land
there too. Creating an item with nothing piped writes no body file at all.

Piping is never a trap. Running the command with nothing piped — including from
a script, a CI job, or a hook that leaves its own input open — creates the item
without intake and tells me so, rather than waiting for input that is not coming.
If text starts arriving and then stops, the command **refuses** instead of
storing what it got: a fragment kept as `intake.md` would look exactly like a
document I meant to write, and "verbatim" would stop being true. When a producer
is genuinely slow, `TCW_STDIN_TIMEOUT` buys it more time.

`tcw work show` displays the intake as the item's body until a request exists,
and `tcw work list` marks it with a lowercase `i` ahead of `R`, so I can see at a
glance which items hold raw input and which have had their `request` stage
written. Editing an item's body always writes the request and never the intake:
on an item that has only intake, that edit promotes the item and says so, and
the intake is left byte-for-byte as it arrived.

The same holds for something that changes the request later — a decision, a
clarification, a new constraint. It is appended to the request under a dated
`## Added` heading and never to the intake; an item that has only intake gets
its request written first. Once the item has a spec or plan, the amendment is
carried into them too — or the appended section says why they do not change —
because the stages that build and check the work read those rather than the
request. For an item already in review, it goes into the rework notes that send
the item back, and into the spec as well.
