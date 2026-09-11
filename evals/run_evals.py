"""Spawn each eval case in each of its arms, and capture what happened.

One case × one arm is one run: seed a fresh fixture at the right variant, invoke
the harness with the fixture as its working directory, capture the transcript and
the timing, and leave the mutated fixture for `grade.py` to read.

**Which contrast applies is read from the case, not remembered.** Axis A arms are
the *fixture variant* (`customized` against `control`) and both hold the skill,
because axis A asks whether a project's bound instructions reach the agent. Axis
B arms are the *plugin toggle* against one fixture, because axis B asks what
holding the skill adds.

Three things here were settled by probe rather than by argument, and each
replaces something the plan's first draft had wrong:

* **The plugin comes from this checkout**, via `--plugin-dir`. Enabling
  `tcw@tcw` instead loads `~/.claude/plugins/marketplaces/tcw`, which is a
  different commit with `autoUpdate: true` — so the arm could shift underneath a
  sequential run, and no refinement would be visible until it was pushed.
* **The isolation map is the union of every settings file**, not one of them.
  Plugin enablement is split between the user's file and the project's. Reading
  either alone leaks.
* **Isolation is asserted from the `init` event**, which carries `plugins` and
  `skills` as structured fields, rather than by asking a model to report on
  itself.

Results land in a run directory outside the repository. Measurements are
disposable; the instrument is not.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from evals.seed_fixture import seed

REPO = Path(__file__).resolve().parent.parent
EVALS = Path(__file__).with_name("evals.json")

# Every settings file that can carry `enabledPlugins`, most general first. The
# union of their keys is what has to be forced false; the plan's first draft said
# "the settings file", singular, and either one alone leaks into both arms.
SETTINGS_FILES = (
    Path.home() / ".claude/settings.json",
    REPO / ".claude/settings.json",
    REPO / ".claude/settings.local.json",
)

# Axis A cases produce one artifact; axis B cases walk several lifecycle stages.
MAX_TURNS = {"A": 30, "B": 60}


def load_cases() -> list[dict]:
    return json.loads(EVALS.read_text(encoding="utf-8"))["cases"]


def isolation_map() -> dict[str, bool]:
    """Every known plugin key, forced false.

    Derived rather than hardcoded, so a newly installed plugin cannot leak into a
    future run. `tcw@tcw` is forced false too: the treatment arm gets the plugin
    from `--plugin-dir`, pointed at this checkout.
    """
    keys: set[str] = set()
    for path in SETTINGS_FILES:
        try:
            keys.update(json.loads(path.read_text()).get("enabledPlugins", {}))
        except (OSError, json.JSONDecodeError):
            continue
    return {key: False for key in sorted(keys)}


def prompt_for(case: dict, manifest: dict | None) -> str:
    """The case's prompt with `{item}` resolved to a real slug.

    The slug carries today's date and is minted by the CLI, so it cannot be
    written into `evals.json`. A case names *which* fixture item it addresses and
    the manifest says what that item ended up called.
    """
    text = case["prompt"]
    if "{item}" not in text:
        return text
    if manifest is None:
        return text.replace("{item}", "<slug, resolved after seeding>")
    key = case.get("item")
    slug = (manifest["items"][key] if key
            else manifest["stage_items"][case["stage"]])
    return text.replace("{item}", slug)


def command(case: dict, arm: str, settings_path: Path,
            manifest: dict | None = None) -> list[str]:
    """The full invocation for one case in one arm."""
    argv = ["claude", "-p",
            "--settings", str(settings_path),
            "--permission-mode", "acceptEdits",
            "--max-turns", str(MAX_TURNS[case["axis"]]),
            "--output-format", "stream-json", "--verbose"]
    # Axis A holds the skill in both arms; only axis B's baseline drops it.
    if not (case["axis"] == "B" and arm == "no-skill"):
        argv += ["--plugin-dir", str(REPO)]
    argv.append(prompt_for(case, manifest))
    return argv


def variant_for(case: dict, arm: str) -> bool:
    """Whether this run's fixture is the customized one.

    Axis A's arms *are* the variants. Axis B toggles the plugin instead and runs
    against the customized node in both arms, so its two arms differ only by the
    thing axis B is measuring.
    """
    return arm == "customized" if case["axis"] == "A" else True


def read_init(transcript: Path) -> dict:
    """The `init` event, which carries what was actually loaded."""
    for line in transcript.read_text().splitlines():
        event = json.loads(line)
        if event.get("subtype") == "init":
            return event
    return {}


def check_isolation(case: dict, arm: str, init: dict) -> list[str]:
    """Complaints about what the harness loaded. Empty means clean.

    Asserted rather than trusted: a silently-merged settings file would make
    every number wrong in the same direction, which is the failure a human
    reading a pass rate could never spot.
    """
    problems = []
    plugins = init.get("plugins") or []
    wants_plugin = not (case["axis"] == "B" and arm == "no-skill")

    if wants_plugin:
        paths = [p.get("path") for p in plugins]
        if len(plugins) != 1 or paths != [str(REPO)]:
            problems.append(
                f"expected exactly this checkout as the only plugin, got {paths}")
    elif plugins:
        problems.append(f"the baseline arm loaded plugins: "
                        f"{[p.get('name') for p in plugins]}")
    return problems


def run_one(case: dict, arm: str, out: Path) -> dict:
    """Seed, spawn, capture. Returns this run's entry for `benchmark.json`."""
    out.mkdir(parents=True, exist_ok=True)
    fixture = out / "fixture"
    manifest = seed(fixture, customized=variant_for(case, arm))

    settings_path = out / "settings.json"
    settings_path.write_text(json.dumps({"enabledPlugins": isolation_map()}))

    argv = command(case, arm, settings_path, manifest)
    transcript = out / "transcript.jsonl"
    started = time.monotonic()
    with transcript.open("w") as stream:
        proc = subprocess.run(argv, cwd=str(fixture), stdout=stream,
                              stderr=subprocess.PIPE, text=True,
                              stdin=subprocess.DEVNULL)
    elapsed = time.monotonic() - started

    result = {}
    for line in transcript.read_text().splitlines():
        event = json.loads(line)
        if event.get("type") == "result":
            result = event

    init = read_init(transcript)
    entry = {
        "case": case["id"],
        "axis": case["axis"],
        "arm": arm,
        "exit_status": proc.returncode,
        "wall_seconds": round(elapsed, 2),
        "duration_ms": result.get("duration_ms"),
        "cost_usd": result.get("total_cost_usd"),
        "num_turns": result.get("num_turns"),
        # A budget limit and a skill defect are different findings. Conflating
        # them reads the first as the second, so capped runs leave the pass-rate
        # denominator entirely.
        "capped": result.get("num_turns") is not None
                  and result["num_turns"] >= MAX_TURNS[case["axis"]],
        "fixture": str(fixture),
        "transcript": str(transcript),
        "prompt": prompt_for(case, manifest),
        "nonces": manifest["nonces"],
        "stage_items": manifest["stage_items"],
        "plugin_version": (init.get("plugins") or [{}])[0].get("version"),
        "isolation_problems": check_isolation(case, arm, init),
    }
    (out / "timing.json").write_text(json.dumps(entry, indent=1) + "\n")
    if proc.stderr:
        (out / "stderr.txt").write_text(proc.stderr)
    return entry


