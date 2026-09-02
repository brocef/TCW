# Resolve a cross-node external: blocker against the node that owns it

## Origin

GitHub issue [#28](https://github.com/brocef/TCW/issues/28), filed 2026-09-02
by @brocef, against tcw 1.2.2.

> ### Steps to reproduce
>
> `tcw work delegate` / `escalate` record a cross-node dependency as an opaque string under `blocked_by`:
>
> ```yaml
> blocked_by:
> - external: proposit-shared/2026-08-18-federate-xor-through-the-shared-layer
> ```
>
> 1. Complete the referenced item (`proposit-shared/<slug>`).
> 2. Try to start the dependent: `tcw work start <dependent>` still refuses.
> 3. Roll up the epic: `tcw work reconcile <epic>` prints **"Next: all blocked or complete"**.
>
> ### Expected vs. actual
>
> - **Expected:** an `external:` entry that names a real `<node>/<slug>` is recognised as a reference, and clears — or is at least reported as satisfied — once that item completes. Failing that, `reconcile` should distinguish "blocked on something already done" from "genuinely blocked".
> - **Actual:** the string is never resolved, so completing the referent changes nothing. The dependent stays gated and must be cleared by hand:
>
> ```
> tcw work edit <dependent> --unblocked-by "external: <node>/<slug>"
> ```
>
> quoted exactly as `show`/`list` prints it, `external: ` prefix included. `tcw work start --force` is not a substitute: it waives *every* gate, including unrelated blockers and the inactive-epic check.
>
> The reconcile line is the expensive part. **"Next: all blocked or complete" reads as "this epic is finished"** when in fact its next slice is gated on work that is already done. On a three-slice cross-node epic here, every hand-off needed the manual edit, and one rollup was read as complete when it was not.
>
> A caveat on evidence: the only stale entry of this shape currently in my store
> sits on a *superseded* item, and a completed or superseded item is expected to
> carry references that have since gone stale — that is history, not a defect. So
> treat it as illustrative of the mechanism only, not as a bug in its own right:
>
> ```
> blocked_by:
> - external: proposit-server/2026-08-22-convert-the-server-shell-to-tamagui-and-retire-the-mui-theme   # completed 2026-08-22
> ```
>
> The real cost is on **active** work, and it is the three-hand-off epic described
> above rather than any stale row: each dependent had to be unblocked by hand after
> its predecessor completed, and one rollup was read as finished when its next
> slice was gated on work already done. Any fix should likewise only concern itself
> with items still in `backlog/` or `active/`.
>
> ### Remediation
>
> The field is currently free text and legitimately so — some blockers are genuinely external and unresolvable, e.g.:
>
> ```yaml
> blocked_by:
> - external: 'Play Console app-signing SHA-256 fingerprint — gates only the fingerprint
>     VALUE in assetlinks.json. The route and the intent filters can be built now
>     against an env-supplied value.'
> ```
>
> So the fix probably is not to make `external:` resolvable, but to separate the two cases. Options, roughly in order of preference:
>
> 1. A distinct blocker kind for an in-TCW cross-node reference (`blocked_by: - work: <node>/<slug>`), which `start`, `list` and `reconcile` resolve, leaving `external:` for genuinely outside dependencies. `delegate`/`escalate` would emit the new kind.
> 2. Keep `external:` but resolve any value matching `<node>/<slug>`, and report it as satisfied once complete.
> 3. At minimum, have `reconcile` check whether a blocker string names a completed item and say so, so "all blocked or complete" stops being ambiguous.

## Earlier note from the same reporter

Filed on 2026-08-25 as `docs/work/inbox/2026-08-25-an-external-blocker-never-clears-even-when-its-target-is-completed.md`
and folded in here during triage of issue #28 — the same defect, written up from
the code side. Quoted verbatim; the inbox entry was removed in the same commit.

> # An `external:` blocker never clears, even when its target is completed
>
> ## Origin
>
> Hit while driving a multi-node epic to completion in `proposit-orchestration`
> (root node plus four child nodes) on 2026-08-25, running the installed plugin at
> **1.0.2**. The code below is quoted from the repo at **1.0.3**, where it is
> unchanged.
>
> ## Problem
>
> `tcw work start` refuses an item whose only blocker is an `external:` reference to
> an item that is **`completed`**. The blocker can never be satisfied by finishing
> the work it names; the only ways forward are `--force` or editing the blocker away.
>
> Observed sequence:
>
> ```
> $ tcw work complete proposit-mobile/2026-08-22-convert-the-mobile-shell-to-tamagui-…
> completed proposit-mobile/2026-08-22-convert-the-mobile-shell-to-tamagui-… (done)
>
> $ tcw work start 2026-08-22-capability-and-parity-audit-after-the-tamagui-conversion
> tcw work: blocked by: external: proposit-mobile/2026-08-22-convert-the-mobile-shell-to-tamagui-…
>           (use --force to override)
> ```
>
> `store/base.py::unresolved_blockers` (1883–1907) reports every external entry as
> unresolved, without looking at it:
>
> ```python
> for b in item.blocked_by:
>     if "external" in b:
>         out.append(f"external: {b['external']}")     # ← unconditional
>     elif "slug" in b:
>         ... # resolves the item and honours RESOLVED_STATUSES
> ```
>
> The docstring says so outright — *"An entry is unresolved if it is external, or a
> slug whose item is not resolved"* — so this reads as deliberate: the store cannot
> resolve a reference into another node, so it assumes the worst.
>
> `work/recursion.py::_ready` (138) makes the same assumption independently:
>
> ```python
> blocked = any(b.get("slug") in unresolved or "external" in b for b in item.blocked_by)
> ```
>
> ## Why it is worth changing
>
> **The rollup already resolves cross-node references, so the two disagree about the
> same fact in the same output.** `tcw work reconcile` printed the blocker's target
> as `completed`, in a table it built by walking the connected nodes — and the row
> directly above it showed the dependent item as `backlog | blocked-by: external: …`:
>
> ```
> | . | …capability-and-parity-audit… | backlog | external: proposit-mobile/…convert-the-mobile-shell… |
> | proposit-mobile | …convert-the-mobile-shell… | completed | - |
> ```
>
> So the machinery to answer the question exists and is being used a few lines away;
> `unresolved_blockers` just does not use it. If the reconcile walk can see that the
> target is resolved, the blocker check should be able to.
>
> **The workaround teaches the wrong thing.** `--force` is the obvious escape, and it
> records "started despite an unmet dependency" when the dependency was in fact met.
> I used `tcw work edit --unblocked-by "external: …"` instead so that the history
> says the blocker was satisfied rather than overridden — but that permanently
> deletes the edge, so the item no longer records what it waited on. Neither option
> leaves an accurate record, which is the thing a work tracker is for.
>
> This bites hardest exactly where cross-node blockers are most useful: a multi-node
> epic whose slices hand off between nodes in a fixed order. Every hand-off needs a
> manual intervention.
>
> ## Shape
>
> The narrow fix is to resolve the external reference the way `reconcile` does before
> declaring it unresolved, and fall back to "blocked" only when the reference cannot
> be resolved from where the command runs — which is the honest version of the
> current assumption, and keeps the behaviour unchanged for a genuinely
> unreachable node.
>
> Both call sites need it: `store/base.py::unresolved_blockers` gates
> `start`/`complete`, and `work/recursion.py::_ready` computes the rollup's **Next**
> line, which today can name an item that `start` will then refuse.
>
> Worth deciding explicitly: whether an unreachable external reference should block
> (today's behaviour, safe but sticky) or warn and proceed. A third option is to let
> it block but say *why* — "cannot resolve `proposit-mobile/…` from this node" is a
> much better message than "blocked by", because it tells the reader the problem is
> their vantage point rather than their sequencing.
>
> ## Repro
>
> Two registered nodes, A and B.
>
> 1. In B: `tcw work new "thing"`.
> 2. In A: `tcw work new "dependent" --blocked-by "external: B/<thing-slug>"`.
> 3. In B: `tcw work start <thing-slug>` then
>    `tcw work complete <thing-slug> --resolution done --confirm`.
> 4. In A: `tcw work start <dependent-slug>` → refuses, naming the completed item.
>
> Step 4 is the bug; steps 1–3 are the ordinary hand-off it is meant to support.

## Triage notes

Confirmed against the working tree at 1.2.3 — all three call sites the two
reports name are unchanged:

- `tcw/store/base.py:2177-2178` — `unresolved_blockers` appends every `external:`
  entry unconditionally, without looking at what it names. Gates `start` and
  `complete`.
- `tcw/work/recursion.py:138` — `_ready` repeats the same assumption
  independently (`... or "external" in b`).
- `tcw/work/recursion.py:166` — the rollup's `**Next:** all blocked or complete`,
  which is the line that reads as "finished".

Note also `tcw/store/base.py:2079`: a blocker ref becomes `{"slug": ...}` only if
it resolves in the local store, else `{"external": ...}` — which is why a
cross-node reference is recorded as `external:` in the first place. Option 1
(a distinct `work:` kind emitted by `delegate`/`escalate`) has to change that
call site too, not just the readers.

Scope is `backlog/` and `active/` items only, per the reporter's own constraint —
a completed or superseded item is expected to carry stale references.
