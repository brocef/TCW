As a user, I run `tcw validate`, and as part of its checks it validates the taxonomy: taxonomy kinds, feature vocabulary refs, and every relatesTo and subject reference — flagging dangling refs and feature refs that do not point at vocabulary. Each problem is an `error: <where>: <message>` line on standard output, and any error makes `tcw validate` exit 1. There is no separate taxonomy check command.

It also flags a `config.yaml` left at the root of the taxonomy from before 2.5.0,
which is no longer read, saying that a project inherits taxonomy and
capabilities from its parents (`parents:` in `.tcw/tcw-config.yaml`) and telling
me to delete the file.

A term of my project's own that overrides nothing must be complete: a `name`
and a `description.md`, which may be empty. One that lacks either is an error
naming what is missing, which is how an override whose original was moved or
removed is caught. Each of my own terms, overrides included, is checked as my
project sees it, combined with what it inherits. Two parents that do not
inherit from each other, each with a term at one path, are a warning, until my
project gives that path a complete term of its own. When the inherited taxonomy
cannot be read, the checks that need it are one could-not-check finding, and
the rest still run. The checks of inheritance cycles and of a project ID
colliding with a top-level entry are gone.
