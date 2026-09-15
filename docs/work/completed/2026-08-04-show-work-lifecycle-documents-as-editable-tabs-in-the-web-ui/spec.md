# Specification: first-class lifecycle document tabs

## Capability changes

- Changed: `web/editing` — work-item planning documents are directly viewable
  and editable from a tabbed work content area, without opening an external
  Markdown editor.

## Problem

The work-detail view renders the work item's body (the initial request) directly
in the page, but filters `initial-request` out of the artifact controls and
renders every other present lifecycle artifact as an external-open button plus
a separate edit icon
(`web/client/src/ui/content-views.tsx:369-408`,
`web/client/src/ui/content-views.tsx:562`). As a result, the specification and
implementation plan are less prominent than the initial request and viewing
them takes the user out of the web app.

The server and client already expose bounded, revision-bearing reads and writes
for lifecycle artifacts (`tcw/serve/__init__.py:485-515`,
`tcw/serve/__init__.py:1106-1141`). The client also already opens those
resources in its Markdown editor with conflict tracking
(`web/client/src/ui/app.tsx:456-507`). The missing behavior is therefore a
first-class viewing and navigation surface in the work detail, not a new store
operation or lifecycle concept.

## Goals

- Make Initial Request, Spec, and Implementation Plan peer views in the work
  content area.
- Keep the three planning documents visible and understandable even when a
  later-stage document is not present yet.
- Let users edit each present document through the existing in-web Markdown
  editing flow.
- Preserve existing revision-conflict handling, validation warnings, and the
  storage-abstracted artifact interface.
- Keep Initial Request selected whenever a different work item is opened.

## Non-goals

- Adding or replacing the Markdown editor itself; that remains the scope of
  `2026-07-02-add-a-vendored-rich-markdown-editor-to-the-local-web-app`.
- Changing lifecycle stages, artifact names, artifact persistence, or the
  `WorkStore` interface.
- Adding first-class tabs for outcome, verification, rework, post-mortem,
  staged-plan documents, or sidecars.
- Allowing a missing Spec or Implementation Plan to be created from the tab.
- Removing external-open support for lifecycle artifacts at the API level.

## Design

The work content area will use an accessible tab interface with these labels
and this order:

1. Initial Request
2. Spec
3. Implementation Plan

Selecting a present document displays its rendered Markdown in the detail pane
and provides an Edit action. Initial Request uses the existing work-item edit
flow; Spec and Implementation Plan use the existing lifecycle-artifact editor,
including revision checks and post-save validation warnings.

All three tabs remain visible for every work item. When Spec or Implementation
Plan is absent, its panel shows a clear not-yet-present state and does not offer
an Edit action. This makes lifecycle progress legible without introducing an
unreviewed artifact-creation workflow.

Initial Request is selected by default. Selecting another work item resets the
tab selection to Initial Request so the new item's request is never hidden by
the prior item's local UI state.

The current row of generic artifact open/edit controls will no longer duplicate
Initial Request, Spec, or Implementation Plan. Controls for other present
lifecycle artifacts remain available as they are today. Plan-stage documents
and sidecars retain their existing dedicated sections.

The implementation will consume the bounded artifact summaries and existing
GET/PUT routes already exposed by the abstract work-resource vocabulary. No
filesystem locator or path becomes part of the web UI contract.

## Acceptance criteria

- A work detail shows exactly the tabs Initial Request, Spec, and Implementation
  Plan in that order.
- Initial Request is selected when a work item first opens and whenever the user
  selects a different work item.
- Selecting each present tab renders that document's Markdown inside the work
  detail without launching an external application.
- Each present tab offers an Edit action that enters the existing in-web editor
  for the selected document.
- Saving Spec or Implementation Plan retains stale-revision conflict handling
  and surfaces the server's validation warnings in the same way as existing
  lifecycle-artifact edits.
- A missing Spec or Implementation Plan keeps its tab visible, displays a clear
  not-yet-present state, and exposes no Edit action.
- Initial Request, Spec, and Implementation Plan are not duplicated in the
  generic artifact action row; other present lifecycle artifacts remain
  reachable there.
- Existing plan-stage and sidecar presentation and editing continue to work.
- Component tests cover tab labels/order, initial selection, switching among
  present documents, missing-document states, edit routing, and reset behavior
  on work-item selection.
- The maintained web test, typecheck, lint, build, and deterministic-build
  checks pass.

## Risks

- Loading tab content on demand introduces a transient loading/error state that
  must not display stale content from the previously selected item or tab.
- Keeping tab state inside a reused detail component could carry selection
  across work items unless reset behavior is explicit and tested.
- Initial Request is represented both as the work item's core body and as a
  bounded artifact; the UI must preserve the existing core edit path while
  treating all three documents consistently as content views.
- Removing the visible external-open controls for the three planning documents
  changes an existing convenience. The in-web rendering/editing must be fully
  reachable before those controls are removed.
