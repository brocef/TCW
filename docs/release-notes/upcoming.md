# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## `tcw work new` no longer leaves a file to edit

This is the change you will notice first. Creating an item with
`tcw work new "Some title"` used to write a starter document with three empty
headings, and print its path for you to open. It no longer does: a brand-new item
has a title and nothing else.

That is deliberate. The starter document meant every item looked like its request
had already been written, so there was no way to tell an item somebody had
thought about from one somebody had merely named. Now the request document
appears when you write it, and the board can tell you which is which.

If you pipe text in — `echo "the thing is broken" | tcw work new "Fix the thing"` —
that text is kept, in a new file called `intake.md`.

## Raw input is kept as raw input

`intake.md` holds whatever the item started from, exactly as it arrived. Piped
text goes there. So does an accepted inbox entry: `tcw work inbox accept` now
records the entry's own words, a list of everything it preserved, and where it
came from, instead of wrapping them in a half-written request full of `TBD`.
Attachments, binary files, and everything else the command kept before, it still
keeps.

Nothing writes a request document on your behalf any more.

## The board says which items have been written up

`tcw work list` shows a lowercase `i` for an item that has raw intake, before the
`R` that marks a written request. So `i` means "someone dropped this on us",
`iR` means "and we've since written it up", and `R` alone is an item that came
straight in as a request. An item with neither shows `-`.

`R` used to appear on every item the moment it was created, which made it worth
nothing.

## Reading and editing an item's body

`tcw work show` displays the request when there is one and the raw intake
otherwise, so there is always something to read — and an item with neither shows
an empty body rather than failing.

Editing the body always writes the request, never the intake. On an item that has
only raw intake, editing the body creates its request for the first time and says
so. The intake is left exactly as it arrived; raw input that quietly changes
isn't raw input any more.

## Nothing changes for items you already have

Every existing item has a request document, so it reads, displays, and shows on
the board exactly as before. Nothing is rewritten or backfilled — an item that
never had raw input does not get an invented one.
