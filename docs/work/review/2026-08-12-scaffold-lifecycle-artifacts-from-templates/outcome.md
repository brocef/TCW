# Outcome — Scaffold lifecycle artifacts from templates

Eight plan tasks, eight commits, plus this one. The suite was run to completion
at every commit boundary, not only the last.

## What shipped

### 1. `produces_note`, and the renderers move to it — `eb80d14`

`LifecycleStep.produces_note` carries the prose every row's `produces` held, and
the two renderers — the `produces:` line in `_lifecycle_lines`
(`tcw/work/cli.py:670-671`) and the `"produces"` key in `--json`
(`cli.py:915`) — read it. `produces` itself is untouched in this commit. Its own
commit exactly so the eleven baselines and `tests/test_lifecycle_hooks.py:277`
are a live check that neither surface moved: 1458 passed, the same count as
before the change. — criterion 12

### 2. `produces` becomes a tuple — `1697289`

`tuple[str, ...]` of extensionless names: `()`, `("spec",)`,
`("refined-outcome", "rework")`. Three tests in `tests/test_lifecycle_policy.py`
beside the existing id-set contract assertions — the tuple's shape (criterion
10), that every registered artifact except `intake` is produced by some stage,
and the drift invariant holding `produces` and `produces_note` to the same fact
(criterion 11). `--json` gains nothing; the baselines pass a second time.

`tests/test_skill_lifecycle_parity.py` moved in the same commit because
`artifacts_in(step.produces)` regexes a string and raises on a tuple. It now
compares `{f"{n}.md" for n in step.produces}` against the set `artifacts_in()`
returns instead of substring-matching extensionless names against the body, and
`test_verify_names_both_of_its_outcomes` is gone, subsumed. — criteria 10, 11, 13

### 3. `write_draft` on the store — `eb3e12d`

One method on the `WorkStore` ABC beside `write_artifact`, returning the locator.
`FsWorkStore` writes `<artifact>.draft.md` through `_atomic_write` + `_stage`;
that filename shape exists in exactly one place. Presence is the canonical
`_present` rule, so an empty draft is never present. No `read_draft`. Six store
tests in the new `tests/test_scaffold.py`. — criterion 9 (store half), and the
mechanics criterion 4 rests on

### 4. Built-in artifact templates — `587102d`

`ARTIFACT_TEMPLATES` in `tcw/work/templates.py`, one entry per `WORK_ARTIFACTS`
name, each derived from the matching stage document's `Produce` section.
`intake`'s is `""`. Set equality and the empty-intake case are both asserted.
`load_builtins()` joins `resolve.py` as the single source of TCW's shipped text
(see § C6 below). — criteria 5, 6

### 5. `tcw work scaffold <artifact> <ref> [--force]` — `94d2282`

The verb, ordered exactly as the spec's Design lists it. Legality inverts
`produces` over `LIFECYCLE_STEPS` into a stage-per-artifact map and looks the
stage up in `STAGE_STATUSES`; `intake` is absent from that map, so it has no
lookup and no `KeyError`. The built-in is the fallback when no `PlanEntry` has
`matched=True`, which is every project that has configured nothing. 27 tests.
— criteria 1, 2, 3, 4, 6, 7, 8, 9, 15, 16

### 6. No surface reports a draft — `91d51af`

Test-only. With every draft present and no real artifact: the board's string is
unchanged, `artifacts()` reports all absent, `tcw work show --json` is all
`false`, and `serve`'s detail response lists none present. It passes on the first
run because `serve` gates every artifact route on the registry and a draft is not
a registry name — a regression test, as the plan said. — criterion 14

### 7. Documentation Sync — `8a8f179`

One pass over the finished diff, after the code was done and green. All four
CLAUDE.md entries fire: `README.md` (the command-block lines and the drafts
paragraph under §"Reading a stage's instructions"), `docs/release-notes/
upcoming.md`, `docs/changelogs/upcoming.md`, and the `tcw-work` references
(`commands.md`'s row, and a new `hooks.md` section on how an `artifacts:` binding
is finally reached). C7's §"Binding your own skills and commands to the
lifecycle" is untouched.

Plus criterion 17's guard, which did not exist in either direction before: every
check in `tests/test_documented_cli_surface.py` asserts a documented verb exists,
and none asserted a shipped verb is documented. The positive check now sits
beside the negative one and covers `tcw work stage` as well as
`tcw work scaffold`. — criterion 17

