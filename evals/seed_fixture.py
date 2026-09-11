"""Seed one throwaway TCW node for the eval harness.

The fixture is a small fake billing/reporting product with a taxonomy, a
capability ledger, and a work store primed so that every eval case has something
real to act on. It is disposable; the instrument that reads it is not.

Two variants, one seeder, so they cannot drift apart:

* **control** — the node as a project that has configured no lifecycle
  instructions at all. Every stage falls back to TCW's built-in floor. This is
  the complement of `tests/fixtures/prompt_fallback/unconfigured.json`.
* **customized** (`--customized`, task 2) — the same node plus a
  `work.lifecycle.stages` block carrying nonce-bearing bindings.

Determinism: fixed git identity, and no timestamps in any content this module
writes. Two control runs are otherwise identical, but **not byte-identical**,
and the plan's claim that they would be was wrong. Four things vary per run, all
minted by the CLI and none controllable from here:

* the date-prefixed slugs `tcw work new` mints (stable within one day),
* the `cap-XXXXXX` id `tcw capabilities add` assigns,
* the `started` timestamp `tcw work start` records in `state.yaml`,
* the commit hashes, which follow from the timestamps.

None of them is read by grading, which queries through `tcw work list`,
`tcw work show` and `tcw capabilities show` rather than diffing trees. The
customized variant additionally differs by its nonces, which are random by
construction and recorded to `manifest.json`.

Usage:

    python evals/seed_fixture.py /tmp/probe
    python evals/seed_fixture.py --customized /tmp/probe
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tcw.store.fs import init

PROJECT_ID = "demo-app"

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

INBOX_REQUEST = """# Login is slow

Signing in takes about eight seconds for accounts with a lot of invoices. It was
fast last month. Nobody has changed the login code, so it is probably the
invoice count query running on the sign-in path.
"""

# The active item is mid-flight: spec, plan and outcome written, implementation
# committed, and a capabilities.yaml declaring a capability still sitting at
# Missing. That primes `tcw work complete` to fail closed, which is what case B3
# is there to measure.
ACTIVE_SPEC = """# Spec — Let an account download its invoice

## Problem

`compute_invoice` produces an invoice but nothing lets an account holder take it
away. Support currently reads totals down the phone.

## Capability changes

Declares `billing/download-invoice`, today `Missing`.

## Acceptance criteria

1. An account holder can download one invoice as a file.
2. The downloaded total matches `compute_invoice`.
"""

ACTIVE_PLAN = """# Plan — Let an account download its invoice

One task.

### Task 1 — Render an invoice to a downloadable file

**Modifies:** `src/billing.py`
**Proves it:** the rendered text carries the same total `compute_invoice` returns.
"""

ACTIVE_OUTCOME = """# Outcome — Let an account download its invoice

## What shipped

Task 1. `render_invoice` in `src/billing.py` formats an invoice for download,
reusing `compute_invoice` for the total rather than re-summing the line items.

## Test result

Verified by hand against a two-line invoice; the rendered total matched.

## What the plan got wrong

The plan assumed the total could be formatted inline. It could not, because
`compute_invoice` returns a mapping rather than a scalar, so the renderer takes
the mapping and reads `total` from it.
"""

# The completed item carries a defect found after the fact, which is what case
# B9 asks a post-mortem about.
DONE_SPEC = """# Spec — Show an account's report

## Problem

Nothing rendered an account's rows for a human to read.

## Acceptance criteria

1. A report lists every row with its label and amount.
"""

DONE_PLAN = """# Plan — Show an account's report

One task: add `render_report` to `src/reports.py`.
"""

DONE_OUTCOME = """# Outcome — Show an account's report

## What shipped

`render_report` in `src/reports.py`, rendering label and amount per row.

## Test result

Checked by hand against a three-row report.

## What the plan got wrong

Nothing. The task was one function.
"""

DONE_REFINED = """# Refined outcome — Show an account's report

Accepted.

## Defect found after acceptance

