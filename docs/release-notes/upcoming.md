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

In the local web app, the Initial Request tab now shows only the request. On an
item whose request has not been written, the tab says it is not yet present and
the editor opens blank — it no longer hands you the raw intake to edit under the
request's name, which would have copied it into the request the moment you saved.
The intake is still there to read, as its own document. When a save creates the
request, the confirmation says so.

## An epic's rollup lives in its own file

`tcw work reconcile` used to write its summary of an initiative's slices into the
epic's `initial-request.md`. That meant reconciling an epic created a request
document nobody had written — and the board then claimed the epic had been
written up when all that happened was that a command wrote a table.

The rollup now goes to `rollup.md` alongside the epic's other documents. The
command itself behaves the same — it still prints the rollup when you run it, and
`--commit` still commits it.

One thing to know: `tcw work show <epic>` no longer prints the rollup, because it
prints the epic's request and the rollup is no longer in it. To read a rollup,
run `tcw work reconcile <epic>` — it prints the current one, and changes nothing
if nothing has changed. `tcw work path <epic>` tells you where the file lives if
you would rather open it directly.

The local web app lists `rollup.md` and marks it generated. It offers no Edit
button for it, because `tcw work reconcile` writes that file and would discard
anything you typed there.

Epics you already have migrate themselves. The first time you reconcile one, the
rollup moves out of the request and into `rollup.md`, and anything you wrote
around it stays exactly where it was. If the rollup was the only thing in the
request, the empty file is removed rather than left behind.

## Nothing changes for items you already have

Every existing item has a request document, so it reads, displays, and shows on
the board exactly as before. Nothing is rewritten or backfilled — an item that
never had raw input does not get an invented one.
