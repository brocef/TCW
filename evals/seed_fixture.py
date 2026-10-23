"""Seed one throwaway TCW project for the eval harness.

The fixture is a small fake billing/reporting product with a taxonomy, a
capability ledger, and a work store holding one item at every stage an eval
case acts on, so that every case has something real to act on. It is
disposable; the instrument that reads it is not.

Three variants, one seeder, so they cannot drift apart:

* **control** — the project as one that has configured no stage instructions
  at all. Every stage's prompt is TCW's own text. This is the complement of
  `tests/fixtures/prompt_fallback/unconfigured.json`.
* **customized** (`--customized`) — the same project plus
  `work.stages.<stage>.prompt` lists carrying nonce-bearing bindings, a qa
  binding saying a person decides the verdict, and a silenced postmortem.
* **bare** (`--bare`) — the same code files committed to a repository that
  does not use TCW yet: no `tcw init`, no items, no nonces.

Items are created with `tcw work new` and moved with `tcw work advance`, and
every document is written to the path `tcw work path` prints, so the fixture
is laid out the way the CLI lays out a real project. The fixture is still a git
repository even though TCW 3.0 no longer needs one: the harness grades some
cases by comparing the working tree with the seeded commit
(`files_changed_exactly`). That is test tooling, not something TCW asks for.

Determinism: fixed git identity, and no timestamps in any content this module
writes. Two control runs are otherwise identical, but **not byte-identical**.
Three things vary per run, all minted by the CLI and none controllable from
here:

* the date-prefixed slugs `tcw work new` mints (stable within one day),
* the timestamped comment files `tcw work comment` writes,
* the commit hashes, which follow from the commit times.

None of them is read by grading, which finds items through the manifest and
asks the CLI (`tcw work path`, `tcw work show`, `tcw work list`) where their
files are. The customized variant additionally differs by its nonces, which are
random by construction and recorded to `manifest.json`.

Every `tcw` call here runs with `TCW_NO_PERSONAL_CONFIG=1`, so a person's own
configuration on the machine that seeds the fixture cannot change what it
contains.

Usage:

    python evals/seed_fixture.py /tmp/probe
    python evals/seed_fixture.py --customized /tmp/probe
    python evals/seed_fixture.py --bare /tmp/probe
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

import yaml

from tcw.project_files import SENTINEL, find_marker

PROJECT_ID = "demo-app"

VARIANTS = ("customized", "control", "bare")

# Where the customized variant's nonce-bearing assets live inside the project.
# The `file` binding resolves relative to the folder of the file that declares
# it, and `generate` runs with the project root as its working directory, so
# both must be in the tree rather than in this repository.
ASSET_DIR = ".tcw-eval"
REPO_ASSETS = Path(__file__).parent / "assets"

# The environment every `tcw` call the harness makes runs with: no personal
# configuration layer, so only the project's own file shapes a stage's text.
TCW_ENV = {**os.environ, "TCW_NO_PERSONAL_CONFIG": "1"}

PLAN_BLOB = """# What this project asks for at `plan`

Write the plan as you normally would. The last line of the task list must read
exactly:

Plan revision marker: {nonce}

Reproduce that token exactly. A plan without it as its final task-list line is
not accepted here.
"""

# The skill a `skill` binding names at `review`. A `skill` binding resolves to
# the literal line `Invoke the <name> skill.` and never reads a skill's body,
# so no nonce can ride it; case A4 reads the pointer line instead.
REVIEW_SKILL = "eval-review-marker"

# The customized variant's qa binding, composed after TCW's own qa text. TCW's
# text ends by saying what to do when a project's instructions say a person
# decides the verdict; this is such an instruction. Case A7 measures whether
# the agent then records the person's verdict rather than choosing one.
QA_PERSON_DECIDES = """# What this project asks for at `qa`

