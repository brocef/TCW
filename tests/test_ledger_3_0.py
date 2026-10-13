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

REPO = Path(__file__).resolve().parent.parent
CAPABILITIES = REPO / "docs" / "capabilities"
TAXONOMY = REPO / "docs" / "taxonomy"

NEW = ("cli/rely-on-one-output-contract", "cli/list-connected-projects",
       "cli/validate-a-project",
       "work/declare-capability-changes-in-a-child-projects-ledger")
REMOVED = ("cli/use-shorthand-to-read-an-item", "cli/validate-a-node",
           "work/inspect-the-node-topology",
           "work/declare-capability-changes-in-a-child-nodes-ledger")
RETIRED_ENTRIES = ("node", "connected-project-registry")


@pytest.mark.parametrize("path", NEW)
def test_a_new_record_exists_and_is_not_missing(path):
    meta = yaml.safe_load((CAPABILITIES / path / "meta.yaml").read_text())
    assert meta.get("Status") not in (None, "Missing"), meta


@pytest.mark.parametrize("path", REMOVED)
def test_a_removed_record_is_gone(path):
    assert not (CAPABILITIES / path).exists()


@pytest.mark.parametrize("entry", RETIRED_ENTRIES)
def test_a_retired_taxonomy_entry_is_gone(entry):
    assert not (TAXONOMY / entry).exists()


def test_the_new_taxonomy_entries_exist():
    assert (TAXONOMY / "project" / "meta.yaml").is_file()
    assert (TAXONOMY / "project-registry" / "meta.yaml").is_file()


def test_no_record_names_a_retired_entry():
    word = re.compile(r"\b(node|connected-project-registry)\b")
    found = [str(meta.relative_to(REPO)) for meta in CAPABILITIES.rglob("meta.yaml")
             if word.search(meta.read_text(encoding="utf-8"))]
    assert not found, found
