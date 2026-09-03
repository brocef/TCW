Raw request, from a working session on 2026-09-03.

> I need to figure out a way to get TCW work to be functional in cloud
> environments for the proposit-app repo. Claude in the cloud will clone just the
> app repo and not the orchestration repo nor will it have the same relative
> folder structure so all the work artifacts cannot be found. What can we do
> about that?

Reproduced in a cloud checkout of `proposit-app`, in `apps/server`:

    $ tcw work list
    tcw: /home/user/tcw-config.yaml: registered target has no tcw-config.yaml

The node declares `connected-projects.parent: proposit-app: ../../..`, which is
the orchestration repo — present on the author's machine because `proposit-app`
sits inside it there, and absent in any checkout that cloned only the code. Every
command fails, because `find_node` calls `FsProjectRegistry.open(nr).require_valid()`
and an unreadable locator is a graph problem.

The blast radius is wider than the work store. With the parent gone there is no
route between sibling nodes either, so `extends` cannot resolve a sibling that is
physically present in the same checkout:

    $ tcw validate            # full proposit-app monorepo checked out
    taxonomy check: .../apps/server/docs/taxonomy/config.yaml: extends project
      'proposit-shared' is not reachable through connected-projects
    capabilities check: ... same
    (plus 7 tcw://C/... capability references failing for the same reason)

`packages/shared/tcw-config.yaml` is right there. The two packages simply have no
edge between them: each declares only its parent, so the route from one to the
other goes up to the orchestration node and back down.

The shape agreed in session: a locator whose target has no `tcw-config.yaml` is a
fact about one machine, exactly as `work.path` is. It should drop out of the
graph rather than fail; malformed configuration (bad id, cycle, duplicate id)
stays a hard error; `tcw validate` reports the dropped edges as declared but not
reachable in this checkout; and a command that genuinely needs the absent node
says so by name.

A second half surfaced while prototyping: an unreachable locator must not be able
to disprove reciprocity. Pointing a parent at a provisioned checkout currently
fails with

    child locator for 'proposit-server' does not point back to <path>

because the parent names its children at paths that exist only on the author's
machine. If the counterpart path is not here and the ids match, that is a machine
fact, not a configuration error.

Prototyped in-session as a monkeypatch over `_read_config` and `_problem`. With
both halves, `tcw work list` and `tcw work nodes` work in the cloud checkout.
