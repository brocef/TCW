"""An item's files: documents, rounds, handoffs and the declaration file.

Only the paths the layout names are files here, and only for enabled stages
whose record is kept in the item folder. Everything else in the folder is
the backend's storage or not part of the model, and is not found.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from tcw.work.layout import HANDOFF_NAME, round_verdict
from tcw.work.model import DOCUMENT, NO_ARTIFACT, ROUNDS, STAGES, Slug


def revision(path: Path) -> str | None:
    """The SHA-256 of the file's bytes, or None when there is no file."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return None


def file_stages(context) -> list:
    """The stage rows whose files live in the item folder: enabled, with an
    artifact, and not kept by the backend. In table order."""
    return [row for row in STAGES
            if row.name in context.config.enabled and row.artifact != NO_ARTIFACT
            and row.name not in context.backend.external_stages]


def _handoffs(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted((e for e in folder.iterdir()
                   if HANDOFF_NAME.match(e.name) and e.is_file()),
                  key=lambda e: e.name)


def _entry(item_dir: Path, path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(item_dir).as_posix(), "revision": revision(path)}


def listing(context, slug: Slug) -> list[dict[str, Any]]:
    """Every file the item may have, read from disk alone: per stage its
    document or its rounds, and its handoffs; then the declaration file.
    Needs no backend read, so it answers while the backend cannot."""
    layout = context.layout
    item_dir = layout.item_dir(slug)
    found: list[dict[str, Any]] = []
    for row in file_stages(context):
        entry: dict[str, Any] = {"stage": row.name, "artifact": row.artifact,
                                 "verdict": row.verdict}
        if row.artifact == DOCUMENT:
            document = layout.document(slug, row.name)
            entry["document"] = {**_entry(item_dir, document),
                                 "present": document.is_file()}
        elif row.artifact == ROUNDS:
            rounds = []
            for number, path in reversed(layout.rounds(slug, row.name)):
                one = {**_entry(item_dir, path), "number": number}
                if row.verdict:
                    one["verdict"] = round_verdict(path).state
                rounds.append(one)
            entry["rounds"] = rounds
        entry["handoffs"] = [_entry(item_dir, p) for p in
                             reversed(_handoffs(layout.stage_dir(slug, row.name)))]
        found.append(entry)
    declaration = layout.capabilities_file(slug)
    found.append({"stage": None, "artifact": "declaration",
                  "document": {**_entry(item_dir, declaration),
                               "present": declaration.is_file()}})
    return found


def verdicts(context, slug: Slug) -> list[dict[str, str]]:
    """`current_verdict` for each verdict stage whose rounds are on disk."""
    return [{"stage": row.name,
             "verdict": context.layout.current_verdict(slug, row.name)}
            for row in file_stages(context) if row.verdict]


ROUTES: list = []
