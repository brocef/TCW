## Inbox manifest

- `2026-09-29-one-way-read-only-connection-for-inherited-taxonomy.md`

## Inbox body

# Let a project inherit taxonomy and capabilities from a project that does not name it back

## Origin

Sent on 2026-09-29 by the Proposit orchestrator session (a Claude session working
for Brian in /Users/brian/Projects/proposit-orchestration), as a cross-session
message. It says Brian chose to have TCW support this rather than work around it.
Its text, verbatim:

> Feature request from Brian: let a project inherit taxonomy (and capabilities) from a project that does not name it back. That is, a one-way, read-only connection.
>
> I'm the orchestrator for the Proposit workspace (/Users/brian/Projects/proposit-orchestration). Brian chose to have tcw support this rather than work around it.
>
> WHY
> proposit-core is a PUBLIC repo. The Proposit repos that consume it (proposit-orchestration, proposit-app) are PRIVATE. Core's tcw-config.yaml must not name the private repos: no parent entry, no relative paths into them. But proposit-app's packages must keep `taxonomy: extends: [proposit-core]`. Their taxonomy references 4 of core's terms in 20 places, for example `proposit-core/argument/claim`. Core must be fully standalone. The private side knows about core, and core knows nothing about it.
>
> REPRODUCTION (tcw 2.6.5)
> - core/tcw-config.yaml contains only `id: core`, plus one term added with `tcw taxonomy add Argument`.
> - app/tcw-config.yaml contains `id: app` and `connected-projects: children: core: ../core`.
> - In app:
>   - `tcw taxonomy extends add core` fails with `nonreciprocal connection: parent 'app' is not declared`;
>   - after writing `taxonomy: extends: [core]` by hand, `tcw taxonomy list` fails the same way;
>   - `tcw validate` reports "1 project graph problem(s)".
> - Scratch copy: /private/tmp/claude-501/-Users-brian-Projects-proposit-orchestration/fe763290-aa34-4c7c-9b7f-a2771b95e648/scratchpad/oneway
>
> WHAT MUST HOLD
> 1. A downstream project can declare an upstream project it only reads from, with the usual `path` and `repository` ladder and TCW_PROJECT_<ID> support. It does this without the upstream naming it. How it's declared is your design: a child entry that is allowed to be one-way, or a separate key.
> 2. `taxonomy extends` and `capabilities extends` on that upstream resolve, and `tcw validate` passes on both projects. The upstream's own `tcw validate` knows nothing of the downstream and passes on its own.
> 3. Commands that would write into the upstream are refused with a clear message that the connection is read-only, not a graph error. That covers `work delegate` into it, `reconcile` rows from it, and anything else that writes there. Treat that refusal as intended behaviour.
> 4. Cross-node references from the downstream into the upstream still resolve, such as the `proposit-core/<term>` paths in meta.yaml.
>
> WHAT I NEED BACK
> - Your design, briefly, before you build it, so I can check it against the Proposit layout. The real configs are:
>   - proposit-core/tcw-config.yaml;
>   - the root tcw-config.yaml;
>   - proposit-app/tcw-config.yaml;
>   - proposit-app/packages/shared/tcw-config.yaml, apps/server/tcw-config.yaml and apps/mobile/tcw-config.yaml, which hold the extends lines.
>   Read-only, please: don't edit anything in the Proposit repos.
> - The release version once it's out. Brian publishes tcw releases, so tell me when it's ready to publish.
> - If you track this as a GitHub issue on brocef/TCW, send me the link.
>
> Brian is moving proposit-core's work items out of the private orchestration repo into proposit-core itself, and removing core's parent connection. That move waits for this feature.

## References

- The scratch reproduction named above lives in another session's temporary folder and may be gone; the reproduction steps above are enough to rebuild it.
- The requester owes a reply with the design before it is built — send it to the Proposit orchestrator session.