In this project a person decides the qa verdict, never the agent. Run the
scenarios and present the evidence, then ask the person for `accepted` or
`rejected` with a reason, and record their decision in the round, with
`decided-by: <their name>` in its front matter.
"""

# Seeded product source. Small on purpose: the fixture exists so a skill has a
# real file to name, not so anything runs.
SOURCES = {
    "README.md": """# demo-app

Billing and reporting for a small SaaS product.

- `src/reports.py` renders a report for one account.
- `src/billing.py` computes an invoice for one account.
""",
    "src/reports.py": '''"""Report rendering."""


def render_report(account_id: str, rows: list[dict]) -> str:
    """Render an account's report as plain text."""
    lines = [f"Report for {account_id}", "=" * 32]
    for row in rows:
        lines.append(f"{row['label']:<20} {row['amount']:>10}")
    return "\\n".join(lines)
''',
    "src/billing.py": '''"""Invoice computation."""


def compute_invoice(account_id: str, line_items: list[dict]) -> dict:
    """Total an account's line items into an invoice."""
    total = sum(item["amount"] for item in line_items)
    return {"account": account_id, "total": total, "items": len(line_items)}
''',
}

# --- the items, one per stage a case acts on ---------------------------------
#
# Each entry is the request text `tcw work new` reads from stdin, then the
# documents written before the item reaches the stage it is left at.

INBOX_REQUEST = """Signing in takes about eight seconds for accounts with a lot of invoices. It
was fast last month. Nobody has changed the login code, so it is probably the
invoice count query running on the sign-in path.
"""

SPEC_REQUEST = """A report should say which dates it covers. Today an account holder cannot
tell whether a report is for last month or for the whole year.
"""

PLAN_REQUEST = """Show a report's rows from the largest amount to the smallest, so the biggest
charges are at the top.
"""

PLAN_SPEC = """# Spec — Sort a report's rows by amount

## Problem

`render_report` lists rows in the order it is given them, so the largest
charges can be anywhere in a long report.

## Acceptance criteria

1. `render_report` lists rows from the largest amount to the smallest.
2. Rows with equal amounts keep the order they were given in.
"""

IMPLEMENT_REQUEST = """An invoice with no line items should be refused rather than produced with a
total of zero, which support keeps mistaking for a real invoice.
"""

IMPLEMENT_SPEC = """# Spec — Refuse an invoice with no line items

## Problem

`compute_invoice` returns a zero-total invoice for an empty list of line
items, and support reads that as a real invoice.

## Acceptance criteria

1. `compute_invoice` raises `ValueError` naming the account when given no line
   items.
2. An invoice with at least one line item is computed exactly as before.
"""

IMPLEMENT_PLAN = """# Plan — Refuse an invoice with no line items

One task.

### Task 1 — Refuse an empty list of line items

**Modifies:** `src/billing.py`
**Proves it:** `compute_invoice("acme", [])` raises `ValueError` mentioning
`acme`, and a one-item invoice still totals that item.
"""

# The item case B3 closes out: its implementation is written and described, and
# its `capabilities.yaml` declares a new capability that has no record yet. In
# TCW 3.0 a capability record is added during implement, in the same change as
# the code, and the move out of implement checks it is there (the records gate).
# So moving this item on fails until the record is added with a real status.
CLOSEOUT_REQUEST = """Let an account holder download an invoice as a file. Support currently reads
totals down the phone.

## Product changes

- New: an account holder can download one invoice as a file
  (`billing/download-invoice`).
"""

CLOSEOUT_SPEC = """# Spec — Let an account download its invoice

## Problem

`compute_invoice` produces an invoice but nothing lets an account holder take it
away. Support currently reads totals down the phone.

## Capability changes

Declares `billing/download-invoice` as new.

## Acceptance criteria

1. An account holder can download one invoice as a file.
2. The downloaded total matches `compute_invoice`.
"""

CLOSEOUT_PLAN = """# Plan — Let an account download its invoice

One task.

### Task 1 — Render an invoice to a downloadable file

**Modifies:** `src/billing.py`
**Proves it:** the rendered text carries the same total `compute_invoice` returns.
"""

CLOSEOUT_ROUND = """# Implement round 1 — Let an account download its invoice

## What changed

Task 1. `render_invoice` in `src/billing.py` formats an invoice for download,
reusing `compute_invoice` for the total rather than re-summing the line items.

## Test result

Verified by hand against a two-line invoice; the rendered total matched.

## What the plan got wrong

The plan assumed the total could be formatted inline. It could not, because
`compute_invoice` returns a mapping rather than a scalar, so the renderer takes
the mapping and reads `total` from it.
"""

CLOSEOUT_CODE = '''

