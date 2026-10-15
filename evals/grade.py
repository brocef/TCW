"""Read one run directory and decide what it showed.

Two families, matching the two things a run leaves behind.

**Transcript reads** answer questions nothing else can: did the agent run
`tcw work stage prompt`, did a pointer line reach it, did it open a given file.
A run whose transcript was not captured cannot be graded for them.

**Fixture end-state reads** ask the project rather than walk it — `tcw work
path`, `tcw work show`, `tcw work list`, `tcw capabilities show`, `tcw
validate` — so the harness measures a project rather than a directory layout.
One read genuinely cannot: which files a change touched. That is a property of
the fixture's version control rather than of the store interface, and the
fixture is a git repository by construction. It stays here and never reaches
`tcw/`.

## What a nonce shows, now that nothing injects

TCW 3.0 has one source of stage text: `tcw work stage prompt <stage> <slug>`.
No skill injects it into the conversation, so there is no longer a question of
*how* a nonce arrived — the agent either ran that command and acted on what it
printed, or it did not. An axis A case therefore asks two things, each its own
assertion: the agent ran the command (`tool_input_contains`), and the artifact
carries the nonce (`nonce_in_artifact`).

## Verdict rounds

Review and qa rounds begin with YAML front matter TCW reads when an item moves:
`verdict: accepted|rejected` and `judges: <N>`, where N is the newest implement
round. `round_front_matter` asks TCW's own reader (`tcw.work.layout`) whether
the front matter is valid, so "valid" means exactly what `tcw work advance`
means by it, and then checks `judges` against the implement rounds that are
actually there.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

from tcw.work.gates import parse_declarations
from tcw.work.layout import INVALID, ROUND_NAME, round_verdict

# The environment every `tcw` call made here runs with: no personal
# configuration layer, so grading reads what the project configured and
# nothing a person on the grading machine set for themselves.
TCW_ENV = {**os.environ, "TCW_NO_PERSONAL_CONFIG": "1"}

# The first line TCW prints above every non-empty stage prompt. A stage that
# resolves to nothing prints nothing at all, this line included.
PROMPT_HEADER = "This text ran no checks."


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
    pointer line or an answer can appear in any of them.
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


def _tool_inputs(events: list[dict]):
    """The input of every tool call the run made, in order, as JSON text.

    Only what the agent ran or opened: a `Read`'s `file_path`, a `Bash`
    command. Assistant prose, user messages and tool *results* are left out,
    because a skill body that merely mentions a path is not the agent opening it.
    """
    for event in events:
        content = (event.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                # Non-ASCII left as is, so a search text containing it matches.
                yield json.dumps(block.get("input"), ensure_ascii=False)


def _first_index(texts: list[str], needle: str) -> int | None:
    for i, text in enumerate(texts):
        if needle in text:
            return i
    return None


# --- asking the project ----------------------------------------------------

def tcw(fixture: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tcw.cli", *args],
                          cwd=str(fixture), capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, env=TCW_ENV)


def all_items(fixture: Path) -> list[str] | None:
    """Every item's slug, ended ones included, or None when the list could not
    be read."""
    proc = tcw(fixture, "work", "list", "--all")
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def resolve_item(run: dict, key: str) -> tuple[str | None, str]:
    """The slug a case's `item` argument names, and how it was found.

    A seeded role (`spec`, `closeout`, `completed`, ...) is read from the run's
    manifest, because slugs carry the date they were minted. `new` names the
    one item the agent created: it resolves only when exactly one item exists
    that the seeder did not make, since with none or several there is no
    single item the case could mean.
    """
    if key != "new":
        slug = run["items"].get(key)
        return (slug, slug) if slug else (None, f"no seeded item {key!r} in "
                                                f"the run's manifest")
    slugs = all_items(run["fixture"])
    if slugs is None:
        return None, "`tcw work list --all` failed"
    created = sorted(set(slugs) - set(run["items"].values()))
    if len(created) != 1:
        return None, f"expected exactly one new item, found {created}"
    return created[0], created[0]


def item_folder(run: dict, slug: str) -> Path | None:
    """The item's folder, as `tcw work path <slug>` prints it."""
    proc = tcw(run["fixture"], "work", "path", slug)
    return Path(proc.stdout.strip()) if proc.returncode == 0 else None


def stage_path(run: dict, slug: str, stage: str) -> Path | None:
    """What `tcw work path <slug> <stage>` prints: a document stage's file, or
    a rounds stage's folder. None when the CLI refused."""
    proc = tcw(run["fixture"], "work", "path", slug, stage)
    return Path(proc.stdout.strip()) if proc.returncode == 0 else None


def rounds(folder: Path | None) -> list[tuple[int, Path]]:
    """A rounds stage's `round-N.md` files, in order."""
    if folder is None or not folder.is_dir():
        return []
    return sorted((int(m.group(1)), p) for p in folder.iterdir()
                  if (m := ROUND_NAME.match(p.name)) and p.is_file())


