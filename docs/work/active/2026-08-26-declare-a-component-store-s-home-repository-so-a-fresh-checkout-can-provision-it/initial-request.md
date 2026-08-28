# Declare a component store's home repository so a fresh checkout can provision it

## The request

Let a project declare **another repository** — not just another local path — as
the home of its TCW component stores: its work items and their lifecycle
artifacts first, and its taxonomy and capabilities trees as well.

One of my projects keeps its work items inside a separate orchestrator folder on
my machine, and points at it from `tcw-config.yaml`. That works on my laptop,
where both folders exist side by side. It does not survive a cloud session: when
I start Claude Code on the web it clones **only** the project repository, the
orchestrator folder is not there, and every work item and lifecycle artifact for
that project is missing. The agent starts blind, with no board, no specs, and no
plans.

A path is a fact about my laptop. What I want to record instead is something
portable — where the store actually lives, in terms any fresh checkout on any
machine can act on.

## Coordination goal

This is the initiative item. Collectively its children should make a project's
component stores reachable from a machine that has never seen them, by:

1. letting the config name the store's home repository in a portable way, and
   giving the CLI an explicit command that materializes it;
2. extending that from the work store to any component tree (taxonomy and
   capabilities too); and
3. keeping a provisioned store in step with its remote around writes, so work
   done in an ephemeral environment is not stranded when the container is
   reclaimed.

Child 1 alone should be enough to unblock the cloud sessions that prompted this.

## Constraints

- **Declaration and provisioning are separate.** The config declares; an
  explicit command (a `provision`-shaped verb) is what clones or fetches.
  Commands that find the store missing should fail with an actionable error that
  names that command, rather than reaching for the network on their own.
- **The CLI has to carry it.** A SessionStart hook may call the command, but it
  must not be the only thing that does — a Codex user gets no hooks and must be
  able to finish the same job.
- **Where the clone lands is configurable, with a sane default.** The
  declaration may carry a local path; absent one, TCW picks a per-machine cache
  location and resolves the store there.
- **Writes should stay in step with the remote.** A provisioned store should
  pull before and push after transitions, so a cloud session's work outlives the
  session. This is new territory: TCW performs no network writes today.
- Existing local `work.path` setups must keep working untouched — a path is
  still a valid way to name a store.

## Out of scope

- Replacing the filesystem store with a remote tracker. That is a different
  thing, tracked separately in
  [Supplement filesystem TCW work with an external tracker bridge](tcw://W/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge)
  and [Full external TCW store adapters](tcw://W/2026-06-19-remote-adapter-jiraworkstore).
  Here the store is still a folder in a Git repository; only *which* repository,
  and how it gets there, is new.
- Materializing a whole registered node (an orchestrator project as a connected
  project) rather than its component stores. Considered and set aside; it may be
  the right eventual shape, but it is not what this initiative buys.

## Notes

- Requester's environment is Claude Code on the web, where the session clones a
  single repository and any second repository has to be attached deliberately.
  The design should assume the store's repository may be unreachable and say so
  clearly, not fail obscurely.
- The following were decided with the requester at intake, and are constraints
  rather than inferences: explicit provision command over implicit
  auto-materialization; configurable clone target defaulting to a cache
  directory; pull-before/push-after around writes; and scope covering all three
  component trees rather than the work store alone.
- The requester chose to track this as an epic with independently shippable
  children rather than one long-running item.

## References

Asked; none provided — the requester's answer was that the code is enough. The
`spec` stage should work from what is already in this repository:
`work.path` resolution in `FsWorkStore.open` (`tcw/store/fs.py`), the connected-
projects registry (`tcw/store/project.py`), and `scripts/remote_session_setup.sh`
as the existing example of a session provisioning itself.
