# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Tell TCW where a project already is on your machine

If your repositories sit somewhere other than where their configuration says
they do, you can now say so with an environment variable instead of editing a
file that everyone else reads. Set `TCW_PROJECT_<ID>` — the project's ID,
uppercased, with hyphens as underscores — to the folder that holds it.

It takes priority over both the path in the configuration and the repository the
configuration says to fetch from. That matters most when the configured path is
not merely missing but points at the wrong place, which is the case that used to
make TCW download a second copy of a project you already had.

A variable naming a folder you do not have is not an error. It quietly falls
back to fetching, exactly as if you had set nothing. So one set of variables can
be set up once for a whole environment — a cloud session, a build runner — and
reused by sessions that have different repositories checked out. A variable
naming a folder that *is* there but holds the wrong thing is refused, and the
message says what it found instead.

`tcw validate` now prints a line for each variable in effect and where it points,
so a project graph that only works because of one is never a mystery to whoever
reads it next.
