# Outcome — The init ignore guard probes fixed path names that a rule could collide with

Two commits, as planned. The item stayed the size the spec predicted.

## What shipped

**Task 1 — two probes, `all(...)`, reworded message.**
`tcw/store/fs.py`, the `init` pre-flight leaf loop. The single probe built from
`an-item` became a two-element list over `("an-item", "some-slug")`, and the
refusal moved from `if git_ignored(...)` to
`if all(git_ignored(...) for p in probes)`. The message went from describing the
folder as being inside an ignored path to naming the outcome for items, keeping
the substring `gitignored` so the five existing `pytest.raises(match=…)`
assertions hold unedited. The comment block gained a paragraph recording why
there are two names and why the *file* name is not varied.

Tests, same commit, in `tests/test_non_git_writes.py`: two acceptance cases
(default store and external store, `.gitignore` = `an-item*`) and one
`parametrize` over the six broad rule shapes.

**Task 2 — documentation sync.** The changelog entry describing the
single-probe guard was **amended in place** rather than joined by a second
bullet: it has not shipped, so a second bullet would read as a
regression-then-fix that never happened publicly. The other three declared
entries do not fire, for the reasons the plan gives; re-checked against the tree
and still correct.

## Test result

`python -m pytest tests/test_non_git_writes.py -q` → **50 passed**. Full suite
green — final number recorded at `verify`.

The red-first discipline paid off here in a way worth recording. The first run
of the new tests showed **three** failures, not the expected two: the third was
`test_init_still_refuses_every_broad_ignore_rule[*]`, and it was a **fixture
bug, not a defect**. A `.gitignore` containing `*` hides `.gitignore` itself, so
the shared `commit_all` helper had nothing to commit and died. Fixed by staging
that one file with `git add -f`, which is also the more honest fixture: the
guard asks the *rules* (`--no-index`), so what matters is that the rule is on
disk, not that it is tracked.

After that, exactly the two intended tests were red and **all six broad rules
were already green** — which is the important half of this change. Two probes
make the guard strictly *less* likely to fire, so every rule that should still
refuse had to be re-proved rather than assumed.

## Manual verification

Run at the shell in a throwaway repo, both directions (plan's Verification
step 4):

```
# .gitignore = an-item*   → previously refused, now scaffolds
$ tcw init work --id demo
Node marker: tcw-config.yaml
.gitignore: resolved work (completed/, discarded/) stays on disk, out of the tracked tree

# .gitignore = docs/work/ → still refuses, and names the leaf
$ tcw init work --id demo
tcw init: items written in …/docs/work/inbox would be gitignored, so work filed
there would not be tracked
```

`grep -rn "work store folder" tcw/ tests/` → empty (criterion 6); the only
remaining hits anywhere are this item's own spec and plan, quoting the old text.

## What the plan and spec got wrong

**Nothing material, which is worth stating plainly rather than leaving as an
empty section.** This is the one item in the batch whose plan survived contact
intact: every line citation resolved, the six broad rules behaved exactly as the
spec's experiment table predicted, and both protected tests
(`test_init_still_accepts_the_resolved_status_rules_it_writes_itself`,
`test_init_re_runs_on_a_healthy_external_store`) passed unedited.

Two small corrections:

- **The plan's test-fixture assumption.** It said to reuse `commit_all` for
  every case. That does not work for `*` — see above. A one-line divergence, but
  it is the kind that silently produces a green-for-the-wrong-reason test if
  nobody reads the red output.
- **The refusal message rewording is a scope addition** beyond the literal
  request, which asked only about probe collision. It is one string and it kept
  every existing assertion working, so it stayed. Flagging it because the
  requester should get to disagree: the old message was not *wrong*, it just
  blamed the folder when the folder is usually fine and one rule is not.

## Residual risk, accepted with eyes open

`**/state.yaml`, `*.yaml` and `*.md` ignore **both** probes and therefore still
refuse, even though such a rule may have nothing to do with the work store. This
is honest rather than accidental — a rule hiding every `state.yaml` really does
hide every item's status record — but a project that ignores `*.yaml` for
unrelated reasons must scope or negate that rule before `tcw init`. Recorded in
the spec's Risks; unchanged by implementation.

And the ceiling the guard has always had is untouched and still marked in the
source: a configure-time check cannot see a `.gitignore` written after `init`, a
rule naming a real slug, or one arriving with a later `git pull`. That is the
sibling item
`2026-08-20-enforce-the-gitignore-trap-at-write-time-not-only-at-init`.

## Notes

- **Abstraction litmus test:** passes, unchanged. `git check-ignore` has no
  abstract analog — a remote tracker has no ignore rules — and this guard is
  already private to the filesystem adapter's `init`. No interface change.
- **Sibling collision:** none. This item touches only the `init` pre-flight
  loop; the write-time item touches `git_stage` and `git_mv`. They can land in
  either order, and this one landed first.
- **Capability ledger:** no delta, as the spec settled. Both entries that
  describe the guard describe it by intent and neither quotes the message;
  re-checked with `tcw capabilities check` (clean).
