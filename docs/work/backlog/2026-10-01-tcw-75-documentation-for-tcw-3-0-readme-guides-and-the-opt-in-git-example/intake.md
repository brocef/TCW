# TCW-75 — Documentation for TCW 3.0: README, guides and the opt-in git example

Imported on 2026-10-01 from [TCW-75](https://proposit.atlassian.net/browse/TCW-75) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). The original decision record is attached to the epic; where this ticket differs from it, this ticket is current (it includes the outcome of an adversarial review).

h1. What this delivers

User-facing documentation that describes TCW 3.0 as it is, and explains why the product's description lives next to its code.

h1. README

* *New section right after the Overview: "Why taxonomy and capabilities live in the repository."* This is the owner's explicit request from TCW-67.
** The product's description changes in the same commit as the code that changes it, and reviewers see both. Implement is the stage that changes it.
** Any commit shows the product as it was then: its vocabulary, features and capabilities, readable by anyone.
** Documentation could be generated from it, e.g. a knowledge base that updates with every change and lets a reader pick any point in time. This is a possibility, not a promised feature.
** Tickets describe changes and are short-lived; the records describe the product and are long-lived. They are never stored in Jira, in either mode.
* The Work overview and Jira section are rewritten to describe 3.0 as it is, not as a diff from 2.x. "What changed" belongs in the release notes and migration guide.
* Filesystem mode is presented as first-class, alongside Jira mode.
* The README's web app section is updated to match TCW-77: no Node requirement, reading, editing and creating only.
* The documentation index is updated, and links the 3.0 migration guide.

h1. Guides and other documents in scope

Each is rewritten, merged or deleted:

* {{docs/guide/jira.md}}, for the Jira-first model. It covers:
** people outside engineering writing and reading tickets in plain language;
** the request template's Product changes;
** the QA plan comment and QA on the ticket;
** the optional postmortem comment;
** ownership and the stage/status mapping;
** adoption and delegation;
** workflow compatibility via {{tcw validate --remote}}.
* {{docs/guide/work.md}}, the main lifecycle guide.
* {{docs/guide/multi-repo.md}}, rewritten around "project" and {{new --project}}.
* {{docs/guide/taxonomy-and-capabilities.md}}. It currently says records flip at completion, which contradicts the new model. Add the {{spec/capabilities.yaml}} chain and {{drift}}.
* {{docs/guide/linking-and-validation.md}}, which still mentions {{graveyard.yaml}} and {{tracker.yaml}}.
* {{docs/lifecycle/abstraction.md}}, {{implementation.md}} and {{harness.md}}.
* {{docs/work-inbox-template.md}}.
* The {{--worktree}} section of TCW's own {{CLAUDE.md}}.
* A user-facing description of the stdout, stderr and exit-code contract (TCW-73).

{{docs/guide/web-viewer.md}} is rewritten by TCW-77.

h1. Configuration documentation

* {{skills/configure/references/}} is the canonical home of each key's documentation, including the shared/overridable table (TCW-72). Guides link to it rather than repeating it.
* {{tracker.md}} and {{projects.md}} there are rewritten for the new config.

h1. The opt-in git example

The configuration guide shows a project that keeps git in step with each stage change, clearly labelled as something a project adds:

* Pulling is prompt text ("pull before starting"), not a {{pre}} gate, so a network failure never blocks a move.
* A {{post}} hook commits the item's files and succeeds when there is nothing to commit, as in Jira mode where a move may change no file.
* Pushing is shown as an optional extra.

TCW's own repository adopting this example belongs to TCW-76.

h1. Who owns the rest

* *Capability records* under {{docs/capabilities/}} change with the code that changes them: each of TCW-69 to TCW-73 and TCW-77 updates the records for what it changes, removes or adds.
* *Release notes and changelog entries:* each change keeps its own {{upcoming/}} file, named by the item's folder name, never the full slug, since the slash would break the path. TCW-76 applies this rule to TCW's own documentation entries.
