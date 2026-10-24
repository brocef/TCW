As a user, I get my project's ancestors read in one order, the load order,
which ends with my project: TCW computes it from every project's own order of
parents by C3, the method Python uses for classes, so that a later parent wins
over an earlier one and each project's own order is kept. When no order can
keep every project's own order, TCW uses the depth-first order instead and
warns, naming the project where the orders disagree; the warning is a
`tcw validate` warning at `.tcw/tcw-config.yaml` and the `load-order-warning`
of `tcw projects list --json`, and no other command prints it. A loop of
parents is an error that stops every command.

An ancestor that is not on this machine, or whose parents cannot be read,
keeps its place in the order, and `load-order-complete` is false. It stops
only a command that needs what it passes down: such a command exits 7, naming
the project and how to fetch it, and `tcw validate` reports it as could not
be checked. A project that passes nothing a command needs may be missing.
