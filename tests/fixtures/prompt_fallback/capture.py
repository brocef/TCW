"""Capture `tcw work stage` output on a node that configures nothing.

Run **before** the documentation-entry substitution is built, and the recorded
bytes become the back-compat tripwire for it: a project with no
`work.documentation` must see byte-identical stage instructions afterwards.

    python tests/fixtures/prompt_fallback/capture.py <outdir>

Captured before, this is evidence. Captured after, it would only record what the
code now does — which is why `tests/fixtures/lifecycle_baseline/capture.py`, the
script this is modelled on, says the same thing in its own docstring.

Every stage is exercised at a status where it is **legal**, because
`tcw work stage` refuses out-of-status stages and a refusal message pins nothing
about prompt text. The item walks backlog → active → review, and each stage is
captured at the point it becomes legal.
"""

import json
import subprocess
import sys
from pathlib import Path

# (stage id, the status the item must be in for that stage to be legal)
WALK = [
    ("request", "backlog"),
    ("spec", "backlog"),
    ("plan", "backlog"),
    ("implement", "active"),
    ("verify", "review"),
    ("postmortem", "review"),
]


def _run(root: Path, *args: str) -> dict:
    r = subprocess.run(["tcw", *args], cwd=str(root), capture_output=True,
                       text=True, stdin=subprocess.DEVNULL)
    return {"argv": list(args), "returncode": r.returncode,
            "stdout": r.stdout, "stderr": r.stderr}


def build_node(root: Path) -> str:
    """A node that configures nothing: no work.lifecycle, no work.documentation."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    subprocess.run(["tcw", "init", "--id", "fallback", "work"], cwd=str(root),
                   capture_output=True, check=True, stdin=subprocess.DEVNULL)
    r = subprocess.run(["tcw", "work", "new", "Baseline item"], cwd=str(root),
                       capture_output=True, text=True, check=True,
                       stdin=subprocess.DEVNULL)
    return r.stdout.strip()


# The transition that reaches each status from the one before it.
INTO = {"active": "start", "review": "submit"}


def capture_one(root: Path, slug: str) -> list[dict]:
    out = []
    current = "backlog"
    for stage, status in WALK:
        if status != current:                 # only on a change: `verify` and
            subprocess.run(                   # `postmortem` share `review`, and
                ["tcw", "work", INTO[status], slug],   # review → review is not
                cwd=str(root), capture_output=True,    # a legal transition
                check=True, stdin=subprocess.DEVNULL)
            current = status
        out.append(_run(root, "work", "stage", stage, slug))
    return out


def main(outdir: Path, scratch: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    root = scratch / "unconfigured"
    slug = build_node(root)
    (outdir / "unconfigured.json").write_text(
        json.dumps(capture_one(root, slug), indent=2) + "\n")
    print(f"captured unconfigured ({len(WALK)} stages)")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    scratch = Path(sys.argv[2]) if len(sys.argv) > 2 else out / "_scratch"
    main(out, scratch)
