The project whose store holds an object's own declaration: the project ID in
the object's full identifier. Only the owning project changes or deletes the
object; a command or web route run in any other project refuses it, naming the
folder to run it in. Referring to an object is not changing it, so any project
may name another's object as a parent, a blocker or a link, and a project's
override of an inherited capability is that project's own object.
