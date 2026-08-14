"""Capture `tcw work lifecycle` output for the legacy back-compat corpus.

Run **before** the parser is touched, and again after, to prove criterion 1 of
`2026-08-12-give-lifecycle-hooks-roles-kinds-and-conditions`: every config that
was valid before the roles/kinds rewrite renders byte-identically after it.

    python tests/fixtures/lifecycle_baseline/capture.py <outdir>

The corpus is one config per row of that item's back-compat table, plus this
repository's own `tcw-config.yaml` — the row nobody thought to write.
"""

import json
import subprocess
import sys
from pathlib import Path

import yaml

# One entry per row of the back-compat table. `None` means "no work.lifecycle
# key at all", which is the shape almost every real node has.
CORPUS: dict[str, object] = {
    "absent": None,
    "stage_skill": {"stages": {"spec": [{"skill": "superpowers:brainstorming"}]}},
    "stage_command": {"stages": {"spec": [{"command": "./bin/spec-help.sh"}]}},
    "stage_mixed": {"stages": {"plan": [
        {"skill": "a"}, {"command": "b"}, {"skill": "c"}]}},
    "stage_empty": {"stages": {"spec": []}},
    "transition_command": {"transitions": {"complete": {"pre": [
        {"command": "pytest -q"}]}}},
    "transition_skill": {"transitions": {"start": {"post": [
        {"skill": "notify"}]}}},
    "transition_empty": {"transitions": {"start": {"pre": [], "post": []}}},
    "timeout_set": {"timeout": 42,
                    "stages": {"implement": [{"skill": "tdd"}]}},
    "everything": {
        "timeout": 120,
        "stages": {"request": [{"skill": "x"}],
                   "spec": [{"command": "c"}, {"skill": "y"}],
                   "implement": []},
        "transitions": {"start": {"pre": [{"command": "a"}]},
                        "complete": {"pre": [{"command": "b"}],
                                     "post": [{"skill": "z"}]}},
    },
}

STAGES = ("inbox", "request", "spec", "plan", "implement", "verify", "postmortem")
TRANSITIONS = ("start", "submit", "complete", "rework", "discard")


def _run(root: Path, *args: str) -> dict:
    r = subprocess.run(["tcw", "work", "lifecycle", *args], cwd=str(root),
                       capture_output=True, text=True)
    return {"argv": list(args), "returncode": r.returncode,
            "stdout": r.stdout, "stderr": r.stderr}


def capture_one(root: Path) -> list[dict]:
    """Every rendering criterion 1 pins, for the node at `root`."""
    out = [_run(root)]
    for sid in STAGES:
        out.append(_run(root, "--stage", sid))
        out.append(_run(root, "--stage", sid, "--directive"))
    for tid in TRANSITIONS:
        out.append(_run(root, "--transition", tid))
        out.append(_run(root, "--transition", tid, "--directive"))
    out.append(_run(root, "--json"))
    return out


def build_node(root: Path, lifecycle: object) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    subprocess.run(["tcw", "work", "init", "--id", "corpus"], cwd=str(root),
                   capture_output=True, check=True)
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    if lifecycle is not None:
        cfg.setdefault("work", {})["lifecycle"] = lifecycle
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def main(outdir: Path, scratch: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for name, lifecycle in CORPUS.items():
        root = scratch / name
        build_node(root, lifecycle)
        (outdir / f"{name}.json").write_text(
            json.dumps(capture_one(root), indent=2) + "\n")
        if lifecycle is not None:
            (outdir / f"{name}.config.yaml").write_text(
                yaml.safe_dump(lifecycle, sort_keys=False))
        print(f"captured {name}")

    # This repository's own node, captured in place — the config the corpus did
    # not think of, and the one that breaks the whole session if C3 changes it.
    here = Path(__file__).resolve().parents[3]
    (outdir / "self.json").write_text(
        json.dumps(capture_one(here), indent=2) + "\n")
    print("captured self")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    scratch = Path(sys.argv[2]) if len(sys.argv) > 2 else out / "_scratch"
    main(out, scratch)
