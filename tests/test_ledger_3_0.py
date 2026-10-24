"""This repository's own ledger after TCW-73 (AC 21).

The capability records TCW-73 declares new exist and are not `Missing`, the
ones it removes are gone, and nothing still names the retired `node` term or
the `connected-project-registry` feature.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from tests.statefiles import record_file, record_files

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
CAPABILITIES = DOCS / "capabilities"
TAXONOMY = DOCS / "taxonomy"

NEW = ("cli/rely-on-one-output-contract", "cli/list-connected-projects",
       "cli/validate-a-project",
       "work/declare-capability-changes-in-a-child-projects-ledger")
REMOVED = ("cli/use-shorthand-to-read-an-item", "cli/validate-a-node",
           "work/inspect-the-node-topology",
           "work/declare-capability-changes-in-a-child-nodes-ledger")
RETIRED_ENTRIES = ("node", "connected-project-registry")


def check_new(docs: Path, path: str) -> None:
    meta = yaml.safe_load(record_file(docs / "capabilities" / path, "capabilities")
                          .read_text())
    assert meta.get("Status") not in (None, "Missing"), meta


def check_removed(docs: Path, path: str) -> None:
    assert not (docs / "capabilities" / path).exists()


def check_retired(docs: Path, entry: str) -> None:
    assert not (docs / "taxonomy" / entry).exists()


def check_new_entries(docs: Path) -> None:
    assert record_file(docs / "taxonomy" / "project", "taxonomy").is_file()
    assert record_file(docs / "taxonomy" / "project-registry", "taxonomy").is_file()


def check_no_retired_name(docs: Path) -> None:
    word = re.compile(r"\b(node|connected-project-registry)\b")
    found = [str(meta.relative_to(docs)) for meta in
             record_files(docs / "capabilities", "capabilities")
             if word.search(meta.read_text(encoding="utf-8"))]
    assert not found, found


@pytest.mark.parametrize("path", NEW)
def test_a_new_record_exists_and_is_not_missing(path):
    check_new(DOCS, path)


@pytest.mark.parametrize("path", REMOVED)
def test_a_removed_record_is_gone(path):
    check_removed(DOCS, path)


@pytest.mark.parametrize("entry", RETIRED_ENTRIES)
def test_a_retired_taxonomy_entry_is_gone(entry):
    check_retired(DOCS, entry)


def test_the_new_taxonomy_entries_exist():
    check_new_entries(DOCS)


def test_no_record_names_a_retired_entry():
    check_no_retired_name(DOCS)


def test_every_check_holds_on_the_records_in_4_0_form(tmp_path):
    from tests.migrate.fixtures import as_4_0_records
    docs = as_4_0_records(DOCS, tmp_path / "docs")
    assert not list(docs.rglob("meta.yaml"))
    for path in NEW:
        check_new(docs, path)
    for path in REMOVED:
        check_removed(docs, path)
    for entry in RETIRED_ENTRIES:
        check_retired(docs, entry)
    check_new_entries(docs)
    check_no_retired_name(docs)
    # The copy really is read: a retired name planted in a record is found.
    planted = record_files(docs / "capabilities", "capabilities")[0]
    planted.write_text(planted.read_text() + "# node\n")
    with pytest.raises(AssertionError):
        check_no_retired_name(docs)
