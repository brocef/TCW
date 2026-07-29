# Make the reconcile rollup read the canonical capabilities.yaml schema

## Origin

GitHub issue [#8](https://github.com/brocef/TCW/issues/8), filed 2026-07-29 by
@brocef. Accepted during the first `tcw-triage-issues` sweep.

Reported against `tcw 0.16.0` on macOS 26.5.2, editable checkout.

> ### Steps to reproduce
>
> 1. On a work item with a product delta, author the `capabilities.yaml` sidecar
>    in the shape the `tcw-capabilities` skill documents as canonical:
>
>     ```yaml
>     new:
>         - proposit-shared/auth/deactivate-account
>     changed:
>         - proposit-shared/auth/delete-account
>     ```
>
> 2. Run `tcw capabilities check` — passes (`capabilities OK`).
> 3. Run `tcw work reconcile <epic-slug>` on the epic that item hangs off.
>
> ### Expected vs. actual
>
> - **Expected:** the rollup's **Capability deltas** section lists the declared
>   `new:` / `changed:` paths, since that is the schema the skill documents and
>   the completion gate enforces.
> - **Actual:** the rollup emits
>
>     ```
>     **Capability deltas:**
>     - <slug>: capabilities.yaml present but not a list — skipped
>     ```
>
> ### Cause
>
> Two readers, two schemas, same file.
>
> - `capability_gate` (`tcw/work/recursion.py:24`) → `declared_capabilities(item.capabilities)`
>   reads the `new:` / `changed:` mapping.
> - `_capability_deltas` (`tcw/work/recursion.py:89`), which builds the reconcile
>   rollup, instead does `if isinstance(caps, list)` over entries shaped
>   `{file, heading, from, to}` — an older schema — and falls through to the
>   "not a list" branch for anything else.
>
> So a sidecar authored per the documented schema, which the completion gate is
> happy with, always reports as malformed in the rollup. The `tcw-capabilities`
> skill even calls the mapping canonical, so following the docs is what triggers
> the warning.
>
> The tolerant `elif caps:` branch means nothing breaks — `complete` still gates
> correctly — but the message says the file is wrong when it is right, which
> sends you looking for a defect in your own sidecar. It cost me a detour through
> the tcw source to establish that closeout would not fail.
>
> ### Remediation
>
> Have `_capability_deltas` call `declared_capabilities()` like the gate does,
> and render the `new:` / `changed:` paths; keep the legacy
> `{file, heading, from, to}` list as a fallback branch if it is still in use
> anywhere. That leaves exactly one reader of the sidecar schema and makes the
> rollup agree with the gate.
>
> Axis: **work** (with a foot in capabilities — it is the work→capability
> sidecar).

## Notes

Cosmetic in effect but not in cost: the gate behaves correctly, so the only
damage is a false "your file is malformed" on a file that is not, which the
reporter says cost a source-reading detour to disprove. That is the argument for
fixing it rather than deferring it.

The `spec` stage should establish whether the legacy
`{file, heading, from, to}` list schema still has any live producer, since the
remediation's fallback branch is only worth keeping if it does.

This is TCW's own repo, so reporter and maintainer are the same person. The
quoted text is the report as filed.
