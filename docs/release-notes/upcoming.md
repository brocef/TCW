# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

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