### 8. Capability ledger — `79b2c16`

`work/customize-lifecycle-artifact-templates` added at `Missing` with the
planning back-pointer and `Subject: work-item/lifecycle-hook,
work-item/lifecycle-stage`, written through `tcw capabilities` rather than by
hand. Contradiction detection against the standing ledger found nothing to
resolve: `work/configure-the-work-lifecycle` covers *declaring* a template and
stays Supported, and `work/run-a-lifecycle-stage`'s promise that `tcw work stage`
writes "no lifecycle document, no draft" is still true — the drafts are a
different verb's. The `complete` gate flips the status. — criterion 18

## Tests

```
1510 passed in 253.88s (0:04:13)
```

The eleven `tests/fixtures/lifecycle_baseline/*.json` fixtures pass
**unmodified** — `git diff --stat eb80d14~1..HEAD -- tests/fixtures/
lifecycle_baseline/` is empty, and `tests/test_lifecycle_baseline.py` is 11
passed on its own. `tests/test_lifecycle_hooks.py` is unedited.

`tcw capabilities check` → `capabilities OK`. `tcw capabilities drift` → `no
capability drift`. `tcw validate` → `validate OK`.

## Corrections

**The plan's task 5 said to pass `Builtins(artifact_templates=ARTIFACT_TEMPLATES)`
at the call site.** It does not; it calls `load_builtins()`, per the coordination
requirement C6's spec §2 states and the plan does not mention. Passing a
constructed `Builtins` at the call site is exactly the second-loader shape both
specs forbid — C6 would then have to change the call site rather than extend the
loader, and the two halves could diverge. Nothing else about the task changed.

**Everything else the plan and spec claimed held.** The `produces` consumer
enumeration was complete (`grep -rn "\.produces\b"` finds no site the spec's
table missed), `read_artifact`'s divergence never came up because the verb routes
through `artifacts()`, and criterion 13's subset direction — corrected during
planning in `6ee69bb` — passes on the unmodified stage documents.

## Notes

### What C6 inherits

```python
@lru_cache(maxsize=1)
def load_builtins() -> Builtins:
    return Builtins(artifact_templates=ARTIFACT_TEMPLATES)
```

in `tcw/work/resolve.py`, directly under the `Builtins` dataclass it fills, with
a docstring telling C6 to populate `stage_prompts` **on this return value**.
C6 adds its half inside this function — reading `tcw/work/prompts/<stage>.md`
through `importlib.resources` and passing `stage_prompts=` alongside the existing
`artifact_templates=` — and adds no second function. `cli.py` already imports it
and `_scaffold` already calls it; the one remaining call site is C4's bare
`Builtins()` at the `resolve_prompts` call in `_stage`, which C6 owns and
replaces with `load_builtins()`.

The `lru_cache` is on the loader rather than inside it, so C6's file reads are
cached for free. If C6 wants its "missing or empty prompt file is a loud
failure" to be re-raised per call rather than cached, note that a cached
exception is not cached at all — `lru_cache` does not memoize raises — so the
failure surfaces on every call as it should.

### `SKILL.md` was left alone, and it was a judgment call with an answer

The plan flagged the stage/artifact table at `SKILL.md:29-35` as "a judgment call
at the gate". The gate answered it: the router's body is **exactly** 60 lines
against a 60-line budget whose stated rule on breach is "extract, don't grow"
(`tests/test_skill_lifecycle_parity.py:190-198`). The draft distinction went to
`references/hooks.md`, which is what an agent loads when it is about to run the
verb. C7 owns the router and can revisit it with room to spend.

### For C8's backlog audit

`read_artifact`'s `p.is_file()` (`tcw/store/fs.py:3478`) still disagrees with the
canonical presence rule (`fs.py:2217-2221`). C5 routed around it rather than
fixing it, exactly as the spec's Risks require, so the inconsistency outlives
this item and no test will remind anyone. It is the one adjacent defect this
implementation touched and deliberately did not repair.

### Read before believing the templates are done

The eight built-ins are asserted to exist and to be byte-for-byte what gets
written; nothing asserts they are *good*. They were read once in place — a
scratch node, `scaffold spec` and `scaffold plan`, board still showing `-` — and
the three refusal messages each name an openable locator and say what to do next.
That is a read, not a test, and it is the item's main verification-stage question
along with whether the draft/artifact distinction reads as obvious in the README
and release notes.
