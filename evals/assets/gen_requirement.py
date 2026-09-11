"""A `generate` prompt binding for the eval fixture's `implement` stage.

Emits a requirement whose marker is derived at run time from the work item this
stage is being asked about, so the marker exists in no committed file. It is
still readable by anything that can read *this* file, which lives in the node
(`run_generate` uses `cwd=node_root`). The claim it supports is therefore the
narrow one: the marker cannot come from repository knowledge or from training.

**This script must never raise.** `_resolve_one` turns a `GenerateError` into a
`ResolveError`, and the CLI then prints to stderr and exits 1 with *no stdout at
all* — not a missing section, the whole stage. Under the composing skill's
`|| true` that is silent, and the eval would read it as failure mode I1, which
is the exact mode the harness exists to detect. So every unexpected input takes
a degraded path and still prints something.
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
        # The envelope is {"item": <projection or null>, "hook": {...}} — not the
        # projection itself. `item` is null whenever the verb is called without a
        # work item reference, which every per-stage skill documents.
        item = payload.get("item")
        if isinstance(item, dict):
            slug = item.get("slug")
    except Exception:
        slug = None

    if not slug:
        # Degraded, but not silent: a reader still gets a prompt, and grading can
        # tell this apart from a marker that never arrived.
        print("# What this project asks for at `implement`\n\n"
              "Record the outcome as usual. This project's outcome marker could "
              "not be derived, because no work item reference reached the "
              "generator (TCW_EVAL_NO_ITEM).")
        return 0

    print(f"""# What this project asks for at `implement`

Record the outcome as usual, and then add one more line.

**Required line.** The outcome must end with a line reading exactly:

Outcome marker: {marker(slug)}

That token is derived from this work item and is how this project tracks which
outcomes were written against the current process. Reproduce it exactly. An
outcome without that final line is not accepted here.""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
