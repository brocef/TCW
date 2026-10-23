"""Full identifiers and `tcw://` addresses (TCW-110 Design 1 and 2).

Every taxonomy entry, capability and work item has one name, its **full
identifier**, `<project>.<namespace>/<id-path>`: the project that owns it,
which of the three namespaces it is in, and its path among its store's
folders. The same name after `tcw://` is its **address**, the form a Markdown
link holds. A **folder address**, `tcw://<project>[.<namespace>].path/<folder>`,
names a folder on disk instead: a project's root, or one of its stores.

The grammar, in the notation of the spec:

    full-id    = project-id "." namespace "/" id-path
    namespace  = "taxonomy" / "capabilities" / "work"
    id-path    = id-part *( "/" id-part )
    id-part    = ( A-Z / a-z / 0-9 ) *( A-Z / a-z / 0-9 / "-" / "_" ), at most 128

    object-address = "tcw://" full-id
    folder-address = "tcw://" project-id [ "." namespace ] ".path" "/" [ folder-path ]
    folder-part    = 1*( A-Z / a-z / 0-9 / "-" / "_" / "." / "~" ), not "." or ".."

Neither a project ID nor an id-part may hold a `.`, so text whose part before
its first `/` holds a `.` is a full identifier, and any other text is an
id-path (Design 1.2). A parser needs no list of projects to tell them apart.

This module reads no disk and imports nothing from the store or work layers,
so every layer can use it. It is the one place an identifier is parsed or
printed, and the one place a TCW 3.x reference is recognised (Design 2.4).
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from typing import Any

from tcw.errors import UsageError
from tcw.project_files import PROJECT_ID_PATTERN, RESERVED_PROJECT_IDS

NAMESPACES = ("taxonomy", "capabilities", "work")
ID_PART_LIMIT = 128
ID_PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
FOLDER_PART = re.compile(r"[A-Za-z0-9._~-]+")
SCHEME = "tcw://"

_ID_PART_RULE = (f"letters, digits, '-' and '_', starting with a letter or "
                 f"digit, at most {ID_PART_LIMIT} characters")
_PROJECT_RULE = "lowercase letters and digits joined by single hyphens"
_FOLDER_RULE = "letters, digits, '-', '_', '.' and '~'"
#: The characters an address may hold at all; anything else (`%`, `?`, `#`,
#: a space, `:`, `@`) would be read by a URL parser as something other than
#: part of the path.
_ADDRESS_CHARACTERS = re.compile(r"[A-Za-z0-9._~/-]*")
#: The TCW 3.x link shape `tcw://[<project>/]<axis>/<ref>` (Design 2.4).
_THREE_X_ADDRESS = re.compile(r"tcw://(?:[^/.]+/)?[TCW]/\S+")

MIGRATE_HINT = "run 'tcw migrate' in this project"


class IdError(UsageError):
    """Text that should name an object or a folder does not (exit 2)."""


class MalformedId(IdError):
    """Text that breaks the grammar of a full identifier or an address."""


class ThreeXReference(IdError):
    """A TCW 3.x reference: recognised, never resolved (Design 2.4, 5.2)."""


@functools.total_ordering
@dataclass(frozen=True, eq=False, order=False)
class FullId:
    """One object's full identifier: owner, namespace and id-path.

    The constructor does not check the grammar, so an existing folder whose
    name breaks it can still be printed (Design 1.6); only the parsers refuse.

    Equality, hashing and order are those of `(project, namespace, id_path)`
    whatever the class, so a work model `Slug` (a subclass) and a `FullId`
    parsed from text for the same item are equal and hash the same.
    """

    project: str
    namespace: str
    id_path: str

    def _key(self) -> tuple[str, str, str]:
        return (self.project, self.namespace, self.id_path)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FullId):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, FullId):
            return NotImplemented
        return self._key() < other._key()

    def __str__(self) -> str:
        return f"{self.project}.{self.namespace}/{self.id_path}"

    def address(self) -> str:
        return SCHEME + str(self)

    @property
    def parts(self) -> list[str]:
        """The id-path's folder names: the one place an id-path is split for
        a caller."""
        return self.id_path.split("/")

    def with_id_path(self, id_path: str) -> FullId:
        return FullId(self.project, self.namespace, id_path)


@dataclass(frozen=True)
class FolderAddress:
    """`tcw://<project>[.<namespace>].path/<folder_path>`: a folder on disk,
    in a project's root or in one of its stores. `folder_path` is kept as
    written, a trailing `/` included, so `str()` gives its one spelling."""

    project: str
    namespace: str | None
    folder_path: str

    def __str__(self) -> str:
        scope = f".{self.namespace}" if self.namespace else ""
        return f"{SCHEME}{self.project}{scope}.path/{self.folder_path}"

    @property
    def parts(self) -> list[str]:
        """The folder path's parts, with no empty part for a trailing `/`."""
        rest = self.folder_path.rstrip("/")
        return rest.split("/") if rest else []


