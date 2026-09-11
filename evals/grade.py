"""Read one run directory and decide what it showed.

Two families, matching the two things a run leaves behind.

**Transcript reads** answer questions nothing else can: were both injected blocks
present and non-empty, did the gate run before the artifact was written, were the
manual fallback commands run by hand. Failure modes I1 and I2 are visible nowhere
else, so a run whose transcript was not captured cannot be graded for them.

**Fixture end-state reads** ask the node rather than walk it — `tcw work list`,
`tcw capabilities show`, `tcw validate` — so the harness measures a node rather
than a directory layout. Two reads genuinely cannot: commit ordering, and which
files a change touched. Both are properties of the fixture's version control
rather than of the store interface, and the fixture is a filesystem git
repository by construction. They stay here and never reach `tcw/`.

## Provenance, which is the point of this module

Every composing skill ends with a fenced fallback telling the reader to run
`tcw work stage prompt <stage> <item>` by hand when a block looks empty. An agent
that follows it **produces the nonce with the injection layer having done
nothing**. Reading nonce presence and block presence as independent assertions
would grade injection-failed-and-rescued identically to injection-worked, which is
exactly the wrong verdict on this item's primary question.

So every nonce verdict carries a provenance: `injected` when no manual invocation
precedes the nonce's first appearance, `fallback` when one does, and `unknown`
when the transcript cannot settle it. **`unknown` is never a pass.**

## What this module deliberately cannot say

- **Tool provenance.** Commit history cannot tell a hand-written artifact from a
  scaffolded one; identical commits come from compliant and non-compliant
  histories alike. Commit *ordering* survives, and is all that is claimed.
- **Causation for the gate reminder.** Both arms carry the bookend, so it is not
  the variable. The gate predicate says the gate ran, and nothing more.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# The two injected blocks, identified by their headings rather than by content,
# which varies per node.
BLOCK_HEADINGS = ("## How to work it", "## What this project asks for")

# What an agent running the fenced fallback by hand would type *to obtain the
# instructions*. Any of these appearing before a nonce means the text could have
# arrived without the injection layer doing anything.
#
# `tcw work stage gate` is deliberately **not** here, though the fenced fallback
# names it too. The gate is a legality check: it prints "checks passed; run `tcw
# work stage prompt ...` for the instructions" and never the instructions
# themselves, so it cannot be where a nonce came from. Including it marked every
# well-behaved run as fallback-sourced, because running the gate first is the
# behaviour case A7 exists to reward.
FALLBACK_COMMANDS = ("tcw work stage prompt",
                     "skills/tcw-work/references/lifecycle/stage-")

INJECTED = "injected"
FALLBACK = "fallback"
UNKNOWN = "unknown"


# --- reading a run ---------------------------------------------------------

def load_events(transcript: Path) -> list[dict]:
    if not transcript.is_file():
        return []
    events = []
    for line in transcript.read_text().splitlines():
        if line.strip():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _texts(events: list[dict]) -> list[str]:
    """Every piece of text the run produced, in order.

    Flattened from assistant messages, user messages and tool results alike: a
    nonce can appear in any of them, and their order is what provenance rests on.
    """
    out = []
    for event in events:
        message = event.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            out.append(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                for key in ("text", "content", "input"):
                    value = block.get(key)
                    if isinstance(value, str):
                        out.append(value)
                    elif isinstance(value, (dict, list)):
                        out.append(json.dumps(value))
    return out


def _first_index(texts: list[str], needle: str) -> int | None:
    for i, text in enumerate(texts):
        if needle in text:
            return i
    return None


def provenance(events: list[dict], nonce: str) -> str:
    """Whether `nonce` reached the run by injection or by the manual fallback.

    A manual invocation *before* the nonce first appears means the fallback could
    have supplied it, and nothing in the transcript can rule that out. That is
    reported rather than resolved: a guess here would be the confound, not a fix
    for it.
    """
    texts = _texts(events)
    at = _first_index(texts, nonce)
    if at is None:
        return UNKNOWN
    for command in FALLBACK_COMMANDS:
        manual = _first_index(texts, command)
        if manual is not None and manual < at:
            return FALLBACK
    return INJECTED


# --- asking the node -------------------------------------------------------

def tcw(fixture: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tcw.cli", *args],
                          cwd=str(fixture), capture_output=True, text=True)


def git(fixture: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(fixture), *args],
                          capture_output=True, text=True)
    return proc.stdout


def find_artifact(fixture: Path, name: str) -> Path | None:
    matches = sorted((fixture / "docs/work").glob(f"*/*/{name}"))
    return matches[0] if matches else None


# --- the predicates --------------------------------------------------------

def _verdict(passed: bool, evidence: str, **extra) -> dict:
    """Every pass carries evidence quoted from the output. A heading with nothing
    under it is a fail, so an empty evidence string cannot pass."""
    return {"passed": bool(passed) and bool(evidence.strip()),
            "evidence": evidence, **extra}


def p_transcript_blocks_present(run, **_):
    found = {h: any(h in t for t in _texts(run["events"]))
             for h in BLOCK_HEADINGS}
    missing = [h for h, ok in found.items() if not ok]
    return _verdict(not missing,
                    f"present: {[h for h, ok in found.items() if ok]}; "
                    f"missing: {missing}")


def p_transcript_gate_before_artifact(run, artifact="", **_):
    texts = _texts(run["events"])
    gate = _first_index(texts, "tcw work stage gate")
    if gate is None:
        return _verdict(False, "no `tcw work stage gate` invocation in the run")
    written = _first_index(texts, artifact) if artifact else None
    ordered = written is None or gate < written
    return _verdict(ordered,
                    f"gate at event {gate}, artifact mention at {written}")


def p_transcript_fallback_commands_run(run, **_):
    texts = _texts(run["events"])
    ran = [c for c in FALLBACK_COMMANDS if _first_index(texts, c) is not None]
    return _verdict(bool(ran), f"fallback commands seen: {ran}")


def p_transcript_contains(run, text="", **_):
    hit = _first_index(_texts(run["events"]), text)
    return _verdict(hit is not None,
                    f"{text!r} first appears at event {hit}" if hit is not None
                    else f"{text!r} never appears")


def p_transcript_absent(run, text="", **_):
    hit = _first_index(_texts(run["events"]), text)
    return _verdict(hit is None,
                    f"{text!r} is absent" if hit is None
                    else f"{text!r} appears at event {hit}")


def p_nonce_in_artifact(run, kind="", artifact="", **_):
    """The axis A core, and the one predicate that reports provenance.

    A nonce present proves the text reached the agent *and* was acted on. It does
    not prove how it arrived, which is what `provenance` is for.
    """
    nonce = run["nonces"].get(kind)
    if not nonce:
        return _verdict(False, f"no {kind!r} nonce in the run manifest",
                        provenance=UNKNOWN)
    path = find_artifact(run["fixture"], artifact)
    if path is None:
        return _verdict(False, f"{artifact} was never written",
                        provenance=UNKNOWN)
    body = path.read_text()
    if nonce not in body:
        return _verdict(False, f"{nonce} absent from {artifact} "
                               f"({len(body)} bytes written)",
                        provenance=UNKNOWN)
    how = provenance(run["events"], nonce)
    line = next((l for l in body.splitlines() if nonce in l), "")
    return _verdict(how == INJECTED,
                    f"{nonce} in {artifact}: {line.strip()[:90]!r}",
                    provenance=how)


def p_nonce_absent_from_artifact(run, kinds=(), artifact="", **_):
    path = find_artifact(run["fixture"], artifact)
    if path is None:
        return _verdict(False, f"{artifact} was never written")
    body = path.read_text()
    leaked = [k for k in kinds if run["nonces"].get(k, "\0") in body]
    return _verdict(not leaked,
                    f"none of {list(kinds)} appear in {artifact}" if not leaked
                    else f"leaked into {artifact}: {leaked}")


def p_stage_prompt_empty(run, stage="", **_):
    slug = run["stage_items"].get(stage, "")
    proc = tcw(run["fixture"], "work", "stage", "prompt", stage, slug)
    return _verdict(proc.stdout == "",
                    f"`{stage}` resolved to {len(proc.stdout)} bytes")


def p_stage_prompt_bookended(run, stage="", **_):
    """Asserted by shape, not by byte count, which moves whenever a builtin
    prompt is edited."""
    slug = run["stage_items"].get(stage, "")
    proc = tcw(run["fixture"], "work", "stage", "prompt", stage, slug)
    marker = f"tcw work stage gate {stage}"
    return _verdict(marker in proc.stdout,
                    f"`{stage}` resolved to {len(proc.stdout)} bytes, "
                    f"gate reminder {'present' if marker in proc.stdout else 'absent'}")


def p_artifact_exists(run, artifact="", **_):
    path = find_artifact(run["fixture"], artifact)
    return _verdict(path is not None and path.read_text().strip() != "",
                    f"{artifact} at {path}" if path else f"{artifact} not found")


def p_item_status(run, item="", status="", **_):
    slug = run["items"].get(item, item)
    proc = tcw(run["fixture"], "work", "show", slug)
    line = next((l for l in proc.stdout.splitlines() if status in l), "")
    return _verdict(bool(line), line.strip() or
                    f"{slug} is not in {status}: {proc.stdout[:120]}")


def p_new_item_count(run, count=0, **_):
    proc = tcw(run["fixture"], "work", "list")
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    seeded = len(run["items"])
    actual = len(lines) - seeded + 1   # the completed one leaves `work list`
    return _verdict(actual == count,
                    f"{len(lines)} items listed, {seeded} seeded, "
                    f"{actual} new against an expected {count}")


def p_capability_status(run, ref="", status="", **_):
    proc = tcw(run["fixture"], "capabilities", "show", ref)
    return _verdict(status in proc.stdout,
                    f"{ref}: {proc.stdout.strip()[:120]}")


def p_new_capability_count(run, count=0, **_):
    proc = tcw(run["fixture"], "capabilities", "list")
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    return _verdict(len(lines) - 2 == count,
                    f"{len(lines)} capabilities, 2 seeded, expected {count} new")


def p_taxonomy_entry_kind(run, id="", kind="", **_):
    proc = tcw(run["fixture"], "taxonomy", "show", id)
    return _verdict(kind.lower() in proc.stdout.lower(),
                    f"{id}: {proc.stdout.strip()[:120]}")


def p_taxonomy_feature_links_vocab(run, feature="", vocab="", **_):
    proc = tcw(run["fixture"], "taxonomy", "show", feature)
    return _verdict(vocab in proc.stdout,
                    f"{feature}: {proc.stdout.strip()[:140]}")


def p_validate_exit_zero(run, **_):
    proc = tcw(run["fixture"], "validate")
    return _verdict(proc.returncode == 0,
                    f"`tcw validate` exited {proc.returncode}"
                    + (f": {proc.stderr.strip()[:120]}" if proc.returncode else ""))


def p_git_order(run, before="", after="", **_):
    """Commit ordering, which the log does show. Not tool provenance, which it
    does not: identical commits come from compliant and non-compliant histories
    alike."""
    log = git(run["fixture"], "log", "--oneline", "--reverse").splitlines()
    at_before = next((i for i, l in enumerate(log) if before in l), None)
    at_after = next((i for i, l in enumerate(log) if after in l), None)
    if at_before is None or at_after is None:
        return _verdict(False, f"{before!r} at {at_before}, {after!r} at "
                               f"{at_after} in {len(log)} commits")
    return _verdict(at_before < at_after,
                    f"{before!r} at commit {at_before}, {after!r} at {at_after}")


def p_git_commit_per_artifact(run, **_):
    log = git(run["fixture"], "log", "--oneline").splitlines()
    names = ("spec", "plan", "outcome", "refined-outcome", "post-mortem")
    touched = [n for n in names
               if any(n in l for l in log)]
    batched = [l for l in log
               if sum(1 for n in names if n in l) > 1]
    return _verdict(not batched,
                    f"artifact commits: {touched}; batched: {batched[:2]}")


def p_files_changed_exactly(run, paths=(), **_):
    changed = set(git(run["fixture"], "diff", "--name-only",
                      "HEAD~1", "HEAD").split())
    wanted = set(paths)
    return _verdict(changed == wanted,
                    f"changed {sorted(changed)}, expected {sorted(wanted)}")


PREDICATES = {name[2:]: fn for name, fn in list(globals().items())
              if name.startswith("p_")}


# --- grading a run ---------------------------------------------------------

def grade_run(run_dir: Path) -> dict:
    """Every assertion for one case × arm, with its evidence."""
    timing = json.loads((run_dir / "timing.json").read_text())
    cases = {c["id"]: c for c in json.loads(
        (Path(__file__).with_name("evals.json")).read_text())["cases"]}
    case = cases[timing["case"]]

    run = {
        "events": load_events(run_dir / "transcript.jsonl"),
        "fixture": Path(timing["fixture"]),
        "nonces": timing.get("nonces", {}),
        "stage_items": timing.get("stage_items", {}),
        "items": timing.get("items", {}),
    }

    results = []
    for assertion in case["assertions"]:
        if "unmechanized" in assertion:
            results.append({"text": assertion["unmechanized"],
                            "passed": None, "evidence": "",
                            "unmechanized": assertion.get("why", "")})
            continue
        # An assertion scoped to one arm says nothing about the other.
        if assertion.get("arm") and assertion["arm"] != timing["arm"]:
            continue
        fn = PREDICATES.get(assertion["predicate"])
        if fn is None:
            results.append({"text": assertion.get("text", ""), "passed": False,
                            "evidence": f"no grader for predicate "
                                        f"{assertion['predicate']!r}"})
            continue
        verdict = fn(run, **assertion.get("args", {}))
        results.append({"text": assertion.get("text", ""),
                        "predicate": assertion["predicate"], **verdict})

    graded = [r for r in results if r["passed"] is not None]
    return {
        "case": timing["case"], "arm": timing["arm"], "axis": timing["axis"],
        "capped": timing.get("capped", False),
        "isolation_problems": timing.get("isolation_problems", []),
        "passed": sum(1 for r in graded if r["passed"]),
        "graded": len(graded),
        "unmechanized": len(results) - len(graded),
        "assertions": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_root", type=Path,
                        help="a run directory, or a tree of them")
    args = parser.parse_args(argv)

    dirs = ([args.run_root] if (args.run_root / "timing.json").is_file()
            else sorted(p.parent for p in args.run_root.rglob("timing.json")))
    if not dirs:
        print(f"grade: no runs under {args.run_root}", file=sys.stderr)
        return 1

    reports = [grade_run(d) for d in dirs]
    for report in reports:
        flag = " CAPPED" if report["capped"] else ""
        print(f"{report['case']} [{report['arm']}] "
              f"{report['passed']}/{report['graded']}{flag}"
              + (f" +{report['unmechanized']} unmechanized"
                 if report["unmechanized"] else ""))
        for a in report["assertions"]:
            mark = {True: "pass", False: "FAIL", None: "n/a "}[a["passed"]]
            prov = f" [{a['provenance']}]" if a.get("provenance") else ""
            print(f"    {mark}{prov} {a['text'][:88]}")
            if a.get("evidence"):
                print(f"         {a['evidence'][:100]}")

    out = args.run_root / "grading.json"
    out.write_text(json.dumps(reports, indent=1) + "\n")
    print(f"\nwrote {out}")
    return 0 if all(r["passed"] == r["graded"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