def aggregate(entries: list[dict]) -> dict:
    """Per-arm totals, with capped runs held out of the denominator.

    One run per case means no meaningful spread, so this reports raw counts
    rather than a variance field that would mean nothing.
    """
    arms: dict[str, dict] = {}
    for entry in entries:
        arm = arms.setdefault(entry["arm"], {
            "runs": 0, "capped": 0, "failed": 0,
            "cost_usd": 0.0, "wall_seconds": 0.0, "turns": 0})
        arm["runs"] += 1
        arm["capped"] += bool(entry["capped"])
        arm["failed"] += entry["exit_status"] != 0
        arm["cost_usd"] += entry.get("cost_usd") or 0.0
        arm["wall_seconds"] += entry.get("wall_seconds") or 0.0
        arm["turns"] += entry.get("num_turns") or 0
    for arm in arms.values():
        arm["graded"] = arm["runs"] - arm["capped"]
        arm["cost_usd"] = round(arm["cost_usd"], 4)
        arm["wall_seconds"] = round(arm["wall_seconds"], 2)
    return {"arms": arms, "runs": entries,
            "note": "One run per case: raw counts, no variance. Capped runs are "
                    "excluded from `graded` and are a separate finding from a "
                    "failure."}


def select(cases: list[dict], axis: str | None, case_ids: list[str] | None
           ) -> list[dict]:
    chosen = cases
    if axis:
        chosen = [c for c in chosen if c["axis"].lower() == axis.lower()]
    if case_ids:
        wanted = {c.upper() for c in case_ids}
        chosen = [c for c in chosen if c["id"].upper() in wanted]
    return chosen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--axis", choices=["a", "b", "A", "B"])
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--out", type=Path,
                        help="run directory (default: ./eval-runs/iteration-1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print each arm's command line and fixture path, "
                             "and spawn nothing")
    args = parser.parse_args(argv)

    chosen = select(load_cases(), args.axis, args.cases)
    if not chosen:
        print("no cases matched", file=sys.stderr)
        return 1

    out_root = args.out or Path("eval-runs/iteration-1")

    if args.dry_run:
        settings = out_root / "<case>/<arm>/settings.json"
        print(f"isolation map: {len(isolation_map())} plugin keys, all false")
        for key in isolation_map():
            print(f"  {key}: false")
        for case in chosen:
            for arm in case["arms"]:
                out = out_root / case["id"] / arm
                print(f"\n{case['id']} [{arm}]  axis {case['axis']}  "
                      f"fixture: {'customized' if variant_for(case, arm) else 'control'}")
                print(f"  cwd:     {out / 'fixture'}")
                print(f"  command: {' '.join(command(case, arm, settings))}")
        return 0

    if not shutil.which("claude"):
        print("run_evals: `claude` is not on PATH", file=sys.stderr)
        return 1

    entries = []
    for case in chosen:
        for arm in case["arms"]:
            entry = run_one(case, arm, out_root / case["id"] / arm)
            entries.append(entry)
            flag = " CAPPED" if entry["capped"] else ""
            problems = entry["isolation_problems"]
            print(f"{case['id']} [{arm}] exit={entry['exit_status']} "
                  f"turns={entry['num_turns']}{flag}"
                  + (f" ISOLATION: {problems}" if problems else ""))

    benchmark = out_root / "benchmark.json"
    benchmark.write_text(json.dumps(aggregate(entries), indent=1) + "\n")
    print(f"\nwrote {benchmark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
