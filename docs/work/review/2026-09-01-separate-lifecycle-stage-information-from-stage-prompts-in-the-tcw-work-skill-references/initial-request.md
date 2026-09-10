# Separate lifecycle stage information from stage prompts in the tcw-work skill references

Do a holistic review of how the TCW work lifecycle handles customizable
prompting, and fix what the review finds in the `tcw-work` skill's reference
documents.

The entry point for the skill is `skills/tcw-work/SKILL.md`. It sketches the
lifecycle and points the agent at a reference document for each stage. The
concern is that the `references/stage-{stage}.md` files were doing two jobs at
once:

1. Describing the lifecycle stage — what it takes in, what it puts out, what it
   is for.
2. Acting as the built-in prompt for that stage, used when the consuming project
   does not supply its own.

They should only do the first. Each stage document should describe the stage,
and then say: *"Get your instructions on how to produce the output by running
`tcw work stage {stage name} {slug}`."* The default, built-in prompts should be
their own separate files.

## Reorganize `references/` into subfolders

The `references/` folder has grown flat and cluttered. Group it:

- `references/lifecycle/` — the `stage-*.md` files: brief, generic descriptions
  of each lifecycle stage.
- `references/lifecycle/default/` — the default prompts for each lifecycle
  stage.
- `references/procedures/` — documents describing common procedures, such as
  `decompose.md` and `delegation.md`.

More subfolders can be added later as needed; this is a starting point.

## What the requester decided after reading the findings

Investigating the repository first turned up that most of point 1 above had
already been done, in v1.0.0. That was reported back, and the requester chose
the following scope in response.

**Still wanted, all four:**

- Reorganize `references/` into subfolders.
- Sharpen the wording each stage document uses to point at its prompt, to the
  explicit sentence above.
- Fix `stage-inbox.md`, which really is still doing both jobs, by shipping a
  built-in `inbox` prompt so that `tcw work stage inbox` works and the document
  can become a short pointer like the other six. The requester chose this over
  the two smaller alternatives (move the methodology to `procedures/`, or leave
  it as a documented exception), accepting that it means changing the command
  line tool and not only the documents.
- Make the built-in prompts findable from the skill, by leaving them where the
  installed tool reads them and adding a `references/lifecycle/default/` note
  that points at them and explains which source wins over which.

**Folder layout chosen** — `lifecycle/` holds the stage documents only;
everything else that is not a procedure stays where it is:

```
references/
  commands.md
  tags.md
  transitions.md
  hooks.md
  epic-deltas.md
  cross-node-deltas.md
  lifecycle/
    stage-*.md  (7)
    default/           <- note pointing at tcw/work/prompts/
  procedures/
    decompose.md
    delegation.md
    audit-backlog.md
    consolidate-plans.md
```

## Constraints

- The requester asked that the TCW work planning skill be used to run this
  work, rather than jumping straight to editing.

## Notes

The requester was asked what was unclear and answered two rounds of questions;
their answers are recorded above under *What the requester decided*. They were
not separately asked for outside reference material — the pointers they gave in
their own request (`skills/tcw-work/SKILL.md` and the `references/` folder) were
the material, and everything else needed came from reading this repository.

One finding reported back to them is worth carrying into `spec` as a hard
constraint rather than a preference, because it makes the literal request
impossible as written: the built-in prompts cannot live under
`references/lifecycle/default/`. They are read out of the installed Python
package (`tcw/work/prompts/*.md`), and `pyproject.toml` ships only the `tcw*`
packages, so a project that installs the command line tool from PyPI without the
plugin would lose every default prompt. The requester accepted this and picked
the "point at them from the skill" option instead.

## References

- `skills/tcw-work/SKILL.md` — the skill entry point named in the request; the
  table of stages and their documents lives here.
- `skills/tcw-work/references/` — the folder being reorganized.
- `tcw/work/prompts/*.md` — where the built-in stage prompts actually live
  today; the six shipped prompts, one per stage except `inbox`.
- `tcw/work/resolve.py` — `load_builtins()` reads those prompt files and is the
  code that hard-codes the `inbox` exclusion.
- `tcw/work/cli.py` — the `tcw work stage` command; it refuses `inbox` today
  because that stage runs before an item exists.
- `tests/test_skill_lifecycle_parity.py` — the test that keeps the stage
  documents honest against the lifecycle table; it locates them by path and will
  need to follow the move.
- `tests/test_shipped_prompts.py` — the test that checks the shipped prompt set;
  it derives that set as "every stage except `inbox`".
- `pyproject.toml` — the packaging rules that decide which of these files reach
  a PyPI install.
