"""Where a work item's files live, and what its verdict rounds say.

An item's folder is created by its backend and never moved or deleted by TCW.
Inside it, each stage that has an artifact gets a folder named after the stage:
a document stage holds `<stage>.md`, a rounds stage holds numbered
`round-N.md` files, and any stage may hold timestamped handoffs. The records an
item declares it changes sit at the item's root, in `capabilities.yaml`.

Every path is computed here, and nothing here creates a file or a folder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tcw.errors import Refused, UsageError
from tcw.work.model import DOCUMENT, NO_ARTIFACT, ROUNDS, Slug, Stage, stage as table_stage

ROUND_NAME = re.compile(r"^round-([1-9][0-9]*)\.md$")
HANDOFF_NAME = re.compile(r"^handoff-\d{8}T\d{6}Z\.md$")
CAPABILITIES_FILE = "capabilities.yaml"

ACCEPTED, REJECTED, INVALID = "accepted", "rejected", "invalid"
NO_ROUNDS, STALE = "none", "stale"


@dataclass(frozen=True)
class Verdict:
    state: str  # accepted, rejected or invalid
    judges: int | None  # the implementation round it judged; None when invalid


_INVALID = Verdict(INVALID, None)


def _front_matter(text: str) -> object:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for end, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return yaml.safe_load("\n".join(lines[1:end]))
    return None


def round_verdict(path: Path) -> Verdict:
    """The verdict a round's front matter records, or `invalid` for anything
    that is not exactly `verdict: accepted|rejected` and a non-negative
    whole-number `judges`."""
    try:
        meta = _front_matter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return _INVALID
    if not isinstance(meta, dict):
        return _INVALID
    state, judges = meta.get("verdict"), meta.get("judges")
    if state not in (ACCEPTED, REJECTED):
        return _INVALID
    if isinstance(judges, bool) or not isinstance(judges, int) or judges < 0:
        return _INVALID
    return Verdict(state, judges)


@dataclass(frozen=True)
class Layout:
    """Paths for one project's items. `enabled` is the project's enabled
    stages; `external` the stages whose record the backend keeps elsewhere;
    `backend` names that backend in refusals."""

    work_root: Path
    enabled: frozenset[str]
    external: frozenset[str]
    backend: str = "the work backend"

    # -- plain paths --------------------------------------------------------

    def item_dir(self, slug: Slug) -> Path:
        return self.work_root / slug.folder

    def stage_dir(self, slug: Slug, stage: str) -> Path:
        return self.item_dir(slug) / table_stage(stage).name

    def document(self, slug: Slug, stage: str) -> Path:
        return self.stage_dir(slug, stage) / f"{stage}.md"

    def capabilities_file(self, slug: Slug) -> Path:
        return self.item_dir(slug) / CAPABILITIES_FILE

    # -- rounds -------------------------------------------------------------

    def rounds(self, slug: Slug, stage: str) -> list[tuple[int, Path]]:
        """The stage's rounds in order. Files that are not `round-N.md` are
        not rounds; gaps in the numbering are allowed."""
        folder = self.stage_dir(slug, stage)
        if not folder.is_dir():
            return []
        found = []
        for entry in folder.iterdir():
            match = ROUND_NAME.match(entry.name)
            if match and entry.is_file():
                found.append((int(match.group(1)), entry))
        return sorted(found)

    def latest_round(self, slug: Slug, stage: str) -> tuple[int, Path] | None:
        found = self.rounds(slug, stage)
        return found[-1] if found else None

    def next_round(self, slug: Slug, stage: str) -> Path:
        """One past the highest round. Computed, not reserved: two writers on
        two branches can both pick it, and git settles that when they meet."""
        latest = self.latest_round(slug, stage)
        number = latest[0] + 1 if latest else 1
        return self.stage_dir(slug, stage) / f"round-{number}.md"

    def current_verdict(self, slug: Slug, stage: str) -> str:
        """`none`, `invalid`, `stale`, `accepted` or `rejected`.

        `stale` means the latest round judged an implementation round older
        than the current one: the work changed after the verdict was written.
        Only `accepted` lets work go forward.
        """
        latest = self.latest_round(slug, stage)
        if latest is None:
            return NO_ROUNDS
        verdict = round_verdict(latest[1])
        if verdict.state == INVALID:
            return INVALID
        judged = table_stage(stage).on_reject
        current = self.latest_round(slug, judged) if judged else None
        if verdict.judges != (current[0] if current else 0):
            return STALE
        return verdict.state

    # -- handoffs -----------------------------------------------------------

    def handoff_path(self, slug: Slug, stage: str, now: datetime) -> Path:
        stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.stage_dir(slug, stage) / f"handoff-{stamp}.md"
        if path.exists():
            raise Refused(f"{path} already exists; wait a second and ask again "
                          f"so no handoff is overwritten")
        return path

    def latest_handoff(self, slug: Slug, stage: str) -> Path | None:
        folder = self.stage_dir(slug, stage)
        if not folder.is_dir():
            return None
        names = sorted(e.name for e in folder.iterdir()
                       if HANDOFF_NAME.match(e.name) and e.is_file())
        return folder / names[-1] if names else None

    # -- the path a caller asks for ------------------------------------------

    def _checked(self, name: str) -> Stage:
        row = table_stage(name)
        if name not in self.enabled:
            raise UsageError(f"{name} is disabled in this project")
        if row.artifact == NO_ARTIFACT:
            raise Refused(f"{name} has no files: nothing is written for it")
        if name in self.external:
            raise Refused(f"{name} is kept in {self.backend}, not in the item "
                          f"folder")
        return row

    def path(self, slug: Slug, stage: str | None = None, *, next: bool = False,
             handoff: bool = False, now: datetime | None = None) -> Path:
        """The item folder; a stage's document or folder; the next round
        (`next`); or a new handoff for the current second (`handoff`)."""
        if next and handoff:
            raise UsageError("ask for the next round or a handoff, not both")
        if stage is None:
            if next or handoff:
                raise UsageError("name the stage for a round or a handoff")
            return self.item_dir(slug)
        row = self._checked(stage)
        if handoff:
            return self.handoff_path(slug, stage,
                                     now or datetime.now(timezone.utc))
        if next:
            if row.artifact != ROUNDS:
                raise UsageError(f"{stage} has one document, not rounds")
            return self.next_round(slug, stage)
        if row.artifact == DOCUMENT:
            return self.document(slug, stage)
        return self.stage_dir(slug, stage)
