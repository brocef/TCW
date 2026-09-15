# Plan — A test that passes on its first run must be falsified before it is trusted

Five tasks. The ordering exists for one reason: **the tests for this item are
themselves the kind of test the item is about** — string assertions against a
document — so they are written first, watched fail, and then falsified, out loud.

## Tasks

### 1 — The shipped rule's test, red first

`test_the_implement_prompt_requires_falsifying_a_green_test` and
`test_the_implement_step_list_did_not_grow`, against `load_builtins()` rather
than by reading the file, so they test what a user is served rather than what is
on disk.

**Files.** `tests/test_skill_lifecycle_parity.py` (it already owns the prompt's
guards) — or a new module if the parity file's fixtures do not fit; decide at
implementation, do not force it.
**Proves it.** Both red, for the right reason: the string is absent, and the step
count is what it is.

### 2 — Rewrite step 3 of the shipped prompt

`tcw/work/prompts/implement.md:19-20`. Rewritten, not appended to — a fourth
bullet is the shape of thing that gets skimmed, and this rule's subject is an
instruction that was read and not acted on.

**Files.** `tcw/work/prompts/implement.md`.
**Proves it.** Task 1's tests green; the four existing guards still green
(shared-sentence, router ceiling, one-documentation-span, code-block hazard).

### 3 — Falsify task 1's tests, and say so

The item's own rule, applied to the item. Delete the new sentence from the prompt
and confirm both tests go red; restore it. Record the result in `outcome.md`.

Its own task rather than a step inside task 2, because a check folded into
another task is a check that gets skipped when that task is going well — which is
precisely the failure mode this whole item addresses.

**Files.** None permanently.
**Proves it.** Two observed reds, recorded.

### 4 — The local message-assertion rule

`docs/lifecycle/implementation.md`, beside the two rules the epic's post-mortem
already put there, plus a test that `tcw work stage implement` composes it.

**Files.** `docs/lifecycle/implementation.md`, the test module from task 1.
**Proves it.** Criterion 3.

### 5 — Capability body, docs, suite, `outcome.md`

`work/run-a-lifecycle-stage`'s body describes the stage's instructions, so it goes
stale here. Then the Documentation Sync block below, the full suite, the
bare-shell walk, and the outcome.

**Files.** `docs/capabilities/work/run-a-lifecycle-stage/description.md`,
`docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`, the item folder.

## Documentation Sync

Evaluated against this node's declared entries (`tcw work docs`; source: config).

| Entry | Trigger | Fires | What it needs |
| --- | --- | --- | --- |
| `README.md` | Public-API | **no** | No CLI surface changes: no verb, no flag, no output format. The text a stage prints is not documented in the README. |
| `docs/release-notes/upcoming.md` | Public-API | **yes** | User-facing: the instructions `tcw work stage implement` gives are what a user acts on. Plain language, one short paragraph. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **yes** | Changed: the rewritten step 3, and why it was rewritten rather than appended. |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | **no**, and deliberately | The `implement` stage's lifecycle is unchanged; only the shipped prompt's wording moves. Restating it in `stage-implement.md` would *fail* `test_no_router_sentence_appears_in_its_prompt`, which is the guard telling us the router is the wrong home for it. |

The `README.md` and skill rows are the ones worth stating as **no** rather than
omitting, because both are plausible-looking fires and one of them is actively
prevented by a test.

## Verification

What the suite cannot check:

- **Read the new step 3 cold.** Does someone who has never met this rule know
  what action to take when a test comes up green? The failure this item fixes is
  an instruction that read fine and produced nothing, so "it reads fine" is not
  the bar — "I know what to do in the next thirty seconds" is.
- **Confirm it describes an action, not a disposition.** "Break the behaviour and
  confirm it goes red" survives shortening; "be suspicious of green tests" is what
  it will drift into if anyone trims it for space.
- **Codex parity.** The prompt is the half that reaches Codex users, and it is
  printed by the CLI rather than by a hook, so this is the correct layer — confirm
  it from a bare shell under no harness.

## Notes

- Task 3 has no deliverable and is not optional. It is the item practising what it
  ships, and its absence from the diff would be the most eloquent possible
  argument against the rule.