def artifact(run: dict, item: str, stage: str) -> tuple[Path | None, str]:
    """The stage's artifact for the case's item: the document for a document
    stage, the newest round for a rounds stage. Returns the path, or None and
    why not."""
    slug, said = resolve_item(run, item)
    if slug is None:
        return None, said
    path = stage_path(run, slug, stage)
    if path is None:
        return None, f"`tcw work path {slug} {stage}` refused"
    if path.suffix == ".md":
        return (path, str(path)) if path.is_file() else (
            None, f"{stage} document not written at {path}")
    found = rounds(path)
    return (found[-1][1], str(found[-1][1])) if found else (
        None, f"no {stage} round in {path}")


def _split(path: Path) -> tuple[str | None, str]:
    """A round's front matter text (None when it has none) and its body. The
    same shape TCW reads: a first line `---`, closed by the next `---`."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        for end, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return "\n".join(lines[1:end]), "\n".join(lines[end + 1:])
    return None, "\n".join(lines)


def _body(path: Path) -> str:
    """A round's text below its front matter."""
    return _split(path)[1]


def _meta(path: Path) -> dict:
    """A round's front matter as a mapping; empty when it has none or it does
    not parse."""
    try:
        meta = yaml.safe_load(_split(path)[0] or "")
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    return meta if isinstance(meta, dict) else {}


# --- the predicates --------------------------------------------------------

def _verdict(passed: bool, evidence: str, **extra) -> dict:
    """Every pass carries evidence quoted from the output. A heading with nothing
    under it is a fail, so an empty evidence string cannot pass."""
    return {"passed": bool(passed) and bool(evidence.strip()),
            "evidence": evidence, **extra}


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


def p_tool_input_contains(run, text="", **_):
    inputs = list(_tool_inputs(run["events"]))
    hit = _first_index(inputs, text)
    return _verdict(hit is not None,
                    f"{text!r} is in tool call {hit}" if hit is not None
                    else f"{text!r} is in none of {len(inputs)} tool calls")


def p_tool_input_absent(run, text="", **_):
    """Fails when the run made no tool calls at all. A transcript in a shape
    `_tool_inputs` does not recognise yields none, and "absent" would then pass
    for every text."""
    inputs = list(_tool_inputs(run["events"]))
    if not inputs:
        return _verdict(False, "no tool calls found in the transcript")
    hit = _first_index(inputs, text)
    return _verdict(hit is None,
                    f"{text!r} is in none of {len(inputs)} tool calls"
                    if hit is None
                    else f"{text!r} is in tool call {hit}: {inputs[hit][:140]}")


def p_nonce_in_artifact(run, kind="", item="", stage="", **_):
    """The axis A core: the binding's nonce is in the stage's artifact.

    Present proves the bound text reached the agent *and* was acted on. Whether
    the agent got it by running `tcw work stage prompt` is a separate assertion
    on the transcript.
    """
    nonce = run["nonces"].get(kind)
    if not nonce:
        return _verdict(False, f"no {kind!r} nonce in the run manifest")
    path, said = artifact(run, item, stage)
    if path is None:
        return _verdict(False, said)
    body = path.read_text()
    if nonce not in body:
        return _verdict(False, f"{nonce} absent from {path.name} "
                               f"({len(body)} bytes written)")
    line = next((l for l in body.splitlines() if nonce in l), "")
    return _verdict(True, f"{nonce} in {path.name}: {line.strip()[:90]!r}")


def p_nonce_absent_from_artifact(run, kinds=(), item="", stage="", **_):
    path, said = artifact(run, item, stage)
    if path is None:
        return _verdict(False, said)
    body = path.read_text()
    leaked = [k for k in kinds if run["nonces"].get(k, "\0") in body]
    return _verdict(not leaked,
                    f"none of {list(kinds)} appear in {path.name}" if not leaked
                    else f"leaked into {path.name}: {leaked}")


def p_stage_prompt_empty(run, stage="", **_):
    slug = run["stage_items"].get(stage, "")
    proc = tcw(run["fixture"], "work", "stage", "prompt", stage, slug)
    if proc.returncode != 0:
        return _verdict(False, f"`tcw work stage prompt {stage}` exited "
                               f"{proc.returncode}: {proc.stderr.strip()[:120]}")
    return _verdict(proc.stdout == "",
                    f"`{stage}` resolved to {len(proc.stdout)} bytes")


def p_stage_prompt_framed(run, stage="", **_):
    """Asserted by shape, not by byte count, which moves whenever TCW's own
    text is edited: a stage that resolves to something prints TCW's header
    line above it."""
    slug = run["stage_items"].get(stage, "")
    proc = tcw(run["fixture"], "work", "stage", "prompt", stage, slug)
    framed = PROMPT_HEADER in proc.stdout
    return _verdict(proc.returncode == 0 and framed,
                    f"`{stage}` resolved to {len(proc.stdout)} bytes, header "
                    f"{'present' if framed else 'absent'}")