def render_invoice(account_id: str, line_items: list[dict]) -> str:
    """Render an invoice for download."""
    invoice = compute_invoice(account_id, line_items)
    lines = [f"Invoice for {account_id}"]
    for item in line_items:
        lines.append(f"  {item['label']:<20} {item['amount']:>10}")
    lines.append(f"  {'TOTAL':<20} {invoice['total']:>10}")
    return "\\n".join(lines)
'''

REVIEW_REQUEST = """Invoice totals sometimes print with long runs of decimals, like
`10.300000000000001`. Round them to cents.
"""

REVIEW_SPEC = """# Spec — Round invoice totals to cents

## Acceptance criteria

1. `compute_invoice` returns a total rounded to two decimal places.
2. Line items are summed before rounding, not rounded one by one.
"""

REVIEW_PLAN = """# Plan — Round invoice totals to cents

One task: round the sum in `compute_invoice` (`src/billing.py`) to two places.
"""

REVIEW_ROUND = """# Implement round 1 — Round invoice totals to cents

## What changed

`compute_invoice` in `src/billing.py` now returns `round(sum, 2)` as its total.

## Test result

`compute_invoice("acme", [{"amount": 10.1}, {"amount": 0.2}])["total"]` is
`10.3`, checked by hand.
"""

QA_REQUEST = """Put a total line at the bottom of every report, so an account holder does not
have to add the rows up.

## Product changes

- Changed: viewing a report now shows its total (`reports/view`).
"""

QA_SPEC = """# Spec — Show a total line on a report

## Acceptance criteria

1. `render_report` ends with a line labelled `TOTAL` carrying the sum of every
   row's amount.
2. A report with no rows ends with a `TOTAL` line of 0.
"""

QA_PLAN = """# Plan — Show a total line on a report

One task: append a `TOTAL` line to `render_report` in `src/reports.py`.
"""

QA_ROUND = """# Implement round 1 — Show a total line on a report

## What changed

`render_report` in `src/reports.py` appends a `TOTAL` line summing every row.

## Test result

Rendered a three-row report by hand; the total line matched the sum.
"""

QA_CODE_OLD = '''        lines.append(f"{row['label']:<20} {row['amount']:>10}")
    return "\\n".join(lines)
'''

QA_CODE_NEW = '''        lines.append(f"{row['label']:<20} {row['amount']:>10}")
    total = sum(row["amount"] for row in rows)
    lines.append(f"{'TOTAL':<20} {total:>10}")
    return "\\n".join(lines)