def same_target(a: FolderAddress, b: FolderAddress) -> bool:
    """Whether two folder addresses name one folder: their text is equal,
    except that a trailing `/` is ignored (Design 2.3)."""
    return (a.project, a.namespace, a.parts) == (b.project, b.namespace, b.parts)


def is_project_id(text: Any) -> bool:
    """Whether `text` is a valid project ID that is not reserved."""
    return (isinstance(text, str) and PROJECT_ID_PATTERN.fullmatch(text) is not None
            and text not in RESERVED_PROJECT_IDS)


def looks_full(text: str) -> bool:
    """Design 1.2: a `.` before the first `/` marks a full identifier."""
    return "." in text.partition("/")[0]


def _check_project(project: str, text: str) -> None:
    if not PROJECT_ID_PATTERN.fullmatch(project):
        raise MalformedId(
            f"{text!r} is not a full identifier: {project!r} is not a project "
            f"ID ({_PROJECT_RULE})")
    if project in RESERVED_PROJECT_IDS:
        raise MalformedId(
            f"{text!r} is not a full identifier: {project!r} is a reserved "
            f"project ID and names no project")


def _check_namespace(namespace: str, text: str) -> None:
    if namespace not in NAMESPACES:
        raise MalformedId(
            f"{text!r} is not a full identifier: {namespace!r} is not a "
            f"namespace (one of {', '.join(NAMESPACES)})")


def id_path_problem(id_path: str) -> str | None:
    """Why `id_path` breaks Design 1.1, or None when it is a valid id-path."""
    if not id_path:
        return "it has no id-path"
    for part in id_path.split("/"):
        if not part:
            return "an id-path has no empty part ('//' or a '/' at an end)"
        if len(part) > ID_PART_LIMIT:
            return (f"the id-part {part[:20]!r}... is longer than "
                    f"{ID_PART_LIMIT} characters")
        if not ID_PART.fullmatch(part):
            return f"the id-part {part!r} breaks the rule: {_ID_PART_RULE}"
    return None


def id_part_problem(part: str) -> str | None:
    """Why one folder name breaks Design 1.1's id-part rule, or None."""
    if "/" in part:
        return f"{part!r} holds a '/'"
    return id_path_problem(part)


def parse_full_id(text: Any, namespace: str | None = None) -> FullId:
    """`<project>.<namespace>/<id-path>`, by Design 1.1. With `namespace`, an
    identifier of another namespace is refused naming the one expected."""
    if not isinstance(text, str) or not text:
        raise MalformedId(f"{text!r} is not a full identifier")
    head, slash, id_path = text.partition("/")
    pieces = head.split(".")
    if not slash or len(pieces) != 2:
        raise MalformedId(
            f"{text!r} is not a full identifier: write "
            f"<project>.<namespace>/<id-path>, such as demo.work/<folder>")
    project, found = pieces
    _check_project(project, text)
    _check_namespace(found, text)
    if namespace is not None and found != namespace:
        raise MalformedId(
            f"{text!r} names a {found} object; this command takes a "
            f"{namespace} object ({namespace} namespace)")
    problem = id_path_problem(id_path)
    if problem:
        raise MalformedId(f"{text!r} is not a full identifier: {problem}")
    return FullId(project, found, id_path)


def is_3x_address(text: Any) -> bool:
    """Design 2.4: `tcw://[<project>/]<axis>/<ref>`, with no `.` before the
    first `/` after the scheme, an axis of T, C or W and a non-empty ref."""
    if not isinstance(text, str) or not text.startswith(SCHEME):
        return False
    if looks_full(text[len(SCHEME):]):
        return False
    return _THREE_X_ADDRESS.fullmatch(text) is not None


def three_x_address_message(text: str) -> str:
    return (f"{text} is a TCW 3.x reference; TCW 4 writes "
            f"tcw://<project>.<namespace>/<id-path> ({MIGRATE_HINT})")


