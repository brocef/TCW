# Documentation for TCW 3.0: README, guides and the opt-in git example

TCW 3.0 (epic [TCW-68](https://proposit.atlassian.net/browse/TCW-68)) changes the
work axis from the ground up: items no longer move between status folders, one
command (`advance`) replaces five, a project picks one work backend (the
repository, or Jira), and TCW stops committing, pushing or branching. The
documentation still describes 2.8. A user who reads the README, a guide or the
configuration reference after 3.0 ships would be told to run commands that no
longer exist and to set keys that are now errors.

## What is wanted

User-facing documentation that describes TCW 3.0 as it is, and explains why the
description of the product lives next to its code.

1. **The README.**
   - A new section right after the Overview, _"Why taxonomy and capabilities live
     in the repository"_. This is the owner's explicit request from TCW-67. It
     says that the product's description changes in the same commit as the code
     that changes it (implement is the stage that changes it) and reviewers see
     both; that any commit shows the product as it was then, readable by anyone;
     that documentation could one day be generated from it, such as a knowledge
     base where a reader picks any point in time (a possibility, not a promised
     feature); and that tickets describe changes and are short-lived, while the
     records describe the product, are long-lived, and are never stored in Jira
     in either mode.
   - The Work overview and the Jira section rewritten to describe 3.0 as it is,
     not as a list of differences from 2.x. What changed belongs in the release
     notes and the migration guide.
   - The filesystem backend presented as a fully supported way to use TCW,
     alongside Jira, not as a fallback.
   - The web app section matching TCW-77: no Node.js needed to run it, and it
     reads, edits and creates documents but runs no lifecycle actions.
   - The documentation index updated, linking the 3.0 migration guide.
2. **The guides and other documents.** Each is rewritten, merged or deleted:
   - `docs/guide/jira.md`, for the Jira-first model: people outside engineering
     writing and reading tickets in plain language; the request template's
     "Product changes"; the QA plan comment and QA on the ticket; the optional
     postmortem comment; who owns which fact, and the stage-to-status mapping;
     adopting tickets and delegating work; and checking a Jira workflow with
     `tcw validate --remote`.
   - `docs/guide/work.md`, the main lifecycle guide.
   - `docs/guide/multi-repo.md`, around "project" and `new --project`.
   - `docs/guide/taxonomy-and-capabilities.md`, which says records change at
     completion; under 3.0 they change during implement. It gains the chain from
     request to declared changes to records, and drift.
   - `docs/guide/linking-and-validation.md`, which still names `graveyard.yaml`
     and `tracker.yaml`.
   - `docs/lifecycle/abstraction.md`, `implementation.md` and `harness.md`.
     TCW-69's spec hands the abstraction document's rewrite to this item: in 3.0
     the model reads item folders in both modes, a folder move is no longer a
     transition, and "node" is replaced by "project".
   - `docs/work-inbox-template.md`.
   - The `--worktree` section of TCW's own `CLAUDE.md` (which is `AGENTS.md`).
   - A user-facing description of the output contract TCW-73 sets: what goes to
     stdout, what goes to stderr, and what each exit code means.
3. **Configuration documentation.** `skills/configure/references/` is the one
   home of each configuration key's documentation, including the table of
   which keys a person may override in their personal configuration and which
   are shared by the team (TCW-72). Guides link to it rather than repeating it.
   `tracker.md` and `projects.md` there are rewritten for the new configuration.
4. **The opt-in git example.** The configuration guide shows a project that keeps
   git in step with each stage change, clearly labelled as something a project
   adds, not something TCW does:
   - pulling is prompt text ("pull before starting"), not a `pre` gate, so a
     network failure never blocks a move;
   - a `post` hook commits the item's files and succeeds when there is nothing
     to commit, as happens in Jira mode, where a move may change no file;
   - pushing is shown as an optional extra.
5. **Release notes and changelog** entries for this change, in the `upcoming/`
   folders, and the user-facing introduction to 3.0.0 in the release notes.

## Constraints

- **Describe 3.0 as it is.** No "previously", "no longer" or "since 3.0" in the
  README or guides; differences from 2.x go to the release notes and the
  migration guide (TCW-76).
- **Plain language.** No insider shorthand or metaphors; a technical term is
  defined the first time it appears.
- **One source for each fact.** A configuration key is documented once, in the
  configure skill's references, and everything else links there.
- **TCW never changes git state.** Every git action in the documentation is
  presented as the project's own choice, made through its own prompts and hooks.
- **Works under Claude Code and Codex alike.** The git example uses only TCW's
  own prompt bindings and hooks, which the `tcw` CLI runs identically under
  both, never a harness-specific feature.
- **Breaking changes are expected.** This ships in 3.0.0.

## Out of scope

Owned by sibling items:

- `docs/guide/web-viewer.md`: TCW-77.
- The built-in stage prompts, procedures, skills and agents, including the
  request template's text: TCW-74.
- The migration guide, TCW's own `tcw-config.yaml`, TCW's own repository
  adopting the git example, and the rest of TCW's `AGENTS.md`: TCW-76.
- Capability records under `docs/capabilities/`: each of TCW-69 to TCW-73 and
  TCW-77 updates the records for what it changes, removes or adds.
- Help and message strings inside the Python code: TCW-73.

## Notes

- **There was no one to ask.** This request was written from the ticket
  (`intake.md`, imported from Jira), the epic, the design-decision record, the
  sibling tickets and TCW-69's finished spec. Points that are inference rather
  than something the ticket states:
  - The ticket says to add "the `spec/capabilities.yaml` chain" to the taxonomy
    and capabilities guide. The owner confirmed on 2026-10-01 (in TCW-69's
    review) that the file lives at the item folder's root,
    `<item>/capabilities.yaml`. This request assumes the guide documents the
    confirmed location.
  - "The configuration guide" in the ticket is taken to mean
    `docs/guide/configuration.md`.
  - The release-notes introduction to 3.0.0 is not in the ticket; it is assumed
    to belong here because this item owns user-facing documentation and the
    ticket sends "what changed" to the release notes.
  - This item describes behavior that other items build. It is assumed to be
    implemented after TCW-69 to TCW-74 and TCW-77 have landed on the epic
    branch, and before TCW-76, which links to and adopts what this item writes.
- **Reference material.** None was asked for, since there was no requester to
  ask; the references below are the ones the ticket and the epic point at.
- **Self-hosting.** This item edits documentation, not `tcw/`, but it lands
  while the epic is changing `tcw/`, so the repository's own board is driven by
  editing files, as `CLAUDE.md` requires.

## References

- [TCW-75](https://proposit.atlassian.net/browse/TCW-75) (`intake.md`): the
  ticket; the agreed scope of this item.
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68) and its attached
  `TCW-68-design-decisions-2026-09-30.md`: the vision, and the original wording
  of the README section and the git rule.
- TCW-69's spec
  ([`spec.md`](../2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance/spec.md)):
  the core model the documentation describes, the owner-confirmed
  decisions, and the abstraction-document rewrite it hands to this item.
- [TCW-70](https://proposit.atlassian.net/browse/TCW-70) and
  [TCW-71](https://proposit.atlassian.net/browse/TCW-71): the filesystem and
  Jira backends that the work and Jira guides describe.
- [TCW-72](https://proposit.atlassian.net/browse/TCW-72): personal configuration
  and the shared-or-overridable key table whose home is the configure references.
- [TCW-73](https://proposit.atlassian.net/browse/TCW-73): the command surface and
  the output and exit-code contract the documentation describes.
- [TCW-74](https://proposit.atlassian.net/browse/TCW-74): the prompts and skills,
  whose boundary with this item has to be drawn.
- [TCW-76](https://proposit.atlassian.net/browse/TCW-76): the migration guide this
  item links, and the adoption of the git example in TCW's own repository.
- [TCW-77](https://proposit.atlassian.net/browse/TCW-77): the web viewer the
  README's web app section must match.
- `README.md`, `docs/guide/`, `docs/lifecycle/`, `skills/configure/references/`:
  the documents being rewritten.
