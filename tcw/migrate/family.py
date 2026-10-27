"""The active project's related projects, read in either format and never
written (TCW-116 Design 1.3, 6.1, 6.5, 6.6; plan Step 16).

3.x found a related project through the `projects:` entries of the projects
around it (`legacy.locate_3x`), and 4.0 will find it through the manifests a
migration writes and its search. A migration needs to know where each one is
for every entry it converts, and needs its content only for some
conversions: telling E1 from E4, resolving an override pointer into it, or
finding the owner of a bare reference. So a related project is placed
without being read, and read only when a conversion asks for it
(`Family.member`); one that is asked for and is not on this machine is B5,
with Design 6.5's message.

A related project still in 3.x form is read as 3.x read it; one already
migrated is read as it is now. The 4.0 links a 3.x one will have once it is
migrated are `Family.predicted`, which `config.predict_links` fills.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tcw.migrate import legacy
from tcw.migrate.legacy import Relation3, RepoDecl3
from tcw.migrate.model import Blocker
from tcw.project_files import SENTINEL, VERSION_KEY, without_version


@dataclass
class Member:
    """One project of the family as a migration reads it: its folder, its
    format, and its shared configuration (`raw`, without the version line of
    a 4.0 file)."""

    id: str
    folder: Path
    form: str                       # "3.x" or "4.0"
    raw: dict
    how: str                        # how it was placed: active, locator, ...

    @property
    def three_x(self) -> bool:
        return self.form == "3.x"

    def relations(self) -> list[Relation3]:
        """Its 3.x `projects:` entries; none for a 4.0 project."""
        return legacy.relations_3x(self.raw, ".")[0] if self.three_x else []


@dataclass(frozen=True)
class Placed:
    """Where a related project is, on this machine or not: the folder 3.x
    placed it at, how, the entry that named it and the project whose entry
    it is."""

    id: str
    folder: Path
    how: str                        # locator, repository, variable or absent
    relation: Relation3
    declared_by: str

    @property
    def here(self) -> bool:
        return self.how != "absent"


def absent_project_message(project: str, folder: Path,
                           repository: RepoDecl3 | None) -> str:
    """Design 6.5's B5 message for a related project this run must read and
    that is not on this machine. Every command but `tcw migrate` is refused
    in a 3.x project, `tcw project provision` included, so the fetch is
    spelled out as the clone itself, and `tcw project provision` is named
    for after the migration (Decided 23)."""
    if repository is not None:
        source = repository.url + (f" (at {repository.ref})" if repository.ref else "")
        fetch = f"fetch it with 'git clone {source} {folder}'"
    else:
        fetch = f"put the project at {folder}"
    return (f"project '{project}' is not on this machine, and this run must read it; "
            f"{fetch}, then run 'tcw migrate' again; once this project is migrated, "
            f"'tcw project provision' fetches every related project its manifests name")


def read_member(project_id: str, folder: Path, how: str) -> Member | None:
    """The project at `folder` in whichever form it is in, or None when it
    holds neither form. A 3.x project is read by `legacy.read_3x_layers`, a
    4.0 one by its `.tcw/tcw-config.yaml`."""
    if (folder / legacy.ROOT_CONFIG).is_file():
        layers = legacy.read_3x_layers(folder)
        return Member(project_id, folder, "3.x", layers.shared.data or {}, how)
    if (folder / SENTINEL).is_file():
        layer = legacy.read_layer_3x(folder / SENTINEL, "shared")
        data = layer.data or {}
        if VERSION_KEY not in data:
            return Member(project_id, folder, "3.x", data, how)
        return Member(project_id, folder, "4.0", without_version(data), how)
    return None


@dataclass
class Family:
    """The active project and what it can learn of its related projects."""

    active: Member
    placed: dict[str, Placed] = field(default_factory=dict)
    read: dict[str, Member] = field(default_factory=dict)
    blockers: list[Blocker] = field(default_factory=list)
    #: The 4.0 parent links each 3.x project of the family will have once it
    #: is migrated, by ID (Design 6.1); `config.predict_links` fills it.
    predicted: dict[str, list] = field(default_factory=dict)

    def place(self, project_id: str) -> Placed | None:
        """Where a project the active project's entries name is, without
        reading it; None for an ID no entry names."""
        return self.placed.get(project_id)

    def member(self, project_id: str, why: str, where: str) -> Member | None:
        """The related project `project_id`, read, for a conversion that must
        read it (`why`, the conversion's code; `where`, the file it is in).
        A project that is placed but not here, or that holds no project, is
        B5, recorded once; one that no entry names and the 3.x graph does not
        reach is None, which the caller reports."""
        if project_id == self.active.id:
            return self.active
        if project_id in self.read:
            return self.read[project_id]
        placed = self.placed.get(project_id) or self._walk_to(project_id)
        if placed is None:
            return None
        found = read_member(project_id, placed.folder, placed.how) if placed.here else None
        if found is None:
            self._absent(placed, why, where)
            return None
        self.read[project_id] = found
        return found

    def quiet(self, project_id: str) -> Member | None:
        """`member` for a reading that can go without: the project read when
        it is here, else None, with no B5."""
        if project_id == self.active.id:
            return self.active
        if project_id in self.read:
            return self.read[project_id]
        placed = self.placed.get(project_id) or self._walk_to(project_id)
        if placed is None or not placed.here:
            return None
        found = read_member(project_id, placed.folder, placed.how)
        if found is not None:
            self.read[project_id] = found
        return found

    def base_of(self, placed: Placed) -> Path:
        """The folder of the project whose entry placed `placed`."""
        if placed.declared_by == self.active.id:
            return self.active.folder
        declarer = self.read.get(placed.declared_by)
        return declarer.folder if declarer is not None else self.active.folder

    def _absent(self, placed: Placed, why: str, where: str) -> None:
        detail = absent_project_message(placed.id, placed.folder,
                                        placed.relation.repository)
        blocker = Blocker("B5", where, f"{why}: {detail}",
                          "fetch the project as the line says, then run 'tcw migrate' again")
        if blocker not in self.blockers:
            self.blockers.append(blocker)

    def _walk_to(self, project_id: str) -> Placed | None:
        """3.x's registry walk (`_visit` and `_follow_edges`,
        `tcw/store/project.py:476-551` at v3.0.2), made only as far as it
        takes to reach `project_id`: from each project reached across a
        `parent` or `children` entry, every entry it holds; from one reached
        across an `upstream` entry, nothing. Each project the walk passes
        through is read."""
        from tcw.store.project import worktree_anchors
        anchors = worktree_anchors(self.active.folder)
        frontier = [p for p in self.placed.values() if p.relation.kind != "upstream"]
        seen = {self.active.id, *self.placed}
        while frontier:
            step = frontier.pop(0)
            if not step.here:
                continue
            member = self.read.get(step.id) or read_member(step.id, step.folder, step.how)
            if member is None:
                continue
            self.read[step.id] = member
            for relation, folder, how in _edges(member, anchors):
                if relation.id in seen:
                    continue
                seen.add(relation.id)
                placed = Placed(relation.id, folder, how, relation, member.id)
                self.placed[relation.id] = placed
                if relation.id == project_id:
                    return placed
                if relation.kind != "upstream":
                    frontier.append(placed)
        return None


def declared_id(folder: Path) -> str | None:
    """The `id` the project at `folder` declares, in either form, or None
    when it holds no project or its file cannot be read."""
    for name in (legacy.ROOT_CONFIG, SENTINEL):
        path = Path(folder) / name
        if path.is_file():
            data = legacy.read_layer_3x(path, "shared").data
            value = data.get("id") if isinstance(data, dict) else None
            return value if isinstance(value, str) else None
    return None


def search_4(folder: Path, project_id: str,
             anchors: "tuple[Path, Path] | None | bool" = True) -> list[Path]:
    """4.0's search for `project_id` from the project at `folder` (TCW-107
    Design 2.4, 2.5): the folders next to it, then those enclosing it, that
    declare the ID, in either form, since a related project may not be
    migrated yet. Every match of the first round that has one is kept; the
    rounds, read from the main checkout inside a linked worktree, are the
    ones 4.0 searches (`search_rounds`).

    `anchors` is the linked worktree of the active project, the one 4.0
    runs from, as `worktree_anchors` gives it (None for none), or True when
    the project at `folder` is the active one, to probe `folder`: 4.0 reads
    every project's search through the active project's worktree."""
    from tcw.store.project import search_rounds, worktree_anchors
    folder = Path(folder)
    if anchors is True:
        anchors = worktree_anchors(folder)
    for holder, own, enclosing in search_rounds(folder, anchors):
        try:
            beside = sorted(p for p in holder.iterdir()
                            if p.is_dir() and p != own and p.name != ".tcw")
        except OSError:
            beside = []
        found = [c for c in (*beside, *enclosing) if declared_id(c) == project_id]
        if found:
            return found
    return []


def manifest_entries_4(folder: Path) -> dict[str, tuple[Path, Any]]:
    """The entries of the 4.0 project at `folder`'s two manifests, the
    personal one's first: each ID to the folder it names and the entry."""
    import yaml
    from tcw.project_files import LOCAL_MANIFEST, MANIFEST
    from tcw.store.manifest import parse_manifest
    out: dict[str, tuple[Path, Any]] = {}
    for rel, personal in ((LOCAL_MANIFEST, True), (MANIFEST, False)):
        path = Path(folder) / rel
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        entries, problems = parse_manifest(data, path, personal=personal)
        for project_id, entry in entries.items():
            target = Path(entry.path).expanduser()
            target = target if target.is_absolute() else Path(folder) / target
            out.setdefault(project_id, (Path(_normal(target)), entry))
    return out