def parse_address(text: Any) -> FullId | FolderAddress:
    """An object address or a folder address, by Design 2.1 and 2.2."""
    if not isinstance(text, str) or not text.startswith(SCHEME):
        raise MalformedId(f"{text!r} is not a tcw:// address")
    if is_3x_address(text):
        raise ThreeXReference(three_x_address_message(text))
    rest = text[len(SCHEME):]
    if not _ADDRESS_CHARACTERS.fullmatch(rest):
        bad = next(c for c in rest if not _ADDRESS_CHARACTERS.fullmatch(c))
        raise MalformedId(
            f"{text} is not a tcw:// address: {bad!r} is not allowed (an "
            f"address holds only {_FOLDER_RULE} and '/'; no query, fragment, "
            f"port, user or percent-encoding)")
    authority, slash, path = rest.partition("/")
    if authority != authority.lower():
        raise MalformedId(
            f"{text} is not a tcw:// address: the part before the first '/' "
            f"is lowercase")
    pieces = authority.split(".")
    if pieces[-1] == "path" and len(pieces) in (2, 3):
        if not slash:
            raise MalformedId(
                f"{text} is not a tcw:// address: a folder address has a '/' "
                f"after .path (write {text}/)")
        _check_project(pieces[0], text)
        scope = pieces[1] if len(pieces) == 3 else None
        if scope is not None:
            _check_namespace(scope, text)
        _check_folder_path(path, text)
        return FolderAddress(pieces[0], scope, path)
    if len(pieces) == 1:
        raise MalformedId(
            f"{text} is not a tcw:// address: it needs a namespace or .path "
            f"after the project ID (tcw://<project>.<namespace>/<id-path>, or "
            f"tcw://<project>.path/<folder>)")
    if path.endswith("/"):
        raise MalformedId(
            f"{text} is not a tcw:// address: an object address does not end "
            f"in '/'")
    return parse_full_id(rest)


def _check_folder_path(path: str, text: str) -> None:
    if not path:
        return
    for part in path[:-1].split("/") if path.endswith("/") else path.split("/"):
        if not part:
            raise MalformedId(
                f"{text} is not a tcw:// address: a folder path has no empty "
                f"part ('//')")
        if part in (".", ".."):
            raise MalformedId(
                f"{text} is not a tcw:// address: a folder path has no '.' or "
                f"'..' part, which a URL parser would drop")
        if not FOLDER_PART.fullmatch(part):
            raise MalformedId(
                f"{text} is not a tcw:// address: {part!r} breaks the rule "
                f"for a folder name ({_FOLDER_RULE})")


def three_x_stored_message(value: str, namespace: str) -> str:
    return (f"{value!r} is a TCW 3.x reference; TCW 4 writes "
            f"<project>.{namespace}/<id-path> ({MIGRATE_HINT})")


def parse_stored(value: Any, namespace: str) -> FullId:
    """A reference read from a file or a ticket (Design 5.2): a full
    identifier of `namespace`. A value in a 3.x form (no `.` before its first
    `/`) is a `ThreeXReference`; anything else that is not valid is a
    `MalformedId`."""
    if not isinstance(value, str) or not value:
        raise MalformedId(f"{value!r} is not a full identifier")
    if not looks_full(value):
        raise ThreeXReference(three_x_stored_message(value, namespace))
    return parse_full_id(value, namespace)


@dataclass(frozen=True)
class Input:
    """A command argument naming an object, sorted by Design 3.1's table:

    - `a`: a full identifier, or its object address (`full_id`);
    - `b`: a tracker key alone, work only (`key`);
    - `c`: a work full identifier whose id-path is one key (`full_id`, `key`);
    - `d`: an id-path of the active project (`id_path`).
    """

    form: str
    full_id: FullId | None = None
    key: str | None = None
    id_path: str | None = None


def sort_input(text: Any, namespace: str, key_pattern: re.Pattern | None = None) -> Input:
    """Sort command input into one form of Design 3.1 by its text alone.
    `key_pattern` is the tracker key rule, passed in by the work layer."""
    if not isinstance(text, str) or not text:
        raise MalformedId(f"{text!r} names no {namespace} object")
    if text.startswith(SCHEME):
        found = parse_address(text)
        if isinstance(found, FolderAddress):
            raise MalformedId(
                f"{text} names a folder, not a {namespace} object; write "
                f"tcw://<project>.{namespace}/<id-path>")
        if found.namespace != namespace:
            parse_full_id(str(found), namespace)
        full_id = found
    elif looks_full(text):
        full_id = parse_full_id(text, namespace)
    else:
        if key_pattern is not None and key_pattern.fullmatch(text):
            return Input("b", key=text)
        problem = id_path_problem(text)
        if problem:
            raise MalformedId(
                f"{text!r} names no {namespace} object: {problem}; write its "
                f"full identifier (<project>.{namespace}/<id-path>) or its "
                f"id-path in this project")
        return Input("d", id_path=text)
    if (key_pattern is not None and "/" not in full_id.id_path
            and key_pattern.fullmatch(full_id.id_path)):
        return Input("c", full_id=full_id, key=full_id.id_path)
    return Input("a", full_id=full_id)


def identity(full_id: FullId) -> dict[str, str]:
    """The two keys every record carries (Design 4.3), built one way for the
    CLI and the web."""
    return {"full-id": str(full_id), "owner": full_id.project}
