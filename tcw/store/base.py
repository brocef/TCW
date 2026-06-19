"""Abstract store interfaces — the portable spine the CLI depends on.

Per AGENTS.md (the litmus test) the model is storage-abstracted: a tree of
named nodes with cross-links is implementable by any backend. The filesystem
adapters in `fs.py` are the only realization shipped; remote adapters stay
possible but unbuilt. Phase 2 introduces `TaxonomyStore`; capabilities and work
add their interfaces here in their phases. The shared tree-store core is
extracted in Phase 4 — not pre-abstracted here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class RefError(Exception):
    """A reference could not be resolved cleanly."""


class AmbiguousRef(RefError):
    """A bare reference matches more than one namespace — author must qualify."""


@dataclass
class Term:
    """A taxonomy node: a domain entity/concept addressed by its path.

    `slug` is the identity (path from the taxonomy root, e.g. `admin/permission`).
    `origin` is `"local"` or the `extends` alias the term was resolved through.
    """
    slug: str
    name: str
    description: str = ""
    relates_to: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    origin: str = "local"

    @property
    def qualified(self) -> str:
        """Slug prefixed with its origin alias (`shared/Some/Term`); bare when local."""
        return self.slug if self.origin == "local" else f"{self.origin}/{self.slug}"


class TaxonomyStore(ABC):
    """The taxonomy axis: a forest of terms, optionally federated via `extends`."""

    @abstractmethod
    def list(self, local_only: bool = False) -> list[Term]:
        """All terms (local + inherited), each flagged by `origin`."""

    @abstractmethod
    def get(self, ref: str) -> Term | None:
        """Resolve a reference (B.6) to a term, or None if it resolves to nothing.

        Raises `AmbiguousRef` when a bare ref matches multiple extended taxonomies.
        """

    @abstractmethod
    def add(self, name: str, slug: str | None = None, parent: str | None = None,
            description: str = "") -> Term:
        """Create a local term under `parent` (root by default). Refuse a collision."""

    @abstractmethod
    def remove(self, ref: str) -> None:
        """Remove a local term. Refuse an inherited one."""

    @abstractmethod
    def search(self, query: str) -> list[Term]:
        """Substring search over names + descriptions, local + inherited."""

    @abstractmethod
    def check(self) -> list[str]:
        """Validate the taxonomy; return a list of problems (empty == clean)."""
