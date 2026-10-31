As a user, I change a work item, a term or a capability only from the project
that owns it. Every command and web route that changes or deletes an object
refuses one that another project owns (exit 3, and on the web `403`), writes
nothing, and names the folder to run the command in instead, or says that the
owning project is not on this machine. The rule has one answer whatever the
projects' relation: a parent's object, a child's and an unconnected project's
are refused alike.

A reference to another project's object is still allowed, because it belongs
to the record that holds it: an item of mine may name a parent or a blocker in
any project TCW can locate, and a document of mine may link to anything.
Overriding an inherited capability is allowed too, since the override is my
project's own capability at the same path
([Override an inherited capability](tcw://C/capabilities/override-inherited)).

A new object is always made in the active project's own store. To make one in
another project I run the command there, usually with
[`tcw -C`](tcw://C/cli/run-a-command-as-if-started-in-another-folder).
