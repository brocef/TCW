# Make tcw validate recursive by default

## Product changes

Change `tcw validate` so its default scope includes the active TCW project and
all child TCW roots recursively. Add `--no-recurse` for callers that want to
validate only the active TCW project.

## Technical changes

Preserve the existing validation checks while changing how the command selects
the TCW project roots to validate.

## Meta changes

Keep this work in planning through `plan.md`; do not start or implement it until
the plan has been reviewed.

## Notes

The requester supplied the desired command behavior directly. No separate
reference material was provided with the request; repository code and existing
CLI documentation are the sources for specification research.

