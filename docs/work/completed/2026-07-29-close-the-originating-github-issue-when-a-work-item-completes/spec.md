# Spec: Close the originating GitHub issue when a work item completes

## Capability changes

**New:** `work/customize-the-definition-of-done` — the node-level DoD override.
It is **already implemented and already reachable**; what is missing is any way
to find out about it. Seeded `Missing` and flipped at `complete`, because from
the ledger's point of view "what a user can do" includes "know that they can".

Declaring it is not scope creep — this item's whole design rests on that
mechanism, and depending on an undocumented feature while leaving it
undocumented is how the next person deletes it.

**Changed:** `work/complete-a-work-item` (`cap-24543d`) — its closing line says
the checklist "was the same fixed checklist on every item". That is inaccurate:
`FsWorkStore.dod_checklist` (`tcw/store/fs.py:2012`) reads `docs/work/dod.yaml`
and only falls back to `DEFAULT_DOD` (`tcw/store/base.py:774`) when absent.

**Changed:** `plugin/triage-github-issues` (`cap-2c9a74`) — its scope grows from
one-way intake to include the closeout reply.

## Problem

`tcw-triage-issues` writes a one-way link. An accepted issue's URL lands in the
new item's `## Origin`, and nothing goes back — the reporter is told the work is
tracked and then hears nothing, including when it ships.

