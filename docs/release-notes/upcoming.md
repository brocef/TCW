# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## If you use a provisioned work store, your transitions now push

**Read this one before you upgrade.** If your project's work items live in
another repository and you fetched them with `tcw provision`, then starting,
submitting or completing an item now talks to that repository: it brings your
copy up to date first, and pushes the result afterwards.

This is the point of the feature — work done in a cloud session or a container
used to vanish with the machine — but it is a change to what a routine command
does, so it should not be a surprise. To turn it off, put
`publish-transitions: false` under `work:` in your config.

Nothing changes if your work store is simply a folder on your own disk. Only a
store TCW fetched for you publishes; one you already had is yours to push, and a
project with no declared repository never touches a network at all.

If the repository cannot be reached, what happens depends on when it fails. If
the update at the start fails, nothing moves and the command stops — your item is
exactly as it was. If the push at the end fails, the item has already moved and
been saved locally, and the message tells you where it is saved and what to run
when the remote is back. If someone else changed the same store in a way that
conflicts, you are told; nothing is merged on your behalf.

## Your taxonomy and capabilities can live elsewhere too

Work items could already live in another folder, or another repository, and be
fetched into a fresh checkout. Now the other two trees can as well.

You can keep a project's taxonomy or capabilities anywhere you like by naming the
location in the project's config, and scaffold one there directly when you set
the project up. Or name the repository it comes from, and run one command to
fetch it — the same command, and the same rules, as for work items: a tree
already on your machine is always preferred, nothing reaches the network unless
you ask, and you are told which repository is about to be contacted before it is.

This fixes a confusing answer along the way. A checkout that cloned only your
code has no taxonomy folder in it, and TCW used to take that to mean the project
had no taxonomy at all — and suggested setting one up, which would have created a
second, empty one beside the real one. It now reads the config, sees where the
tree comes from, and tells you the command that fetches it.

One difference worth knowing: TCW can recognize a work store by its layout, so it
refuses a repository that does not actually hold one. A taxonomy or capabilities
tree is just a folder of entries with nothing to recognize, so all TCW can check
is that the folder is there. A failure still never leaves a half-fetched copy
behind.