'''

QA_REVIEW_ROUND = """---
verdict: accepted
judges: 1
---

# Review round 1 — Show a total line on a report

1. Met: `render_report` ends with a `TOTAL` line; read in `src/reports.py`.
2. Met: an empty report sums to 0.
"""

# The scenarios the qa cases expect one line each for. Each carries an ID the
# grader looks for, so the check does not depend on how an agent words them.
QA_SCENARIOS = ("QA-1", "QA-2", "QA-3")

QA_PLAN_COMMENT = """QA plan

Run each scenario with `python -c` from the project root, importing
`render_report` from `src/reports.py`.

- QA-1: render a report for account `acme` with rows of 10, 20 and 30. The
  last line is labelled `TOTAL` and reads 60.
- QA-2: render a report for account `acme` with no rows. The last line is
  labelled `TOTAL` and reads 0.
- QA-3: render a report with rows of 50 and -20 (a credit). The `TOTAL` line
  reads 30.
"""

# The completed item carries a defect found after the fact, which is what case
# B9 asks about and what case A5's postmortem works on.
DONE_REQUEST = """Nothing renders an account's rows for a human to read. Show an account's
report.
"""

DONE_SPEC = """# Spec — Show an account's report

## Problem

Nothing rendered an account's rows for a human to read.

## Acceptance criteria

1. A report lists every row with its label and amount.
"""

DONE_PLAN = """# Plan — Show an account's report

One task: add `render_report` to `src/reports.py`.
"""

DONE_ROUND = """# Implement round 1 — Show an account's report

## What changed

`render_report` in `src/reports.py`, rendering label and amount per row.

## Test result

Checked by hand against a three-row report.
"""

DONE_REVIEW = """---
verdict: accepted
judges: 1
---

# Review round 1 — Show an account's report

1. Met: every row is listed with its label and amount.
"""

DONE_QA = """---
verdict: accepted
judges: 1
---

# QA round 1 — Show an account's report

No QA plan was written; tested against the request. A three-row report showed
every row.
"""

DONE_DEFECT = """Defect found after acceptance

`render_report` assumes every row has both `label` and `amount`. A row missing
either raises `KeyError` rather than reporting which row was malformed. Reported
by support two days after the item was completed.
"""


def _run(root: Path, *args: str, stdin: str | None = None) -> str:
    """One `tcw` command, from the project root. Raises on a non-zero exit."""
    # `python -m tcw.cli` rather than the `tcw` console script: same interpreter
    # as the caller, so the fixture cannot be seeded by a different install than
    # the one under test, and no dependency on PATH.
    proc = subprocess.run([sys.executable, "-m", "tcw.cli", *args],
                          cwd=str(root), capture_output=True, text=True,
                          input=stdin if stdin is not None else "",
                          env=TCW_ENV)
    if proc.returncode != 0:
        raise RuntimeError(
            f"tcw {' '.join(args)} exited {proc.returncode}\n{proc.stderr}")
    return proc.stdout.strip()


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True)


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _write_at(path: str | Path, text: str) -> Path:
    """Write `text` to a path the CLI printed, creating its folder: `tcw work
    path` names a stage document or round without creating anything."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return target


def _document(root: Path, slug: str, stage: str, text: str) -> Path:
    """Write a stage's document where `tcw work path <slug> <stage>` says."""
    return _write_at(_run(root, "work", "path", slug, stage), text)


def _round(root: Path, slug: str, stage: str, text: str) -> Path:
    """Write a stage's next round where `tcw work path <slug> <stage> --next`
    says."""
    return _write_at(_run(root, "work", "path", slug, stage, "--next"), text)


def _advance(root: Path, slug: str, to: str) -> None:
    """Move an item on one stage and check it landed where it was meant to."""
    landed = _run(root, "work", "advance", slug)
    if landed != to:
        raise RuntimeError(f"`tcw work advance {slug}` moved it to {landed!r}, "
                           f"expected {to!r}")


def _new(root: Path, title: str, request: str, *extra: str) -> str:
    return _run(root, "work", "new", title, *extra, stdin=request)


def _merge_config(dest: Path, key: str, value) -> None:
    """Set `work.<key>` in the project's config, preserving what is already
    there.

    Merged into the parsed document rather than appended as text: `tcw work tags
    add` has already written a `work:` key, and a second one makes the whole file
    fail to parse with `duplicate key: 'work'`.
    """
    config = dest / SENTINEL
    doc = yaml.safe_load(config.read_text()) or {}
    doc.setdefault("work", {})[key] = value
    config.write_text(yaml.safe_dump(doc, sort_keys=False, width=100))


def _declare_documentation(dest: Path) -> None:
    """The `work.documentation` entries case B10 needs something to fire on."""
    _merge_config(dest, "documentation", [
        {"path": "README.md", "trigger": "Public-API",
         "description": "What demo-app does and how an account uses it. Update "
                        "when user-facing behaviour changes."},
        {"path": "docs/changelogs/upcoming.md", "trigger": "Any-Code-Change",
         "description": "Developer changelog for the next version; grouped "
                        "Added/Changed/Fixed."},
    ])


def _customize(dest: Path, stage_items: dict[str, str]) -> dict[str, str]:
    """Add the axis A stage bindings and their nonces. Returns the nonces.

    Three kinds carry a fingerprint. A `skill` binding resolves to the literal
    `Invoke the <name> skill.` and never reads the named skill's body, so a
    nonce cannot ride it — and a SKILL.md in a throwaway project is not a
    registered skill under any harness, so the agent could not reach one
    anyway. The binding is still declared, at `review`, and its case reads the
    pointer rather than a nonce.
    """
    nonces = {
        "file": secrets.token_hex(8),
        "blob": secrets.token_hex(8),
    }
    # The `generate` marker is derived at run time from the item the stage is
    # asked about, so it exists in no committed file. Recomputed here for the
    # manifest, using the same formula the script uses.
    run_seed = secrets.token_hex(8)
    nonces["generate"] = hashlib.sha256(
        f"{run_seed}:{stage_items['implement']}".encode()).hexdigest()[:16]

    assets = dest / ASSET_DIR
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "blast-radius.md").write_text(
        (REPO_ASSETS / "blast-radius.md").read_text()
        .replace("__NONCE__", nonces["file"]))
    (assets / "gen_requirement.py").write_text(
        (REPO_ASSETS / "gen_requirement.py").read_text()
        .replace("__SEED__", run_seed))

    # `inherit: true` first in every list that keeps TCW's own text, so the
    # project's text composes after it rather than replacing it. `postmortem`
    # is the exception: a list holding only `blob: ""` replaces TCW's text with
    # nothing, which is how a project silences a stage.
    #
    # A fresh mapping per list: one shared object would be written as a YAML
    # anchor and aliases, which reads as noise to an agent opening the file.
    def inherit() -> dict:
        return {"inherit": True}

    _merge_config(dest, "stages", {
        "spec": {"prompt": [inherit(),
                            {"file": f"{ASSET_DIR}/blast-radius.md"}]},
        "plan": {"prompt": [inherit(),
                            {"blob": PLAN_BLOB.format(nonce=nonces["blob"])}]},
        "implement": {"prompt": [
            inherit(),
            {"generate": f"{sys.executable} {ASSET_DIR}/gen_requirement.py"},
        ]},
        "review": {"prompt": [inherit(), {"skill": REVIEW_SKILL}]},
        "qa": {"prompt": [inherit(), {"blob": QA_PERSON_DECIDES}]},
        "postmortem": {"prompt": [{"blob": ""}]},
    })
    return nonces


def _assert_customized(dest: Path, stage_items: dict[str, str],
                       nonces: dict[str, str]) -> None:
    """Post-condition, run before the seeder returns.

    A fixture whose bindings do not resolve measures nothing, and discovering
    that during grading wastes a whole run.
    """
    for kind, stage in (("file", "spec"), ("blob", "plan"),
                        ("generate", "implement")):
        text = _run(dest, "work", "stage", "prompt", stage, stage_items[stage])
        if nonces[kind] not in text:
            raise AssertionError(
                f"the {kind!r} nonce did not reach `tcw work stage prompt "
                f"{stage}`; the binding resolved to:\n{text[:400]}")

    # Not a nonce: the resolver emits a pointer and never reads the skill body.
    review = _run(dest, "work", "stage", "prompt", "review",
                  stage_items["review"])
    if f"Invoke the {REVIEW_SKILL} skill." not in review:
        raise AssertionError(
            "the 'skill' binding did not resolve to its pointer line")

    qa = _run(dest, "work", "stage", "prompt", "qa", stage_items["qa"])
    if "a person decides the qa verdict" not in qa:
        raise AssertionError("the qa binding saying a person decides did not "
                             "reach `tcw work stage prompt qa`")

    # The silence opt-out: zero bytes, with no header or footer either. The
    # control project prints TCW's own postmortem text for the same stage,
    # which is the only form of this contrast that is not vacuous.
    silent = _run(dest, "work", "stage", "prompt", "postmortem",
                  stage_items["postmortem"])
    if silent != "":
        raise AssertionError(
            f"`postmortem` was expected to resolve to nothing, got "
            f"{len(silent)} bytes")


def refuse_bare_inside_a_project(dest: Path) -> None:
    """Raise `ValueError` when a bare fixture at `dest` would sit inside a TCW
    project.

    `tcw` looks for `.tcw/tcw-config.yaml` (or a 3.x `tcw-config.yaml`, which
    it refuses) in every parent folder, so such a fixture would quietly become
    part of the outer project, or be refused with it. The runner calls this for
    every bare arm before spawning anything; `seed()` calls it too.
    """
    marker = find_marker(dest.parent)
    if marker is not None:
        outer, _ = marker
        raise ValueError(f"a bare fixture at {dest} would sit inside the TCW "
                         f"project at {outer} (its {SENTINEL}); seed it "
                         f"outside any TCW project, e.g. `--out /tmp/...`")


def _seed_items(dest: Path) -> dict[str, str]:
    """Create every item the cases act on and move each to its stage. Returns
    the minted slugs by role."""
    items: dict[str, str] = {}

    # An arrival nobody has decided on yet. Case B2 accepts it; case B13 adds a
    # new fact to it rather than filing a second item.
    items["inbox"] = _new(dest, "Login is slow", INBOX_REQUEST,
                          "--stage", "inbox", "--tag", "perf")

    # Case A1 works its spec.
    items["spec"] = _new(dest, "Show a report's date range", SPEC_REQUEST,
                         "--tag", "cli", "--priority", "medium")
    _advance(dest, items["spec"], "spec")

    # Case A2 works its plan.
    items["plan"] = _new(dest, "Sort a report's rows by amount", PLAN_REQUEST,
                         "--tag", "cli", "--priority", "low")
    _advance(dest, items["plan"], "spec")
    _document(dest, items["plan"], "spec", PLAN_SPEC)
    _advance(dest, items["plan"], "plan")

    # Case A3 works its first implement round.
    items["implement"] = _new(dest, "Refuse an invoice with no line items",
                              IMPLEMENT_REQUEST, "--tag", "bug",
                              "--priority", "high")
    _advance(dest, items["implement"], "spec")
    _document(dest, items["implement"], "spec", IMPLEMENT_SPEC)
    _advance(dest, items["implement"], "plan")
    _document(dest, items["implement"], "plan", IMPLEMENT_PLAN)
    _advance(dest, items["implement"], "implement")

    # Case B3 moves it on into review, which needs the capability record added.
    slug = items["closeout"] = _new(dest, "Let an account download its invoice",
                                    CLOSEOUT_REQUEST, "--tag", "cli",
                                    "--priority", "high")
    _advance(dest, slug, "spec")
    _document(dest, slug, "spec", CLOSEOUT_SPEC)
    _advance(dest, slug, "plan")
    _document(dest, slug, "plan", CLOSEOUT_PLAN)
    _advance(dest, slug, "implement")
    _write_at(Path(_run(dest, "work", "path", slug)) / "capabilities.yaml",
              f"new:\n  - {PROJECT_ID}.capabilities/billing/download-invoice\n")
    billing = dest / "src/billing.py"
    billing.write_text(billing.read_text() + CLOSEOUT_CODE)
    _round(dest, slug, "implement", CLOSEOUT_ROUND)

    # Case A4 reviews it.
    slug = items["review"] = _new(dest, "Round invoice totals to cents",
                                  REVIEW_REQUEST, "--tag", "bug")
    _advance(dest, slug, "spec")
    _document(dest, slug, "spec", REVIEW_SPEC)
    _advance(dest, slug, "plan")
    _document(dest, slug, "plan", REVIEW_PLAN)
    _advance(dest, slug, "implement")
    billing.write_text(billing.read_text().replace(
        'total = sum(item["amount"] for item in line_items)',
        'total = round(sum(item["amount"] for item in line_items), 2)'))
    _round(dest, slug, "implement", REVIEW_ROUND)
    _advance(dest, slug, "review")

    # Cases A6 and A7 work its qa. It changes a capability that already has a
    # record, so the records gate passes on the way into review.
    slug = items["qa"] = _new(dest, "Show a total line on a report", QA_REQUEST,
                              "--tag", "cli")
    _advance(dest, slug, "spec")
    _document(dest, slug, "spec", QA_SPEC)
    _advance(dest, slug, "plan")
    _document(dest, slug, "plan", QA_PLAN)
    _advance(dest, slug, "implement")
    reports = dest / "src/reports.py"
    reports.write_text(reports.read_text().replace(QA_CODE_OLD, QA_CODE_NEW))
    _write_at(Path(_run(dest, "work", "path", slug)) / "capabilities.yaml",
              f"changed:\n  - {PROJECT_ID}.capabilities/reports/view\n")
    _round(dest, slug, "implement", QA_ROUND)
    _advance(dest, slug, "review")
    _round(dest, slug, "review", QA_REVIEW_ROUND)
    _advance(dest, slug, "qa")
    _run(dest, "work", "comment", slug, stdin=QA_PLAN_COMMENT)

    # Cases A5 and B9 work its postmortem.
    slug = items["completed"] = _new(dest, "Show an account's report",
                                     DONE_REQUEST, "--tag", "cli")
    _advance(dest, slug, "spec")
    _document(dest, slug, "spec", DONE_SPEC)
    _advance(dest, slug, "plan")
    _document(dest, slug, "plan", DONE_PLAN)
    _advance(dest, slug, "implement")
    _round(dest, slug, "implement", DONE_ROUND)
    _advance(dest, slug, "review")
    _round(dest, slug, "review", DONE_REVIEW)
    _advance(dest, slug, "qa")
    _round(dest, slug, "qa", DONE_QA)
    _advance(dest, slug, "completed")
    _run(dest, "work", "comment", slug, stdin=DONE_DEFECT)
    return items


def seed(dest: Path, variant: str = "control") -> dict:
    """Seed the fixture at `dest` and return its manifest.

    `variant` is one of `VARIANTS`. `dest` must not exist or be empty: whatever
    a used folder holds would be committed into the seeded commit. The manifest
    records the slugs the CLI minted, because they carry today's date and
    grading cannot guess them.
    """
    if variant not in VARIANTS:
        raise ValueError(f"unknown fixture variant {variant!r}; "
                         f"expected one of {VARIANTS}")
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise ValueError(f"{dest} exists and is not empty; seed into a new "
                         f"folder, since anything left there would be "
                         f"committed into the seeded commit")
    if variant == "bare":
        refuse_bare_inside_a_project(dest)
    customized = variant == "customized"
    dest.mkdir(parents=True, exist_ok=True)

    # 1. A git repo with a fixed identity, then the product source.
    _git(dest, "init", "-q")
    _git(dest, "config", "user.email", "fixture@example.invalid")
    _git(dest, "config", "user.name", "Eval Fixture")
    for rel, text in SOURCES.items():
        _write(dest, rel, text)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "demo-app: reporting and billing")

    # The bare variant stops here: a repository that does not use TCW yet.
    if variant == "bare":
        return _record(dest, {"project_id": PROJECT_ID, "variant": variant,
                              "items": {}, "stage_items": {}, "nonces": {}})

    # 2. Make it a TCW project.
    _run(dest, "init", "--id", PROJECT_ID, "taxonomy", "capabilities", "work")

    # 3. Taxonomy — two nouns and one feature over one of them.
    _run(dest, "taxonomy", "add", "Invoice",
         stdin="What an account owes for a period\n")
    _run(dest, "taxonomy", "add", "Report",
         stdin="A rendering of an account's rows\n")
    _run(dest, "taxonomy", "add", "Report Viewing", "--kind", "feature",
         "--vocab", "report", stdin="Reading a report for one account\n")

    # 4. Capabilities — one, Supported. No record is seeded `Missing`: in TCW
    #    3.0 a record is added during implement with the status it then has,
    #    and case B3 measures exactly that.
    _run(dest, "capabilities", "add", "reports/view", "View a report",
         "--status", "Supported", stdin="An account holder reads a report.\n")
    _run(dest, "capabilities", "set", "reports/view",
         "--field", "Feature=report-viewing", "--field", "Subject=report")

    # 5. Tags, before any item wants one.
    _run(dest, "work", "tags", "add", "bug", "perf", "docs", "cli")

    # 6. Documentation entries, and the files they name. Case B10 asks an agent
    #    to close out a code change against a project that declares them, so a
    #    project declaring none gives it nothing to act on — `tcw work docs`
    #    says exactly that. The trigger vocabulary is open and shape-validated
    #    only. The changelog deliberately stays one shared `upcoming.md` rather
    #    than an `upcoming/` folder: case B10 asserts the exact list of changed
    #    paths, which a file named by the agent would break.
    _write(dest, "docs/changelogs/upcoming.md",
           "# Unreleased\n\n## Added\n\n## Changed\n\n## Fixed\n")
    _declare_documentation(dest)

    # 7. The items, each left at the stage its cases act on.
    items = _seed_items(dest)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "demo-app: work items")

    manifest = {
        "project_id": PROJECT_ID,
        "variant": variant,
        "items": items,
        # Which fixture item each axis A stage case addresses: an item at that
        # stage, or, for the postmortem side stage, the completed item.
        "stage_items": {
            "spec": items["spec"],
            "plan": items["plan"],
            "implement": items["implement"],
            "review": items["review"],
            "qa": items["qa"],
            "postmortem": items["completed"],
        },
        "qa_scenarios": list(QA_SCENARIOS),
        "nonces": {},
    }

    if customized:
        manifest["nonces"] = _customize(dest, manifest["stage_items"])
        _git(dest, "add", "-A")
        _git(dest, "commit", "-q", "-m", "demo-app: bind stage instructions")
        _assert_customized(dest, manifest["stage_items"], manifest["nonces"])

    return _record(dest, manifest)


def _record(dest: Path, manifest: dict) -> dict:
    """Stamp the seeded commit into the manifest and write it beside the
    project.

    `files_changed_exactly` compares the working tree with `seeded_head` and
    counts untracked files as changes, so the manifest, which is written after
    the last commit, is excluded locally. Otherwise every run would appear to
    have added it. The bytecode and pytest caches an agent leaves just by
    importing or testing the fixture's code are excluded for the same reason.
    """
    manifest["seeded_head"] = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True).stdout.strip()
    with (dest / ".git/info/exclude").open("a") as exclude:
        exclude.write("/manifest.json\n__pycache__/\n.pytest_cache/\n")
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path, help="where to build the project")
    kind = parser.add_mutually_exclusive_group()
    kind.add_argument("--customized", action="store_true",
                      help="add the stage bindings and their nonces")
    kind.add_argument("--bare", action="store_true",
                      help="commit the code files only, with no TCW set up")
    args = parser.parse_args(argv)
    variant = ("customized" if args.customized
               else "bare" if args.bare else "control")
    manifest = seed(args.dest, variant)
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
