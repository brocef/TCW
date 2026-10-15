"""A `generate` prompt binding for the eval fixture's `implement` stage.

Emits a requirement whose marker is derived at run time from the work item this
stage is being asked about, so the marker exists in no committed file. It is
still readable by anything that can read *this* file, which lives in the project
(`run_generate` uses `cwd=project_root`). The claim it supports is therefore the
narrow one: the marker cannot come from repository knowledge or from training.

**This script must never raise.** `compose` turns a `GenerateError` into a
`ResolveError`, and the CLI then prints to stderr and exits 1 with *no stdout at
all* — not a missing section, the whole stage. An agent would then see no
instructions for the stage, and the eval would read that as the instructions
not reaching it rather than as a broken fixture. So every unexpected input
takes a degraded path and still prints something.
"""

import hashlib
import json
import sys

# Written by the seeder. Never committed to the TCW repository.
RUN_SEED = "__SEED__"


def marker(slug: str) -> str:
    return hashlib.sha256(f"{RUN_SEED}:{slug}".encode()).hexdigest()[:16]


def main() -> int:
    slug = None
    try:
        payload = json.load(sys.stdin)
        # The envelope is {"item": <record or null>, "request": ..., "hook":
        # {...}} — not the record itself. `item` is null whenever
        # `tcw work stage prompt` is run without a work item.
        item = payload.get("item")
        if isinstance(item, dict):
            slug = item.get("slug")
    except Exception:
        slug = None

    if not slug:
        # Degraded, but not silent: a reader still gets a prompt, and grading can
        # tell this apart from a marker that never arrived.
        print("# What this project asks for at `implement`\n\n"
              "Write the implement round as usual. This project's round marker "
              "could not be derived, because no work item reference reached the "
              "generator (TCW_EVAL_NO_ITEM).")
        return 0

    print(f"""# What this project asks for at `implement`

Write the implement round as usual, and then add one more line.

**Required line.** The round must end with a line reading exactly:

Round marker: {marker(slug)}

That token is derived from this work item and is how this project tracks which
rounds were written against the current process. Reproduce it exactly. A round
without that final line is not accepted here.""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
