# Unreachable connected projects degrade instead of failing every command

A checkout that has only some of a project graph's repositories should still be
able to use TCW. Today it cannot use it at all: a `connected-projects` locator
naming a directory that is not present makes **every** command fail, including
ones that never needed the absent node.

The request came from wanting `tcw work` to function in a cloud coding session on
the `proposit-app` repository. Such a session clones one repository, into a
directory layout that is not the author's, and the orchestration repository that
`proposit-app`'s nodes name as their parent is simply not there.

What should be true when this is done:

- A locator whose target is not present here is treated as a fact about this
  machine, not as a configuration error. The node drops out of the graph and the
  commands that do not need it keep working.
- Configuration that is genuinely wrong still fails: a bad project id, a cycle, a
  duplicate id, unparseable YAML.
- `tcw validate` still reports the dropped edges, distinguishable from errors —
  declared, but not reachable in this checkout.
- A command that genuinely needs an absent node says which node and why, rather
  than reporting that the project has no such component or that there is no node
  here. This is the same courtesy `work.repository` already extends when a
  declared store is missing.
- Reciprocity is not disproved by a locator that is not present. Two nodes that
  each name the other at paths belonging to another machine are correctly
  configured; only a *reachable* counterpart pointing somewhere else is a real
  non-reciprocal declaration.

Out of scope: obtaining the absent node. Making a declared node fetchable is a
separate request ("Connected-project entries declare where they come from"), and
it depends on this one — it needs a graph that tolerates a node being absent
before it can put one there.

Also out of scope: the consumer-side configuration in `proposit-app` and
`proposit-orchestration` that this unblocks. That work belongs to those nodes.

## Notes

Asked for reference material; none provided beyond the session itself. The
request was developed against real checkouts rather than from description — the
reproductions, the prototype and its output are recorded in `intake.md`, and the
code they name is the material the spec should read.

No deadline. The requester's stated priority is that a cloud session can run
`tcw work` against `proposit-app` at all; this item is the first of the three
that gate it.
