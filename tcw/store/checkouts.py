"""Where a declared repository is realized on this machine.

**Filesystem-adapter detail, not part of the storage-neutral model.** It lives in
its own module because two adapter modules need it and one of them may not import
the other: `fs.py` imports `project.py`, so anything both use has to sit beneath
both. `base.py` would be the wrong home for the opposite reason — it is the
storage-neutral interface, and a cache directory is exactly the kind of
filesystem particular it deliberately keeps out.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from tcw.store.base import RepositoryDeclaration


def _cache_root() -> Path:
    """Where working copies land when a declaration names no `checkout`.

    XDG, so it is outside every checkout and survives between sessions on one
    machine. Read from the environment on each call rather than at import: a
    test — and a user's shell — may set it after this module loads.
    """
    base = os.environ.get("XDG_CACHE_HOME") or "~/.cache"
    return Path(base).expanduser() / "tcw" / "stores"


def _cache_key(declaration: RepositoryDeclaration) -> str:
    """A directory name for one (url, ref) pair: readable, then unambiguous.

    The readable half is the tail of the URL, so a user browsing the cache can
    tell whose repository a directory holds. The hash is what actually keeps two
    declarations apart, because the readable half is lossy by design.

    Keyed on url *and* ref: two projects naming the same repository at the same
    ref should share one working copy, and two refs of it must not fight over
    one checkout.
    """
    cleaned = declaration.url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    tokens = [token.rpartition("@")[2]                 # drop any `git@` user part
              for token in re.split(r"[/:]", cleaned) if token]
    slug = "-".join(re.sub(r"[^A-Za-z0-9._-]+", "-", token).strip("-.")
                    for token in tokens[-3:])
    slug = (slug.strip("-").lower() or "store")[:60]
    digest = hashlib.sha256(
        f"{declaration.url}\n{declaration.ref or ''}".encode("utf-8")).hexdigest()[:12]
    return f"{slug}-{digest}"


def checkout_root(node_root: Path, declaration: RepositoryDeclaration) -> Path:
    """The working copy's root for `declaration` — the declared `checkout`, or a
    per-machine cache directory. `~` expands; a relative path is the node's."""
    if declaration.checkout:
        value = Path(declaration.checkout).expanduser()
        return value if value.is_absolute() else (node_root / value)
    return _cache_root() / _cache_key(declaration)


def provisioned_root(node_root: Path, declaration: RepositoryDeclaration) -> Path:
    """Where a provisioned *thing* — a store or a whole node — would live.

    `provisioned_store_root` is this function under the name its callers already
    use. A node is the same computation with `declaration.path` naming the node's
    directory within the repository rather than the store's, which is why there
    is one function and not two that could drift.
    """
    root = checkout_root(node_root, declaration)
    return (root / declaration.path) if declaration.path else root
