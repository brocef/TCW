# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## The `tcw` command now installs and updates itself

There is nothing to run after installing or updating the TCW plugin. When a
session starts, the plugin puts `tcw` on your PATH from its own copy of the
project, and when an update moves that copy it replaces the old install. The
stale `tcw` you used to be left with after a plugin update — until something
misbehaved and you thought to go looking — is gone.

Two things follow from that:

- **`/tcw-init` no longer exists.** It was the manual version of this, and
  nothing needs doing manually now. A brand-new install still takes effect at the
  *next* session, since the plugin can only act when a session starts — so start
  a fresh session after installing.
- **`/tcw-doctor` is still there.** The automatic install only handles "missing"
  and "out of date". Anything stranger — a second copy of `tcw` shadowing the
  first, a half-broken install, `tcw serve` refusing to start — is still its job.
  It also interrupts less than it used to: the steps it and the **`tcw-plugin`**
  skill run to find and reinstall `tcw` are approved up front, so it stops asking
  you to confirm each one.

Working on TCW itself from a checkout you installed with `pip install -e .`? That
is left alone on purpose: your development copy stays the one on your PATH, and
nothing installs over it. The same goes for a `tcw` that came from somewhere the
plugin cannot account for — a virtual environment, or a version manager such as
pyenv or asdf. It only ever replaces an ordinary install, and when it cannot tell,
it does nothing. A machine without `pipx` is left alone too, quietly —
picking a Python environment for you is not something that should happen unasked
while a session starts. If `tcw` is missing and nothing seems to be installing
it, that's the likely reason: ask for the **`tcw-plugin`** skill (or run
`/tcw-doctor`) and it walks you through the options.

If the automatic install ever fails, it says so at the start of the session and
points you at `/tcw-doctor` — or, in Codex, at the `tcw-plugin` skill — rather
than leaving you to find out later.

## Rename a work item from the command line

You can now change a work item's title after you create it:

```
tcw work edit <item> --title "A clearer title"
```

The item's ID stays the same, so anything already pointing at it keeps working —
only the name shown on the board changes. Until now the only way to fix a title
was through the web app.

The heading inside the item's own request document is yours to edit; renaming an
item leaves it alone.

## An interrupted save no longer leaves something half-written

If TCW is interrupted while saving — the disk fills up, a file cannot be written
because of a permissions problem — the work item, term, or capability it was
saving is now left exactly as it was, instead of half-saved. Before this, a save
that failed partway through could leave an item whose details had been updated
but whose request document had not, or leave a brand-new item behind as an empty
shell on the board.

One honest limit: a save writes its files one after another at the very end. If
that very last step fails, one file can land while another does not.
