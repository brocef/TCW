"""Capture `tcw work stage prompt` output on a project that configures nothing.

Run **before** a change that must not move the prompt text, and the recorded
bytes become its tripwire: a project with no `work.documentation` and no
prompt bindings must see byte-identical stage instructions afterwards.

    python tests/fixtures/prompt_fallback/capture.py <outdir>

Captured before, this is evidence. Captured after, it would only record what the
code now does.

**Re-capture only when a release intends the text to move, and say which one.**
The 2.x history of this file (six stages, walked through 2.x statuses) ended
with TCW-74, which rewrote every prompt for the 3.0 stages and added the
generated footer, so the file was re-captured from the 3.0 output in a commit
of its own, after the text was final and before any later change to it.

In 3.0 `stage prompt` composes the same text whatever stage the item is at, so
the capture does not move the item: it creates one and reads every stage's
prompt for it (inbox without a reference, since inbox takes none).

**Capture with the interpreter whose `tcw` you mean to pin.** This script
shells out to whatever `tcw` is first on `PATH`, and an editable install is a
single shared resource that a sibling worktree can own. Use a throwaway venv
(`python -m venv --system-site-packages`, then `pip install -e <checkout>
--no-deps`) with its `bin` first on `PATH`, and check `python -c "import tcw;
print(tcw.__file__)"` immediately before capturing.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Every stage with a built-in prompt, in the stage table's order.
STAGES = ["inbox", "request", "spec", "plan", "implement", "review", "qa",
          "postmortem"]

# The item's slug carries the date it was created, and the prompt quotes it
# back. Recording it verbatim would make these bytes expire at midnight, so
# every occurrence is normalized to this token on the way in, and the replay
# normalizes the same way before comparing.
SLUG_TOKEN = "<slug>"


def _env(home: Path) -> dict:
    """No personal configuration from the person running the capture."""
    return {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / "xdg"),
            "TCW_NO_PERSONAL_CONFIG": "1"}


def _run(root: Path, slug: str, env: dict, *args: str) -> dict:
    r = subprocess.run(["tcw", *args], cwd=str(root), capture_output=True,
                       text=True, stdin=subprocess.DEVNULL, env=env)

    def norm(t: str) -> str:
        return t.replace(slug, SLUG_TOKEN)
    return {"argv": [norm(a) for a in args], "returncode": r.returncode,
            "stdout": norm(r.stdout), "stderr": norm(r.stderr)}


def build_project(root: Path, env: dict) -> str:
    """A project that configures nothing beyond `tcw init`, with one item."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["tcw", "init", "--id", "fallback", "work"], cwd=str(root),
                   capture_output=True, check=True, stdin=subprocess.DEVNULL,
                   env=env)
    r = subprocess.run(["tcw", "work", "new", "Baseline item"], cwd=str(root),
                       capture_output=True, text=True, check=True,
                       stdin=subprocess.DEVNULL, env=env)
    return r.stdout.strip()


def capture_one(root: Path, slug: str, env: dict) -> list[dict]:
    out = []
    for stage in STAGES:
        reference = [] if stage == "inbox" else [slug]
        out.append(_run(root, slug, env, "work", "stage", "prompt", stage,
                        *reference))
    return out


def main(outdir: Path, scratch: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    env = _env(scratch / "home")
    root = scratch / "unconfigured"
    slug = build_project(root, env)
    (outdir / "unconfigured.json").write_text(
        json.dumps(capture_one(root, slug, env), indent=2) + "\n")
    print(f"captured unconfigured ({len(STAGES)} stages)")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    scratch = Path(sys.argv[2]) if len(sys.argv) > 2 else out / "_scratch"
    main(out, scratch)
