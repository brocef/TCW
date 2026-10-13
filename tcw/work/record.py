"""The item record: the one set of fields `show --json`, each `list --json`
entry and a `generate:` prompt binding receive. Backend-neutral, so both
backends and the web viewer build it the same way."""

from __future__ import annotations

from typing import Any, Iterable

from tcw.work.backend import Query
from tcw.work.layout import Layout
from tcw.work.model import Item, blocks_of


def readable(backend) -> tuple[list[Item], list[str]]:
    """Every item of the backend's project that can be read, for `blocks` and
    `children`, and the paths of those that cannot. Only the filesystem keeps
    unreadable items beside readable ones; any other backend answers `list`."""
    from tcw.work.fs_backend import FsWorkBackend, read_all
    if isinstance(backend, FsWorkBackend):
        items, bad = read_all(backend.work_path, backend.project, backend.enabled)
        return items, [str(b.path) for b in bad]
    return backend.list(Query(all=True)), []


def item_record(item: Item, items: Iterable[Item], layout: Layout) -> dict[str, Any]:
    """`items` are the other items of this project that `blocks` and
    `children` are computed from (the readable ones)."""
    items = list(items)
    return {
        "slug": str(item.slug),
        "title": item.title,
        "stage": item.stage,
        "created": item.created.isoformat(),
        "priority": item.priority,
        "effort": item.effort,
        "complexity": item.complexity,
        "tags": list(item.tags),
        "assignee": item.assignee,
        "parent": str(item.parent) if item.parent else None,
        "blocked-by": [str(s) for s in item.blocked_by],
        "blocks": [str(s) for s in blocks_of(item.slug, items)],
        "children": [str(i.slug) for i in items if i.parent == item.slug],
        "path": str(layout.item_dir(item.slug)),
        "untracked": list(item.untracked),
    }
