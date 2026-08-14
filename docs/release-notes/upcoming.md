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

## Writing your own instructions for a lifecycle stage

Until now, telling TCW what should happen at a stage meant naming an agent skill
— and a skill name is not instructions, it is the name of something that has
them. If your project does not ship a plugin, there was nowhere to put your own
words.

Now there is. In `tcw-config.yaml`, a stage can carry instructions written inline,
read from a file in your project, or produced by a script you own:

```yaml
work:
    lifecycle:
        stages:
            spec:
                prompt:
                    - builtin: true
                    - blob: "In this repo, specs name their rejected options."
                    - file: docs/spec-guide.md
```

`builtin: true` means "TCW's own default", so you can add to it rather than
replace it. A `generate:` script receives the work item as JSON on its standard
input and prints whatever it likes — useful when the instructions depend on
something only your project knows.

You can also give a stage a **check** that has to pass before the work begins,
under `pre:`, and give each lifecycle document a **template** under `artifacts:`.

## Asking TCW what to do at a stage

`tcw work stage spec my-item` prints the instructions for writing that item's
spec — TCW's own by default, yours if you have configured them. It is the command
that makes everything above reachable.

It checks first that the stage makes sense for where the item is: asking for
`implement` on something still in the backlog is refused, and so is asking about
a spec for work that is already closed. Then it runs whatever `pre` checks you
configured, and prints the result.

The instructions go to standard output on their own, so you can pipe them
anywhere. Everything else — your checks' output, any error — goes to the error
stream, and if anything fails you get *nothing* on standard output rather than
half an instruction.

**It changes nothing.** No document is written, no draft appears, the item does
not move. Running it just to find out what to do is safe, which is rather the
point.

`--no-exec` goes further and runs nothing at all — not your checks, not your
scripts — printing what it *would* have run instead. Use it to read an
unfamiliar project's lifecycle before you trigger any of it.

## Instructions that depend on the item

Any of these can carry a condition, so a bug is treated differently from a
feature:

```yaml
prompt:
    - blob: "Start with the reproduction steps."
      when: { tags: [bug] }
```

`tags:` matches any of the listed tags, `not_tags:` excludes, and `type:`
distinguishes an epic from an ordinary item. Three ways to say when — anything
more complicated is what a `generate:` script is for, since it is real code and
can decide anything.

## Everything you have configured already keeps working

This is the change most likely to worry you, so: no. A stage id with a plain list
of skills or commands under it means exactly what it always meant, and prints
exactly what it always printed. That is checked against recordings of the old
behaviour, including this project's own configuration.

## Scripts that misbehave now fail instead of leaking

A `generate:` script that exits with an error contributes **nothing** — not the
half a prompt it printed before it died. One that runs too long, or prints more
than 64 KiB, fails with a message saying which limit it hit rather than quietly
handing you a truncated instruction. And `tcw work lifecycle` still runs nothing
at all; it only ever tells you what is configured.

## Reading a work item as JSON

`tcw work show <slug> --json` prints the item as a machine-readable document
instead of the human-readable summary — so you can pipe a work item into `jq`, or
into a script of your own.

The document says what version it is (`"schema": 1`), carries every field of the
item under its own name, and includes a map of which lifecycle documents exist,
so a script can ask "has the spec been written?" without looking at files. If
something goes wrong, the error goes to the error stream and nothing is printed,
so a pipeline fails cleanly instead of receiving half a document.

It is the same document the local web app's API returns. That is the point: there
was one shape for the web app and none for the command line, and now there is one
shape for both.

One small change if you keep unusual values in a work item's `capabilities`
block: a YAML set used to appear as text like `"{1, 2}"` and now appears as a
proper list, `[1, 2]`. Dates, binary values, and deeply linked structures are all
handled properly now rather than being stringified on the way out.

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