This is not hypothetical. Two comments posted from this repo yesterday
([#9](https://github.com/brocef/TCW/issues/9#issuecomment-5122247414),
[#8](https://github.com/brocef/TCW/issues/8#issuecomment-5122248161)) both say
*"Leaving this open until it ships."* That is a promise with nothing behind it.

## Goals

1. Completing a work item that came from a GitHub issue prompts the closeout
   reply — reliably enough that forgetting is the exception, not the default.
2. The prompt reaches a Codex agent and a Claude agent identically.
3. The reply fits the resolution. `done` is not the only way an item closes, and
   `superseded` in particular must not read to the reporter as a refusal.
4. Nothing is posted without the user approving the exact text — the sibling
   skill's core guarantee, honored from this end too.
5. The mechanism the design leans on stops being undocumented.

## Non-goals

- **No new CLI verb, flag, or model field.** See Design §2 and §3.
- **No network call from `tcw`.** `tcw work complete` must not become able to
  fail because GitHub was unreachable.
- **No automatic posting.** A closeout that comments on its own would break goal
  4 from the other direction.
- **No broader sync** — labels, assignees, milestones, status mirroring.
- **No back-fill.** Items completed before this change are not revisited.

## Design

### 1. The prompt is a Definition-of-Done line

`tcw work complete` already prints a checklist and refuses until `--confirm`
(`tcw/work/cli.py:810-816`). That checklist is **already node-configurable**:

```python
# tcw/store/fs.py:2012
def dod_checklist(self) -> list[str]:
    p = self.root / "dod.yaml"
    ...
    return list(DEFAULT_DOD)
```

So the closeout prompt costs **no code**. TCW adds `docs/work/dod.yaml` carrying
the five defaults plus one line for the originating issue.

It passes the litmus test without effort: `dod_checklist()` is already declared
on the abstract store (`tcw/store/base.py:983`), so any adapter serves it. And
it satisfies goal 2 for free — `tcw work complete` prints the same checklist to
whoever runs it.

**The file replaces the defaults, it does not extend them.** `dod.yaml` must
restate all five or they vanish silently.

### 2. Finding the issue: grep the item folder, and no new field

`tcw work path <slug>` resolves the folder; the issue URL is in its
`initial-request.md` under `## Origin`. That URL is already the join key the
sweep writes and reads back, so reusing it adds nothing new to maintain.

**The `source`/`external-ref` field is declined again.** The request named this
the central question. The answer is no, for a reason stronger than YAGNI: the
abstract model already covers it. Provenance is *body content*, and body is one
of the four things the model says an item has. A field would buy machine-readable
lookup that nothing needs — one grep at one moment, performed by an agent that is
already reading the item.

If a second consumer ever appears, revisit. One does not.

### 3. Which resolutions, and what each says

`complete --resolution` takes `{done, duplicate, superseded, wontfix}`.

| Resolution | Reply | Close? |
| --- | --- | --- |
| `done` | It shipped, in which version | Yes |
| `duplicate` | Name the item that absorbed it | Yes |
| `wontfix` | The actual reason | Yes |
| `superseded` | What replaced it — **and whether the ask was absorbed or deferred** | Only if absorbed |

The `superseded` row is not symmetry for its own sake. It is the exact defect
the triage skill was corrected for (`4364a5a`): a superseded item may have had
its request *deferred* rather than absorbed, and closing the issue as though the
project declined it is the worst reply either skill can produce.

**One thing the checklist cannot carry.** `checklist = st.dod_checklist() if
shipping else []` (`tcw/work/cli.py:810`) — `shipping` is `resolution == "done"`,
so a **discard never prints the DoD at all**. Three of the four rows above get no
prompt from the checklist, and their guidance has to live in the stage document
instead. The DoD covers the `done` row only.

### 4. Where the procedure lives

The judgment — draft the reply, get exact-text approval, post, close — belongs to
`tcw-triage-issues`, which already owns `gh` and the approval rule. It gains a
closeout section.

`skills/tcw-work/references/transitions.md` gains a pointer in its `complete` and
`discard` sections. The discard pointer is the load-bearing one, per §3.

### 5. Documenting `dod.yaml`

Grep says `dod.yaml` appears nowhere in `README.md`, `skills/`, or `docs/*.md`.
The mechanism this design depends on is currently discoverable only by reading
`fs.py`. README and the `tcw-work` skill get it, and the ledger gets §0's new
capability.

## Acceptance criteria

1. `docs/work/dod.yaml` exists, restates all five `DEFAULT_DOD` entries, and adds
   one naming the originating issue.
2. `tcw work complete <slug> --resolution done` prints the new line. Checkable by
   running it on the next completed item.
3. `tcw work complete <slug> --resolution wontfix|duplicate|superseded` prints
   **no** checklist — confirming §3's constraint rather than assuming it.
4. `skills/tcw-triage-issues/SKILL.md` has a closeout section covering all four
   resolutions, stating that `superseded` closes the issue only when the ask was
   absorbed, and restating the exact-text approval rule.
5. `transitions.md` points at it from both `complete` and `discard`.
6. `README.md` and `skills/tcw-work/SKILL.md` (or a reference it routes to)
   document `dod.yaml`, including that it replaces rather than extends the
   defaults.
7. `work/customize-the-definition-of-done` exists and reads `Supported` at
   completion; `work/complete-a-work-item`'s "same fixed checklist" line is
   corrected; `plugin/triage-github-issues` covers closeout.
8. No diff under `tcw/` — no CLI, model, or store change.
9. `pytest` green; `tcw validate` and `tcw capabilities check` clean.
10. Issues #9 and #8 remain open and unclosed — their items have not shipped, so
    this change must not touch them.

## Risks

- **The DoD is `[prompted]`, not `[gated]`.** `transitions.md:70` is explicit.
  An agent can acknowledge the line without doing anything, and nothing detects
  it. This design makes forgetting unlikely, not impossible — enforcement would
  need `tcw` to make a network call, which non-goal 2 rules out. Accepted, and
  stated rather than papered over.
- **The line fires on every completed item**, including the majority with no
  originating issue. Mitigated by wording it conditionally; the cost is one
  ignorable line per completion, which is cheaper than the machinery to make it
  conditional.
- **Creating `docs/work/dod.yaml` silently overrides the defaults.** Getting it
  wrong deletes four checks from every completion in this repo, with no error.
  Criterion 1 exists for this.
- **Three of four resolutions get no automatic prompt** (§3). The discard path
  depends entirely on the agent reading `transitions.md`.
- **The reply is public and irreversible.** Unchanged from the sibling skill;
  same mitigation, per-message exact-text approval.

## Notes

**Assumption:** that `docs/work/dod.yaml` is read relative to `self.root` (the
work root) rather than the node root — `fs.py:2013` says `self.root / "dod.yaml"`
and the work root is `docs/work/`, but this has not been executed. Task 1
verifies it by running `complete` rather than by reading the line again.