def _normal(path: Path) -> str:
    import os
    return os.path.normpath(path)


def _edges(member: Member, anchors: tuple[Path, Path] | None
           ) -> list[tuple[Relation3, Path, str]]:
    """Each project `member` names, with where it is: a 3.x project's
    `projects:` entries placed as 3.x placed them; a 4.0 project's
    `parents:` and `children:` placed as 4.0 places them, by its manifests
    and then its search, reading each candidate in either form, a parent
    standing for a `parent` entry, the search made through `anchors`, the
    active project's linked worktree. One neither places is absent, at the
    folder next to `member` the search would have tried first."""
    if member.three_x:
        return [(r, *legacy.locate_3x(member.folder, r)) for r in member.relations()]
    from tcw.store.links import parse_children, parse_parents
    links = parse_parents(member.raw.get("parents"), ".")[0] or []
    children = parse_children(member.raw.get("children"), ".", own_id=member.id)[0]
    named = [("children", c) for c in children] + [("parent", link.id) for link in links]
    entries = manifest_entries_4(member.folder)
    out = []
    for kind, project_id in named:
        folder, how = member.folder.parent / project_id, "absent"
        if project_id in entries and legacy.holds_project(entries[project_id][0]):
            folder, how = entries[project_id][0], "manifest"
        elif project_id not in entries:
            found = search_4(member.folder, project_id, anchors)
            if len(found) == 1:
                folder, how = found[0], "search"
        elif project_id in entries:
            folder = entries[project_id][0]
        out.append((Relation3(kind, project_id), folder, how))
    return out


def read_family(root: Path, project_id: str, mapping: dict[str, Any]) -> Family:
    """The active project at `root`, with `mapping` its shared configuration
    in either form, and every project its own `projects:` entries name,
    placed where 3.x placed it and not yet read."""
    active = Member(project_id, Path(root), "3.x", mapping, "active")
    family = Family(active)
    for relation in active.relations():
        folder, how = legacy.locate_3x(root, relation)
        family.placed.setdefault(relation.id,
                                 Placed(relation.id, folder, how, relation, project_id))
    return family
