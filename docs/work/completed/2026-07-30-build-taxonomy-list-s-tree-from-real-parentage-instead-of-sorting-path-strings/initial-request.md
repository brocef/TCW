# Build taxonomy list's tree from real parentage instead of sorting path strings

## Origin

GitHub issue [#11](https://github.com/brocef/TCW/issues/11), filed 2026-07-30 by
@brocef. Accepted during the second `tcw-triage-issues` sweep.

Reported against `tcw 0.17.2` on macOS 26.5.2 (darwin), Python 3.14.6, editable
install from a local clone.

> ### Steps to reproduce
>
> In a fresh git repo:
>
> ```bash
> tcw init taxonomy --id repro
> printf '%s' "a root term with children" | tcw taxonomy add "Event"
> printf '%s' "child of event"            | tcw taxonomy add "Log Batch" --parent event
> printf '%s' "child of event"            | tcw taxonomy add "Stat"      --parent event
> printf '%s' "an unrelated ROOT feature" | tcw taxonomy add "Event Reporting" --kind feature --vocab event
> tcw taxonomy list
> ```
>
> ### Expected vs. actual
>
> - **Expected:** `event-reporting` is a root entry with no children; `log-batch`
>   and `stat` render as children of `event`.
> - **Actual:**
>
>   ```
>   event  [V] (local)
>   event-reporting  [F] (local)
>     log-batch  [V] (local)
>     stat  [V] (local)
>   ```
>
>   This reads as though `log-batch` and `stat` belong to `event-reporting`. They
>   do not — the on-disk tree is unambiguous:
>
>   ```
>   docs/taxonomy/event-reporting/meta.yaml
>   docs/taxonomy/event/log-batch/meta.yaml
>   docs/taxonomy/event/meta.yaml
>   docs/taxonomy/event/stat/meta.yaml
>   ```
>
>   and `tcw taxonomy show event/log-batch` confirms the real parent.
>
> ### Impact
>
> The data is correct, so **`tcw taxonomy check` and `tcw validate` both report
> OK** — nothing flags it. `list` is the primary way a human or an agent reads
> the tree back, so a wrong parent here is believed. It is also the review
> surface for exactly the operation most likely to create the collision: a
> taxonomy where a Feature is named after the Vocabulary it operates on
> (`Event` / `Event Reporting`, `Watermark` / `Watermarking`, `Category` /
> `Category Sync`), which `references/init.md` actively encourages by having
> Features name the interaction area over a term. I hit it seeding a real
> taxonomy and had to go to disk to convince myself the tree was right.
>
> ### Remediation
>
> The sort is lexicographic over full path strings, and `-` (0x2D) sorts before
> `/` (0x2F) — so any root slug that is a hyphen-extension of another root slug
> lands *between* that root and its children, inheriting their indentation. Fix
> by building the actual parent/child tree and sorting siblings within each level
> (or sorting on the tuple of path segments rather than the joined string), so
> ordering can never interleave a subtree with an unrelated sibling.
>
> Axis: taxonomy.

## Notes

Confirmed still present at HEAD (0.17.3), not only the reported 0.17.2:
`tcw/taxonomy/cli.py:56` sorts on `(t.origin != "local", t.qualified)` — the
joined path string — while line 57 derives indentation independently from
`t.slug.count("/")`. The two disagree exactly as the reporter diagnosed.

Two things the `request` stage should settle that the report does not:

- Whether inherited terms (the `origin != "local"` half of the sort key) group
  as their own block or interleave, once ordering becomes per-level rather than
  global. The current key sorts all local terms before all inherited ones; a
  real tree walk has to decide that deliberately.
- Whether anything besides `list` renders a tree from the same flat, sorted
  `list_all()` output — the web editor, and any skill that parses `list`, would
  inherit the same defect.

This is TCW's own repo, so reporter and maintainer are the same person. The
quoted text is the report as filed, unedited.
