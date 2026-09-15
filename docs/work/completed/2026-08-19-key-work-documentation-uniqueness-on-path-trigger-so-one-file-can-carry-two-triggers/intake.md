# Key work.documentation uniqueness on (path, trigger) so one file can carry two triggers

## Origin

GitHub issue [#21](https://github.com/brocef/TCW/issues/21), filed 2026-08-19 by
@brocef. Accepted during a `tcw-triage-issues` sweep.

## Inbox body

The reporter's text, verbatim:

> ### Motivation
>
> Migrating a `## Documentation Sync` section to `work.documentation` (as the 1.0.0 migration guide recommends), one shape did not survive: two entries on the same file with different triggers.
>
> `proposit-core` has carried this pair for months:
>
> ```markdown
> - `README.md` [Public-CLI-API] — Concepts, usage examples, and CLI sections
> - `README.md` "Invalid Constructions" section [Validation-Rules] — Update when adding, removing, or changing validation rules, thrown errors, error codes, operator constraints, cascade behaviors, or grammar config options
> ```
>
> Two genuinely different triggers on one file. A CLI-surface change fires the first; a validation-rule change that touches no CLI surface fires only the second. In the config form that is rejected:
>
> ```
> work check: tcw-config.yaml: work.documentation entry 1: duplicate 'path' 'README.md', already declared by entry 0
> ```
>
> So the config form — the recommended one — is strictly less expressive than the Markdown fallback it is meant to replace, for any file large enough that different sections answer to different triggers. That is common for a README.
>
> ### Description
>
> Either allow duplicate `path` when the `trigger` differs (uniqueness on the `(path, trigger)` pair rather than on `path` alone), or add an optional `section:` key that qualifies an entry within a file and participates in the uniqueness check.
>
> The `(path, trigger)` pair seems like the smaller change and reads naturally in `tcw work docs` output, which already prints the trigger next to the path.
>
> ### Workaround in use
>
> We disambiguated with an anchored path:
>
> ```yaml
> - path: README.md
>   trigger: Public-CLI-API
>   description: Concepts, usage examples, and CLI sections.
> - path: README.md#invalid-constructions
>   trigger: Validation-Rules
>   description: The "Invalid Constructions" section of `README.md`.
> ```
>
> It validates and prints fine, but it names a path that does not exist on disk, so anything that later resolves an entry's `path` against the filesystem would be misled by it.
>
> ### Benefits
>
> Lets a project move to the recommended config form without losing trigger granularity, and removes a reason to stay on the Markdown fallback. Axis: work.
>
