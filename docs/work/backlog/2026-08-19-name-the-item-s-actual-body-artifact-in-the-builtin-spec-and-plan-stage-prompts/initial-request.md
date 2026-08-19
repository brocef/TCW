# Name the item's actual body artifact in the builtin spec and plan stage prompts

## Request

The builtin `spec` and `plan` stage prompts both open by naming
`initial-request.md` as their input. On 1.0.0 that file is frequently absent:
creation no longer writes one, so an item created from piped input or from
`tcw work inbox accept` carries only `intake.md`. `tcw work list` shows such an
item as `i` and `tcw work show --json` reports `"initial-request": false`.

An agent handed the `spec` prompt on an intake-only item is therefore told to
read a document that does not exist, and is told nothing about the `intake.md`
sitting beside it — which on an inbox-adopted item *is* the entire request. The
stage prompt is the only place the agent is told what to read, so the omission
is load-bearing rather than cosmetic.

What is wanted: the stage prompt should account for whichever body artifact the
item actually has. Either it names what is really there, or it names both and
says how they differ — intake being raw arrival kept verbatim, the request being
the written-up version. The `## References` instruction in the `spec` prompt,
which currently reasons about a section of `initial-request.md`, should degrade
sensibly on an item that only ever had intake.

The same assumption is present in the plugin's own skills — the
`tcw-triage-issues` skill (`skills/tcw-triage-issues/SKILL.md` §5) still tells
the triager to write `initial-request.md` at intake time and then run the
`request` stage over it, which is backwards on 1.0.0. That skill drift is part
of this request, not a follow-up.

## Why it lands on 1.0.0

Under 0.21.x every item had an `initial-request.md`, because creation wrote one
unconditionally. 1.0.0 deliberately stopped doing that, which was the right
call, but the builtin stage prompts still assume the old guarantee. On the
reporter's workspace 60 of the current items are intake-only, so this is now the
common case rather than the edge one.

## Scope

In scope: the builtin stage prompts that assume an `initial-request.md`, and the
plugin skills carrying the same assumption. Confirmed with the requester as one
item covering both.

Out of scope: changing how items are created. 1.0.0's decision to stop writing
an unconditional `initial-request.md` stands; the prompts are what must adapt.

## References

- GitHub issue [#22](https://github.com/brocef/TCW/issues/22) — the report this
  item was accepted from. The body is preserved verbatim in `intake.md`, but the
  live thread may carry comments filed after acceptance; `spec` should read it
  rather than rely on the captured copy.

## Notes

- Requester is @brocef, who is also the maintainer, so the request and the
  acceptance are the same person's.
- The reporter's issue includes a suggested remediation (resolve the body the
  way `tcw work show` does and name what was found). That is recorded here as
  the requester's own preference, not as a decision — `spec` chooses the
  approach.
