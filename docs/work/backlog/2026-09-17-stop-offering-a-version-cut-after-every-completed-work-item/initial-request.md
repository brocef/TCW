# Stop offering a version cut after every completed work item

## The request

TCW instructs an agent to offer a version cut after every work item completes.
The user dismisses that offer every time. They know when they want to cut a
version; it does not need to follow each completed item.

Remove the instructions that tell an agent to **offer** a version cut. Keep
everything that tells an agent **how to cut one** — those instructions stay, and
are read when the user asks for a cut.

## Scope, as the requester set it

Two scoping decisions were taken in the conversation that opened this item:

1. **The removal comes out of TCW's shipped defaults**, not just this repo's
   configuration. Every TCW project stops offering, not only this one. This
   reaches the default `verify` prompt, the `work` skill's verify reference, the
   `documentation-sync` procedure, and the built-in Definition of Done list.
2. **The version-cut machinery stays and stays reachable on request.**
   `skills/documentation-sync/references/cut-version.md`,
   `scripts/cut_version.py`, and
   `skills/documentation-sync/scripts/unpushed-version.sh` are not deleted.
   Nothing that works today stops working; it simply stops being volunteered.

## Explicitly out of scope

- Deleting or changing `scripts/cut_version.py` or the version-cut ritual itself.
- Deleting `unpushed-version.sh` or its test. The fold-into-an-unpushed-tag
  question is still worth answering — when the user asks for a cut.
- Changing how versions are numbered, or the five-file lockstep.

## Constraints

- `version offered` is one of the five built-in Definition of Done items
  (`tcw/store/base.py`). Removing it changes the default checklist every TCW
  project inherits, and this repo's own `docs/work/dod.yaml` restates it.
- The default `verify` prompt text is embedded verbatim in a test fixture
  (`tests/fixtures/prompt_fallback/unconfigured.json`), so the prompt and the
  fixture move together.
- TCW ships a CLI, a plugin and a set of skills that drift from each other; the
  guide, the README and the capability descriptions describe this behavior too.

## Notes

The requester was asked for reference material at this stage and gave the two
scoping answers above; no external documents were offered.

## References

- `tcw/work/prompts/verify.md:30` — step 9, the instruction that states the
  offer. The root of what is being removed.
- `skills/work/references/lifecycle/stage-verify.md:31` — step 5, which names
  the option menu and hands off to the documentation-sync procedure.
- `tcw/work/procedures/documentation-sync.md:50` — "When to offer version and
  changelog options", where the substance of the offer lives.
- `tcw/store/base.py:2481` — the built-in Definition of Done tuple containing
  `version offered`.
- `docs/work/backlog/2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide/`
  — related, and **not** obsoleted by this. It serves *how* this project cuts a
  version from `tcw-config.yaml` rather than from a Markdown heading, which
  matters precisely when the user asks for a cut. Its spec already argues that a
  version cut "is always user-initiated and never automatic"; this item makes
  that true in the instructions as well. Its wording that refers to the
  "completion options" needs adjusting once this lands.
