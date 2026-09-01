# Make tcw validate usable as a gate: suppressible references and graded exit codes

## Origin

GitHub issue [#25](https://github.com/brocef/TCW/issues/25), filed 2026-08-28
by @brocef. The issue's headline ask — a markdown-link parser fix — was
**declined during triage**; only the two secondary asks below were accepted.

The reporter's words for the two accepted asks, verbatim:

> Two things that would help independently of the parser, and would have helped us here:
>
> 1. **A way to record a knowingly-unresolvable reference.** Some of our 17 genuine dangles point at items that never existed in this store and never will — history imported from a pre-TCW tracker. Today there is no way to say so, so they are permanent failures. A `--no-recurse`-style suppression, or honouring a marker in the file, would let a clean run mean something again.
> 2. **Separate exit codes or a `--strict` flag**, so "dangling cross-reference" and "malformed item" do not both simply exit 1. We wanted to run `tcw validate` after a large backlog cleanup to prove we had broken nothing, and could not, because the baseline was already 25.

And the motivation the reporter gave, which survives the declined parser ask:

> Because the 8 never go away and cannot be fixed without rewriting valid links into a worse form, `tcw validate`'s exit code is useless to us, and a *newly introduced* dangling link — the case the check exists to catch — is invisible in the standing noise. That is the real cost: the check is not just noisy, it is unable to signal.

## Why the parser ask was declined

Reproduced against tcw 1.2.0 in the reporter's own workspace — a federated root
with four registered children, 25 problems. Three reference forms were placed in
one file inside a **child** node's store:

| form | result |
| --- | --- |
| `[x](tcw://W/<root-id>/<slug>)` — markdown link, project-qualified | resolves |
| `[y](tcw://W/<slug>)` — markdown link, bare slug | reported missing |
| `bare tcw://W/no-such-slug-zz` — not a link, slug absent | never checked |

Markdown-link parsing is correct. `_LINK_RE` (`tcw/validate.py:27`) matches
**only** `](tcw://…)` and is unchanged since `tcw validate` was introduced, so
bare `tcw://` URLs have never been scanned — the issue's "the bare form
resolves" observation is really "the bare form is not checked."

The 8 reported false negatives are genuine dangling references: each is written
bare from a *child* node but names an item that lives in the **root** node's
store, and a bare slug resolves against the anchor node
(`tcw/store/fs.py:313`). Qualifying them as `tcw://W/<root-id>/<slug>` fixes
them in the reporter's store with no TCW change. Classifying all 25 problem
lines by whether the target exists elsewhere in the workspace reproduces the
reporter's own split exactly: **8 fixable by qualifying, 17 genuinely absent.**

The 17 are what this item is for.

## Scope

1. A way to record a knowingly-unresolvable reference, so a clean run means
   something again. Shape to be decided at spec — a suppression flag, or a
   marker honoured in the file.
2. Distinguish a dangling cross-reference from a malformed item in the exit
   status, so `tcw validate` can gate a change rather than only report.

Whether bare and reference-style `tcw://` references should also be scanned is
**deliberately out of scope**: widening the scan finds more dangles, not fewer,
and would make the reporter's baseline worse rather than better. That is its own
question.
