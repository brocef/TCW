#!/usr/bin/env python3
"""Stage `pre` check: refuse a move until a stage's document is written.

Bound in `tcw-config.yaml` to the `plan` stage (`spec`) and the `implement`
stage (`spec` and `plan`), so `tcw work advance` refuses to move an item into
plan while its spec is unwritten, and into implement while its spec or plan
is.

It asks `tcw work path "$TCW_SLUG" <stage>` where the document lives rather
than composing a store path. That is the litmus test applied to the check
itself: the path the CLI names is the abstract answer to "where is this
item's spec", and a check that wrote out
`docs/work/<folder>/spec/spec.md` would hardcode one store's layout.

Fails closed. An unset `TCW_SLUG`, a `tcw` that cannot be run, or a `tcw`
that exits non-zero all exit 1, because a check that cannot tell you the
answer must not be read as a pass. A document that exists but holds only
white space counts as unwritten.
"""

import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <stage>", file=sys.stderr)
        return 2
    stage = argv[1]

    slug = os.environ.get("TCW_SLUG")
    if not slug:
        print("require_artifact: TCW_SLUG is not set; this runs as a tcw "
              "stage hook, not on its own", file=sys.stderr)
        return 1

    try:
        out = subprocess.run(["tcw", "work", "path", slug, stage],
                             capture_output=True, text=True, timeout=30,
                             stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"require_artifact: could not run tcw: {e}", file=sys.stderr)
        return 1
    if out.returncode != 0:
        print(f"require_artifact: tcw work path {slug} {stage} failed: "
              f"{out.stderr.strip()}", file=sys.stderr)
        return 1

    lines = out.stdout.splitlines()
    if len(lines) != 1 or not lines[0].strip():
        print(f"require_artifact: tcw work path {slug} {stage} did not print "
              f"one path: {out.stdout!r}", file=sys.stderr)
        return 1
    document = Path(lines[0].strip())

    try:
        text = document.read_text(encoding="utf-8")
    except FileNotFoundError:
        text = ""
    except OSError as e:
        print(f"require_artifact: cannot read {document}: {e}", file=sys.stderr)
        return 1
    if not text.strip():
        print(f"require_artifact: {slug} has no {stage} document "
              f"({document}); write it before this stage", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