`render_report` assumes every row has both `label` and `amount`. A row missing
either raises `KeyError` rather than reporting which row was malformed. Reported
by support two days after the item closed.
"""


def _run(root: Path, *args: str) -> str:
    """One `tcw` verb, from the node root. Raises on a non-zero exit."""
    # `python -m tcw.cli` rather than the `tcw` console script: same interpreter
    # as the caller, so the fixture cannot be seeded by a different install than
    # the one under test, and no dependency on PATH.
    proc = subprocess.run([sys.executable, "-m", "tcw.cli", *args],
                          cwd=str(root), capture_output=True, text=True)
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


def _item_dir(root: Path, status: str, slug: str) -> Path:
    return root / "docs/work" / status / slug


def seed(dest: Path, customized: bool = False) -> dict:
    """Seed the fixture at `dest` and return its manifest.

    The manifest records the slugs the CLI minted, because they carry today's
    date and grading cannot guess them.
    """
    dest.mkdir(parents=True, exist_ok=True)

    # 1. A git repo with a fixed identity, then the product source.
    _git(dest, "init", "-q")
    _git(dest, "config", "user.email", "fixture@example.invalid")
    _git(dest, "config", "user.name", "Eval Fixture")
    for rel, text in SOURCES.items():
        _write(dest, rel, text)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "demo-app: reporting and billing")

    # 2. Make it a TCW node.
    init(["taxonomy", "capabilities", "work"], dest, project_id=PROJECT_ID)

    # 3. Taxonomy — two nouns and one feature over one of them.
    _run(dest, "taxonomy", "add", "Invoice", "What an account owes for a period")
    _run(dest, "taxonomy", "add", "Report", "A rendering of an account's rows")
    _run(dest, "taxonomy", "add", "Report Viewing",
         "Reading a report for one account", "--kind", "feature",
         "--vocab", "report")

    # 4. Capabilities — one Supported, one Missing.
    _run(dest, "capabilities", "add", "reports/view", "View a report",
         "--status", "Supported")
    _run(dest, "capabilities", "set", "reports/view",
         "--field", "Feature=report-viewing", "--field", "Subject=report")
    _run(dest, "capabilities", "add", "billing/download-invoice",
         "Download an invoice", "--status", "Missing")
    _run(dest, "capabilities", "set", "billing/download-invoice",
         "--field", "Subject=invoice")

    # 5. Tags, before any item wants one.
    _run(dest, "work", "tags", "add", "bug", "perf", "docs", "cli")

    # 6. A plain backlog item. Cases A1 and A2 use it: `spec` and `plan` are
    #    legal only in `backlog`.
    backlog_slug = _run(dest, "work", "new", "Let an account export its report",
                        "--tag", "cli", "--priority", "40")

    # 7. The mid-flight active item. Cases A3 and A4 use it: `implement` needs
    #    `active`, and `verify` needs `active` or `review` *and* an outcome to
    #    read.
    active_slug = _run(dest, "work", "new", "Let an account download its invoice",
                       "--tag", "cli", "--priority", "60")
    d = _item_dir(dest, "backlog", active_slug)
    (d / "spec.md").write_text(ACTIVE_SPEC)
    (d / "plan.md").write_text(ACTIVE_PLAN)
    (d / "capabilities.yaml").write_text("new:\n  - billing/download-invoice\n")
    _run(dest, "capabilities", "set", "billing/download-invoice",
         "--field", f"Planning doc={active_slug}")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", f"tcw work: {active_slug} spec and plan")
    _run(dest, "work", "start", active_slug)

    # The implementation, committed, then the outcome. The ledger stays at
    # Missing on purpose: that is what makes `tcw work complete` fail closed.
    billing = dest / "src/billing.py"
    billing.write_text(billing.read_text() + '''

def render_invoice(account_id: str, line_items: list[dict]) -> str:
    """Render an invoice for download."""
    invoice = compute_invoice(account_id, line_items)
    lines = [f"Invoice for {account_id}"]
    for item in line_items:
        lines.append(f"  {item['label']:<20} {item['amount']:>10}")
    lines.append(f"  {'TOTAL':<20} {invoice['total']:>10}")
    return "\\n".join(lines)
''')
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "billing: render an invoice for download")
    _write(dest, f"docs/work/active/{active_slug}/outcome.md", ACTIVE_OUTCOME)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", f"tcw work: {active_slug} outcome")

    # 8. An untriaged inbox request, for case B2.
    _write(dest, "docs/work/inbox/slow-login.md", INBOX_REQUEST)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "demo-app: an untriaged inbox request")

    # 9. A completed item carrying a defect found after the fact, for case B9.
    #    Case A5 uses it too: `postmortem` needs `review` or `completed`.
    done_slug = _run(dest, "work", "new", "Show an account's report",
                     "--tag", "cli", "--priority", "30")
    d = _item_dir(dest, "backlog", done_slug)
    (d / "spec.md").write_text(DONE_SPEC)
    (d / "plan.md").write_text(DONE_PLAN)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", f"tcw work: {done_slug} spec and plan")
    _run(dest, "work", "start", done_slug)
    _write(dest, f"docs/work/active/{done_slug}/outcome.md", DONE_OUTCOME)
    _write(dest, f"docs/work/active/{done_slug}/refined-outcome.md", DONE_REFINED)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", f"tcw work: {done_slug} outcome")
    _run(dest, "work", "complete", done_slug, "--resolution", "done", "--confirm")

    manifest = {
        "project_id": PROJECT_ID,
        "variant": "customized" if customized else "control",
        "items": {
            "backlog": backlog_slug,
            "active": active_slug,
            "completed": done_slug,
        },
        # Which fixture item each axis A stage case must address, since stage
        # legality (`STAGE_STATUSES`) restricts every one of them.
        "stage_items": {
            "spec": backlog_slug,
            "plan": backlog_slug,
            "implement": active_slug,
            "verify": active_slug,
            "postmortem": done_slug,
        },
        "nonces": {},
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path, help="where to build the node")
    parser.add_argument("--customized", action="store_true",
                        help="add the lifecycle bindings and their nonces")
    args = parser.parse_args(argv)
    manifest = seed(args.dest, customized=args.customized)
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
