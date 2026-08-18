#!/usr/bin/env python3
"""Stage `pre` check: refuse a stage until a named lifecycle artifact exists.

Bound to the `plan` stage in `tcw-config.yaml`, so `tcw work stage plan <slug>`
refuses on an item whose spec has not been written.

It asks `tcw work show --json` rather than composing a store path. That is the
litmus test applied to the check itself: the artifact map is the abstract answer
to "does this document exist", and a check doing
`$TCW_NODE_ROOT/docs/work/<status>/<slug>/spec.md` would hardcode the filesystem
layout — the exact thing `tcw work reconcile` was fixed to stop doing in 1.0.0.

Fails closed. An unset `TCW_SLUG`, a missing `tcw`, or unreadable JSON all exit
non-zero, because a check that cannot tell you the answer must not be read as a
pass.
"""

import json
import os
import subprocess
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <artifact-name>", file=sys.stderr)
        return 2
    artifact = argv[1]

    slug = os.environ.get("TCW_SLUG")
    if not slug:
        print("require_artifact: TCW_SLUG is not set; this runs as a tcw "
              "lifecycle hook, not on its own", file=sys.stderr)
        return 1

    try:
        out = subprocess.run(["tcw", "work", "show", slug, "--json"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"require_artifact: could not run tcw: {e}", file=sys.stderr)
        return 1
    if out.returncode != 0:
        print(f"require_artifact: tcw work show {slug} failed: "
              f"{out.stderr.strip()}", file=sys.stderr)
        return 1

    try:
        artifacts = json.loads(out.stdout)["artifacts"]
    except (ValueError, KeyError, TypeError) as e:
        print(f"require_artifact: unreadable item document: {e}", file=sys.stderr)
        return 1

    if not artifacts.get(artifact):
        print(f"require_artifact: {slug} has no {artifact}; write it before "
              f"this stage", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
