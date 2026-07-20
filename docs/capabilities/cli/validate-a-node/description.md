As a user, I run `tcw validate [path]` to validate the current registered project
graph plus YAML, `tcw://` links, and bounded component stores. Graph validation
always runs even when `path` narrows component checks. Missing or invalid IDs,
malformed registrations, missing targets, mismatched keys, nonreciprocal edges,
cycles, legacy inheritance maps, and unreachable inheritance targets fail
closed with migration guidance.
