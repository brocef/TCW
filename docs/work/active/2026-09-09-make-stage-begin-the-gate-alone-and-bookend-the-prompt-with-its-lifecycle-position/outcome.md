# Outcome: `stage gate` alone, with bookended prompts

Shipped as specified, with one design decision moved during implementation and
one name settled before it. `pytest -q`: **2443 passed**, 4 failed — the four
container artifacts that fail identically with this work stashed.

## What shipped

| Task | Commit | Note |
| --- | --- | --- |
| 1 — bookend table and wrapper | `0a1057a` | `STAGE_NEXT_STEPS` in `store/base.py`, `bookend()` in `work/resolve.py` — **applied by the CLI**, not the resolver; see below |
| 2 — `gate`: rename and narrowing | `0a1057a` | `_stage_gate`; `_stage_tail` loses `run_checks` and is `prompt`'s alone |
| 3 — the recorded fixture | `0a1057a` | re-captured, with the slug normalized |
| 4 — documents | `1ecce6a` | seven routers name both verbs; every other surface names the right one of the two |
| 5 — Documentation Sync | `1ecce6a` | migration guide rewritten, both `upcoming.md`, README checked |

## Acceptance criteria

| # | Result |
| --- | --- |
| 1 | Pass — `test_the_gate_prints_nothing_on_stdout`; run by hand, stdout 0 bytes |
| 2 | Pass — the illegal-status refusal is unchanged |
| 3 | Pass — `test_a_failing_check_stops_before_the_prompt_would_have_run` |
| 4 | Pass — `test_the_gate_resolves_no_prompt_at_all`, paired so a generator that never worked cannot satisfy the first half alone |
| 5 | Pass — `test_the_bare_form_is_a_usage_error_naming_both_verbs`, exit 2 |
| 6 | Pass — `test_prompt_refuses_a_work_item_for_inbox`, `test_gate_inbox_runs_the_stages_pre_bindings` |
| 7 | Pass — `test_every_stage_is_bookended_with_its_own_gate_and_next_step`, all seven |
| 8 | Pass — `test_the_bookends_wrap_a_projects_own_bindings_too` |
| 9 | Pass — `test_postmortem_says_nothing_follows_rather_than_omitting_the_section` |
| 10 | Pass — the seven prompt files are untouched; `test_shipped_prompts` still caps them at 50 |
| 11 | Pass — `test_no_exec_runs_nothing_and_names_what_it_skipped`, gate half |
| 12 | Pass — `test_prompt_accepts_no_exec_and_prints_no_text` |
| 13 | Pass — `test_every_stage_document_names_the_harness_neutral_binding_command` now requires **both** literals |
| 14 | Pass — re-captured, docstring records both events and the rule |
| 15 | Pass — rewritten; every command in it was run as shown |
| 16 | Pass — `tcw validate` 0, `tcw capabilities check` 0, suite green |

## What changed during implementation

**The bookend belongs to the CLI, not the resolver.** The spec said the resolver
wraps. Implementing it there broke a documented contract on the first run:
`resolve_prompts` promises that a stage whose only binding does not match
resolves to **nothing**, and wrapping turned that deliberate silence into a
header and a footer around an empty middle — which reads as a stage that failed
to resolve. Thirty of its unit tests also assert composed binding text, which is
not what a bookend is about. It moved to the print in `_stage_tail`, where the
single caller is, and `test_a_stage_that_resolves_to_nothing_is_not_bookended`
pins the contract that found it.

**The verb is `gate`, not `begin` narrowed.** Settled before implementation:
the verb runs no transition, writes no artifact and changes no field — verified
by running it and diffing the item — so `begin` promised an action it does not
perform, and success being silent left a user nothing to read. `gate` is the word
the codebase and its documents already use. The rename was free: `begin` appears
in no released changelog or release note and there are no version tags, so what a
user migrates from is 1.x's bare form, once. 108 branch-local call sites.

**The fixture is date-fragile without normalization.** Re-capturing produced
recorded stdout containing `2026-09-09-baseline-item`, because the bookends quote
the reference back and a slug carries its creation date. The replay creates its
item fresh, so the fixture would have failed at midnight rather than when the
text changed. Both capture and replay now normalize the slug to `<slug>`; every
other byte is still pinned.

**`prompt --no-exec` was worth reopening.** The narrowing would otherwise have
dropped the conditioned matched/skipped diagnostic from the CLI entirely, since
`gate --no-exec` reports only its own bindings. The original refusal's reason —
incomplete instructions on stdout — does not apply to a mode that prints nothing
there, so the flag is accepted and the plan goes to stderr.

## What this gave up, and what replaces it

Before this change, an agent following a stage document ran one command and was
gated on the way, because the command that printed the instructions was also the
gate. That is gone: `prompt` answers and never refuses, so nothing about wanting
the instructions makes anyone run `gate`.

The replacement is the header, in the resolved text rather than in the composing
skill — the skill is Claude-only and this has to reach Codex. It is weaker than a
coupling: it is a sentence, and it will be skimmed. **The post-mortem question
for this item is whether agents still run the gate.** If they stop, this change
cost more than the duplication it removed, and the answer would be to put the
refusal somewhere a reader cannot skip rather than to restore the duplication.

## Notes

The seven routers name **both** verbs, and the parity test requires both. Naming
only `prompt` would have left a Codex reader with no route to the gate at all,
which is exactly the failure mode above with no mitigation.

`_stage_tail` being `prompt`'s alone undoes Task 1 of
`2026-09-02-split-tcw-work-stage-into-prompt-and-begin-subcommands`, which
extracted it because the two verbs shared a tail. They no longer share one, and a
parameter a single caller never passes is worse than two functions. Recorded
rather than left for a reader to wonder about.

Two breaking changes reached the same command in one release. That is acceptable
only because one of them never shipped: the migration a user performs is from
1.x's bare form to two verbs, in one edit.