def p_artifact_exists(run, item="", stage="", **_):
    """The stage's document, or its newest round, exists and is not empty."""
    path, said = artifact(run, item, stage)
    if path is None:
        return _verdict(False, said)
    text = path.read_text().strip()
    return _verdict(bool(text), f"{stage} artifact at {path} "
                                f"({len(text)} characters)")


def p_round_front_matter(run, item="", stage="", **_):
    """The stage's newest round opens with front matter TCW accepts, and its
    `judges` is the newest implement round.

    Validity is TCW's own reading (`round_verdict`), the one `tcw work advance`
    applies; the implement round is counted from the files `tcw work path`
    names, not from anything the round itself says.
    """
    path, said = artifact(run, item, stage)
    if path is None:
        return _verdict(False, said)
    verdict = round_verdict(path)
    if verdict.state == INVALID:
        return _verdict(False, f"{path.name}: front matter is not a valid "
                               f"`verdict: accepted|rejected` with a whole-"
                               f"number `judges`: {_meta(path)!r}")
    slug, _ = resolve_item(run, item)
    implemented = rounds(stage_path(run, slug, "implement"))
    newest = implemented[-1][0] if implemented else 0
    return _verdict(verdict.judges == newest,
                    f"{stage}/{path.name}: verdict {verdict.state}, judges "
                    f"{verdict.judges}; newest implement round is {newest}")


def p_round_verdict_is(run, item="", stage="", verdict="", **_):
    """The newest round's `verdict` is exactly this value."""
    path, said = artifact(run, item, stage)
    if path is None:
        return _verdict(False, said)
    found = _meta(path).get("verdict")
    return _verdict(found == verdict,
                    f"{stage}/{path.name}: verdict {found!r}, expected "
                    f"{verdict!r}")


def p_round_decided_by(run, item="", stage="", name="", **_):
    """The newest round's front matter carries a non-empty `decided-by`, and
    it names `name` when one is given."""
    path, said = artifact(run, item, stage)
    if path is None:
        return _verdict(False, said)
    found = _meta(path).get("decided-by")
    ok = isinstance(found, str) and found.strip() != "" and (
        not name or name.lower() in found.lower())
    return _verdict(ok, f"{stage}/{path.name}: decided-by {found!r}"
                        + (f", expected it to name {name!r}" if name else ""))


def p_round_lists_scenarios(run, item="", stage="", **_):
    """Every QA plan scenario the manifest records is named on a line of the
    newest round's body, below its front matter."""
    scenarios = run.get("qa_scenarios") or []
    if not scenarios:
        return _verdict(False, "the run's manifest records no QA scenarios")
    path, said = artifact(run, item, stage)
    if path is None:
        return _verdict(False, said)
    lines = _body(path).splitlines()
    counts = {s: sum(1 for line in lines
                     if re.search(rf"(?<![\w-]){re.escape(s)}(?!\d)", line))
              for s in scenarios}
    missing = [s for s, n in counts.items() if n == 0]
    return _verdict(not missing,
                    f"{stage}/{path.name}: lines naming each scenario {counts}"
                    + (f"; missing {missing}" if missing else ""))


