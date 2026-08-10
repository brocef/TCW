# Repair invalid Playwright taxonomy fixture

## Capability changes

None. This repair changes test setup only.

## Problem

The reference-search end-to-end scenario creates 24 taxonomy entries as
Features without vocabulary references (`web/e2e/parity.spec.ts:335-343`). The
taxonomy contract requires every Feature to reference at least one Vocabulary
(`tcw/store/fs.py:1100-1108`), so the first request returns 422 and the serial
suite skips all later scenarios.

## Goals

- Make the fixture's scrolling entries valid under the current taxonomy model.
- Align stale Playwright expectations with the current Review status and tree
  item interaction exposed after the serial suite advances.
- Preserve the reference-search scenario's intended result volume and matching
  behavior.
- Run the complete Python, web unit, and Playwright suites plus ESLint.

## Non-goals

- Change taxonomy validation or API behavior.
- Change taxonomy validation, API behavior, or unrelated product behavior.

## Design

Supply the existing `react-vocabulary` reference when creating each generated
Feature, matching the valid Feature created immediately afterward. Keep the
generated names, slugs, kind, count, and assertions unchanged.

Refresh the status-filter snapshot so it includes the registered Review status,
and click the tab-reset target through its `treeitem` role, matching the current
DOM and the suite's established tree interaction.

The sibling-defect sweep covers stale expected artifacts subsequently exposed
in the same serial end-to-end file. Each correction must be grounded in current
model or DOM evidence rather than accepting new output blindly.

## Acceptance criteria

- All 24 generated Feature creation requests succeed.
- All 13 Playwright scenarios execute and pass.
- The complete Python and web unit suites pass.
- ESLint passes with zero warnings.

## Risks

- The serial Playwright suite can hide later failures after the first failure;
  acceptance therefore requires all 13 scenarios to execute.
