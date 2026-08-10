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
- Preserve the reference-search scenario's intended result volume and matching
  behavior.
- Run the complete Python, web unit, and Playwright suites plus ESLint.

## Non-goals

- Change taxonomy validation or API behavior.
- Change product behavior or test assertions.
- Refactor unrelated end-to-end fixtures.

## Design

Create a scenario-local Vocabulary and supply its reference when creating each
generated Feature and the final `use-feature` fixture. Keep the generated names,
slugs, kind, count, and assertions unchanged. This makes the scenario valid both
in the serial suite and when selected independently.

The sibling-defect sweep is narrowed to taxonomy Feature creation in the same
end-to-end file because this failure is a fixture-contract mismatch; the only
other explicit Feature creation in that scenario already supplies a vocabulary,
although its original vocabulary came from an earlier serial scenario.

## Acceptance criteria

- All 24 generated Feature creation requests succeed.
- All 13 Playwright scenarios execute and pass.
- The complete Python and web unit suites pass.
- ESLint passes with zero warnings.

## Risks

- The serial Playwright suite can hide later failures after the first failure;
  acceptance therefore requires all 13 scenarios to execute.
