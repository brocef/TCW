# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

### Your work items can live in another repository

If a project's work items and their lifecycle documents live somewhere other than
the project's own folder — an orchestrator repository, a shared planning repo —
you can now say so in a way that travels. Alongside the existing setting for
where the store sits on your machine, `tcw-config.yaml` can name the repository
it comes from: its address, optionally a branch or tag, where the store sits
inside it, and where you'd like a copy kept locally.

That matters most on a machine that has never seen the store. Cloud coding
sessions clone one repository, so until now a project set up this way arrived
with its whole board missing, and the tool said the project had no work items at
all — pointing you at a command that would have created a second, empty set
beside your real one. Now it tells you the store lives elsewhere, names the
repository, and tells you what to run.

`tcw provision` is what fetches it. Run it once in a new checkout and your board,
your specs and your plans are there. Run it again and it does nothing, because
nothing needs doing. It shows you which repository it is about to contact before
it contacts one, and it is the only command that goes to the network at all — so
merely checking out a project never reaches out on its own.

Nothing changes for a machine that already has the store: the local copy is
always preferred, so the same configuration works on your laptop and in a fresh
session without editing anything.