def p_item_stage(run, item="", stage="", **_):
    """The item's stage, as `tcw work show --json` reports it."""
    slug, said = resolve_item(run, item)
    if slug is None:
        return _verdict(False, said)
    proc = tcw(run["fixture"], "work", "show", slug, "--json")
    try:
        found = json.loads(proc.stdout)["item"]["stage"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return _verdict(False, f"`tcw work show {slug} --json` exited "
                               f"{proc.returncode}: {proc.stderr.strip()[:120]}")
    return _verdict(found == stage, f"{slug} is at {found}, expected {stage}")


def p_new_item_count(run, count=0, **_):
    """Items beyond the seeded set, ended ones included, via `tcw work list
    --all`."""
    slugs = all_items(run["fixture"])
    if slugs is None:
        return _verdict(False, "`tcw work list --all` failed")
    created = sorted(set(slugs) - set(run["items"].values()))
    return _verdict(len(created) == count,
                    f"{len(slugs)} items, {len(run['items'])} seeded, new: "
                    f"{created} against an expected {count}")


def p_capability_status(run, ref="", status="", **_):
    proc = tcw(run["fixture"], "capabilities", "show", ref)
    found = re.search(r"(?mi)^\s*status:\s*(\S+)", proc.stdout)
    actual = found.group(1) if found else None
    return _verdict(proc.returncode == 0 and actual == status,
                    f"{ref}: status {actual!r} (exit {proc.returncode}), "
                    f"expected {status!r}")


def p_capability_records_added(run, count=0, seeded=1, **_):
    """How many capability records exist beyond the `seeded` ones, via `tcw
    capabilities list`."""
    proc = tcw(run["fixture"], "capabilities", "list")
    if proc.returncode != 0:
        return _verdict(False, f"`tcw capabilities list` exited "
                               f"{proc.returncode}")
    paths = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    return _verdict(len(paths) - seeded == count,
                    f"{len(paths)} capabilities ({paths}), {seeded} seeded, "
                    f"expected {count} added")


def p_capabilities_declared(run, item="", kind="new", count=1, **_):
    """The item's `capabilities.yaml`, beside the folder `tcw work path <slug>`
    prints, declares exactly `count` capability paths under `kind`. Read with
    TCW's own parser, so a file TCW would reject is a fail."""
    slug, said = resolve_item(run, item)
    if slug is None:
        return _verdict(False, said)
    folder = item_folder(run, slug)
    if folder is None:
        return _verdict(False, f"`tcw work path {slug}` refused")
    path = folder / "capabilities.yaml"
    if not path.is_file():
        return _verdict(False, f"{slug} has no capabilities.yaml")
    declared = parse_declarations(path)
    if isinstance(declared, str):
        return _verdict(False, f"capabilities.yaml: {declared}")
    found = list(getattr(declared, kind))
    return _verdict(len(found) == count,
                    f"capabilities.yaml declares {kind}: {found}, expected "
                    f"{count}")


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


def _expand_paths(run: dict, paths) -> tuple[set[str], str | None]:
    """`{item:<role>}` in a path becomes that item's folder, relative to the
    fixture root, as `tcw work path <slug>` prints it: the folder name carries
    the date the slug was minted, so evals.json cannot spell it."""
    out = set()
    for raw in paths:
        def folder(match):
            slug, said = resolve_item(run, match.group(1))
            where = item_folder(run, slug) if slug else None
            if where is None:
                raise LookupError(said if slug is None
                                  else f"`tcw work path {slug}` refused")
            return where.resolve().relative_to(
                Path(run["fixture"]).resolve()).as_posix()
        try:
            out.add(re.sub(r"\{item:([\w-]+)\}", folder, raw))
        except LookupError as error:
            return set(), f"cannot expand {raw!r}: {error}"
    return out, None


def p_files_changed_exactly(run, paths=(), **_):
    """What the agent changed since the seed, whether or not it committed.

    `git diff <seeded_head>` compares the working tree with the seeded commit,
    so it covers committed and uncommitted edits alike. Untracked files git does
    not ignore are added, because a new file is a change too. A run recorded
    without `seeded_head` fails rather than falling back to the last commit,
    which is the misleading answer this replaced.

    A git failure fails the check with git's error, rather than reading as an
    empty change list. Renames are reported as a deletion plus an addition,
    which is what a plain `mv` looks like too. The grading machine's own global
    ignore file is not read, so a fixture grades the same on every machine, and
    output is read as bytes, so a carriage return in a file name survives.
    """
    seeded_head = run.get("seeded_head")
    if not seeded_head:
        return _verdict(False, "the run entry has no `seeded_head`, so there is "
                               "no seeded commit to compare against")
    changed = set()
    for args in (["diff", "--name-only", "--no-renames", "-z", seeded_head, "--"],
                 ["-c", f"core.excludesFile={os.devnull}",
                  "ls-files", "-z", "--others", "--exclude-standard"]):
        proc = subprocess.run(["git", "-C", str(run["fixture"]), *args],
                              capture_output=True)
        if proc.returncode != 0:
            verb = "ls-files" if "ls-files" in args else "diff"
            return _verdict(False, f"`git {verb}` failed in the fixture: "
                                   f"{os.fsdecode(proc.stderr).strip()[:200]}")
        changed |= {os.fsdecode(p) for p in proc.stdout.split(b"\0") if p}
    if any("{item:" in p for p in paths):
        wanted, problem = _expand_paths(run, paths)
        if problem:
            return _verdict(False, problem)
    else:
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
        # Relative resolves against the run directory, which is where the
        # runner puts the fixture. A live run writes an absolute path.
        "fixture": run_dir / timing["fixture"],
        "nonces": timing.get("nonces", {}),
        "stage_items": timing.get("stage_items", {}),
        "items": timing.get("items", {}),
        "qa_scenarios": timing.get("qa_scenarios", []),
        "seeded_head": timing.get("seeded_head"),
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
            print(f"    {mark} {a['text'][:88]}")
            if a.get("evidence"):
                print(f"         {a['evidence'][:100]}")

    out = args.run_root / "grading.json"
    out.write_text(json.dumps(reports, indent=1) + "\n")
    print(f"\nwrote {out}")
    return 0 if all(r["passed"] == r["graded"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
