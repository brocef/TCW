# Configure an external tracker and read its tickets

The first child of
`2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`. It
builds the foundation every later child stands on, and it ships something a user
can run on its own.

## What is being asked for

A project should be able to point TCW at its Jira Cloud site, and a developer
working in that project should be able to see the tickets assigned to them
without leaving the terminal.

Concretely, three things:

1. **Configuration.** A `work.tracker` block in the node's `tcw-config.yaml`
   naming the site, the candidate query, the environment variables holding the
   credentials, and the workflow transitions that matter. Credentials are read
   from named environment variables and never written into the repository.
2. **A Jira Cloud client.** Enough of the REST surface to resolve who the
   credentials authenticate as, run the configured query, fetch one ticket, and
   discover a project's workflow transitions. It must tell apart the reasons a
   call failed rather than reporting one generic error, because every later child
   depends on distinguishing "your token is wrong" from "the ticket moved".
3. **Two read-only commands.** `tcw work tracker list` and
   `tcw work tracker show <ticket>`. Neither changes anything, locally or
   remotely.

## Why this is its own item

It is the only piece with no dependency on anything else in the initiative, and
it is separately useful. The honest reason the two read commands are in scope is
that they are the harness that exercises the configuration, the client and the
error handling before any claiming code exists. Terminal access to Jira is not
itself scarce. A child that completes with nothing runnable cannot be verified by
anyone but its author.

## The workflow check, and why it is here

The epic's claim experiment (`jira-claim-experiment.md`, 2026-09-12) found that a
Jira workflow transition only excludes a second claimant if the transition is
unreachable from the state it lands in, and that Jira's default workflow does not
have that shape. Whether a given project's workflow can support a claim at all is
therefore a **configuration** question, and configuration is this item's subject.

So this item also answers it: read the transitions available from the state the
configured claim transition lands in, and if the claim transition is itself among
them, say so and refuse the strict mode. Decided 2026-09-12 in preference to
contending on the assignee, which Jira cannot make atomic, and in preference to
dropping the guarantee.

This item does **not** claim anything. It reports whether claiming could work.

## Constraints

- **No new runtime dependency.** TCW ships with PyYAML and nothing else, and that
  does not change for this. The client uses the standard library.
- **Every request carries an explicit timeout.** The default is to block forever,
  which would hang the CLI against a server that accepts a connection and never
  answers.
- **A project with no tracker configured behaves exactly as it does today.** No
  output changes, no new failure, no new required configuration.
- **No secret reaches a tracked file, a sidecar, or any output stream.**
- Both harnesses matter. Anything guaranteed here lives in the `tcw` CLI, which
  behaves the same under Claude and Codex.

## Out of scope

Claiming, importing, the `tracker.yaml` binding, `link`, `unlink`, outbound
lifecycle synchronization, `sync`, the strict mode's gates on `work new` and
`work start`, and anything in the JSON projection or the web app. Those are the
four later children. Jira Data Center, OAuth, and any provider other than Jira
Cloud are out of scope for the whole initiative.

## References

Asked; none provided, and that is deliberate rather than an omission. The
requester's answer on 2026-09-12 was to work from the code and the Atlassian
documentation. The starting set for `spec` is therefore:

- `jira-claim-experiment.md` in the epic's folder — the measured behavior the
  workflow check exists because of, with verbatim responses.
- The epic's `spec.md`, section C1 — the boundary this item was given.
- `https://developer.atlassian.com/cloud/jira/platform/rest/v3/` — the REST
  surface the client is written against.
- `~/.claude/bin/jira` — a working wrapper for the Proposit site, useful as a
  reference for authentication and as a way to check behavior by hand.
- The `TCWTEST` project on the Proposit site — a throwaway fixture created for
  this initiative, safe to reconfigure.

## Notes

The requester chose to work from the code and Atlassian's documentation rather
than supply reference material, so `spec` should research from scratch and not
read the short reference list above as a limit.

The realistic target configuration is a clean fixture, not the existing Proposit
project. `TCWTEST` is the one to design against.
