Users can create and edit Taxonomy entries, Capabilities, Work items, lifecycle
artifacts, and bounded sidecars in the local web app. Structured reference
fields provide accessible live search over the objects already loaded by the
editor while preserving canonical identifiers and free-form entry. Every saved
object is immediately checked with TCW's standard validation rules, with any
findings shown as post-save warnings. A save the store refuses — editing a
project that is not in a Git repository, say — comes back as that refusal in
plain words, and nothing is written.

A capability's reference-bearing fields are the exception to the post-save
rule: one that does not resolve is refused **at** save rather than reported
after it, in the same words `tcw capabilities check` uses. Creating a
capability with such a field leaves no capability behind — the create and its
fields are one write, so a rejected create is not half-made. Post-save warnings
remain the rule for everything else.

A sidecar a command writes rather than a person — `rollup.md`, produced by
`tcw work reconcile` — is listed and labelled generated, and offers no edit
control. The app declines to take an edit it knows the next run of that command
would discard.

The Work detail presents Initial Request, Spec, and Implementation Plan as
first-class tabs. Present documents render and can be edited without leaving
the browser; missing later-stage documents remain visible as not-yet-present
tabs so lifecycle progress is clear.

The complete dialog mirrors the CLI's closeout gates. Choosing `done` shows the
Definition-of-Done checklist and the capabilities-reconciliation reminder;
choosing a non-`done` resolution replaces both with a discard warning and
relabels the action, because a discarded item is closed without shipping and
those gates do not apply to it.

When a work item's plan declares stage documents, users can inspect their
metadata and dependencies and create, edit, delete, or open each declared
document individually with revision-conflict protection.
