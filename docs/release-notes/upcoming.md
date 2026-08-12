# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixed

When two agents start the same work item at the same moment, the one that loses
now always gets the plain message naming who claimed it and when. Before, a few
of the ways it could lose ended in an error dump instead — and one of them
answered "no such work item", which was worse, because the item was there all
along and someone else simply had it first.

Listing the board while another agent is claiming an item no longer fails.
`tcw work list` could crash if a claim landed in the instant between it checking
for an item's documents and reading them.
