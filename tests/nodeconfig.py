"""Declaring a component's `extends` in the node's `tcw-config.yaml`.

`extends` used to live in a file inside the store — `config.yaml` for taxonomy,
`.config.yaml` for capabilities — and a fixture declared inheritance by writing
that file. It now lives at `<component>.extends` in the node config, beside
`path` and `repository`, so a fixture has to merge a key into a file that
usually already holds `id` and `connected-projects`.

One helper rather than a read-modify-write repeated at twenty sites: a fixture
rewritten by hand that many times is where a silently-passing test comes from.

**Nothing here defaults an axis the code branches on.** Both the component and
the declaration are explicit arguments, because a helper's default is always
whichever value makes setup easiest, which is how a resolution cell ends up
unreachable by construction.
"""
from pathlib import Path

import yaml


def set_component_key(node_root: Path, component: str, key: str, value) -> None:
    """Merge `<component>.<key> = value` into the node's config, keeping the rest."""
    config_path = Path(node_root) / "tcw-config.yaml"
    raw = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}
    section = raw.get(component)
    if not isinstance(section, dict):
        section = {}
    section[key] = value
    raw[component] = section
    config_path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))


def declare_extends(node_root: Path, component: str, text: str) -> None:
    """Declare `extends` from the YAML a fixture used to write into the store file.

    Takes the same `extends:`-rooted text those fixtures already pass, so a
    deliberately wrong shape — a legacy alias map, a duplicate id, an
    unregistered project — still reaches the code under test unchanged.
    """
    parsed = yaml.safe_load(text) or {}
    set_component_key(node_root, component, "extends", parsed.get("extends"))
