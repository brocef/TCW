# Recursive validation by default

## Capability changes

- Change `cli/validate-a-node` so an unqualified `tcw validate` validates the
  active TCW project and every registered descendant project recursively.
- Add `--no-recurse` as the explicit active-project-only mode.

## Problem

The current CLI finds the active node and invokes validation only for that node
(`tcw/cli.py:75-94`). Although validation checks the registered project graph,
its content scan roots and component checks are derived from one `node_root`
(`tcw/validate.py:114-163`). A clean result can therefore leave invalid content
in registered child projects undiscovered.

The public documentation likewise describes bare `tcw validate` as checking
only "the whole node" (`README.md:367-380`), and the standing capability promises
validation of the current registered graph plus the active node's bounded stores
(`docs/capabilities/cli/validate-a-node/description.md:1-6`).

## Goals

- Make bare `tcw validate` cover the active project and all registered
  descendants, at every depth.
- Preserve an easy active-project-only validation mode through `--no-recurse`.
- Report failures from any selected project and return a non-zero exit status if
  any selected project fails validation.
- Preserve the validation rules applied within each project.

## Non-goals

- Validating ancestors or siblings of the active project.
- Changing taxonomy, capability, work, YAML, or `tcw://` validation rules.
- Changing object-scoped validation used internally by the web application.
- Replacing registered-project traversal with filesystem discovery.
- Removing the existing optional path selector.

## Design

The top-level CLI command will select project roots before invoking the existing
single-project validation operation. By default, the selection is the active
project followed by all descendants declared in its validated project registry.
The registry already exposes recursive descendants independently of filesystem
layout (`tcw/store/project.py:150-181`); filesystem locators remain an adapter
detail.

`--no-recurse` limits root selection to the active project. An explicit `path`
continues to mean a bounded validation of that path in the active project and
does not recurse, preserving the current narrowing contract described by the
parser (`tcw/cli.py:122-126`) and validation selector (`tcw/validate.py:62-83`).
The flag may be accepted alongside a path as an explicit but redundant scope
choice.

Each selected project is validated with the existing per-project behavior.
Diagnostics must identify the project that produced them when more than one
project is selected, and success is printed only after every selected project
passes. Invalid graph topology continues to fail closed before descendant
content validation begins.

Traversal must use the registered project graph rather than the existing
`child_nodes()` helper: that helper intentionally filters to projects with a
work store (`tcw/store/fs.py:134-161`), while validation applies to any TCW
project and any initialized component subset.

## Acceptance criteria

- With a valid active project and nested registered descendants, bare
  `tcw validate` validates every project exactly once and exits `0` only when all
  are clean.
- A validation problem that exists only in a direct or nested descendant is
  reported with enough project context to locate it, and the command exits `1`.
- `tcw validate --no-recurse` validates only the active project and ignores
  descendant content problems.
- `tcw validate <path>` retains its existing active-project bounded scan and
  component-check behavior without validating descendants.
- Registered descendant projects without a work store are still included when
  they contain another TCW component.
- Malformed, nonreciprocal, cyclic, or otherwise invalid registered-project
  topology still fails closed with the existing graph diagnostics.
- CLI help, README examples, release notes, developer changelog, and the
  `cli/validate-a-node` capability describe the new default and opt-out flag.
- Existing single-project validation and object-scoped web validation tests
  continue to pass.

## Risks

- Existing automation may become slower or begin failing because bare
  validation now intentionally includes descendant projects; `--no-recurse`
  provides the compatibility escape hatch.
- Reusing work-specific descendant helpers would silently omit valid
  taxonomy-only or capabilities-only projects.
- Unqualified diagnostics from multiple projects could be ambiguous when files
  have matching relative paths.
- Applying an active-project path selector to descendants would be ambiguous;
  keeping explicit path validation local avoids inventing cross-project path
  semantics.
