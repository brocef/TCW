"""Writing a component's key into the node's `tcw-config.yaml`.

`set_component_key` merges `<component>.<key>` (`path`, `repository`, ...)
into a file that usually already holds `id` and `parents`, keeping the rest.

One helper rather than a read-modify-write repeated at twenty sites: a fixture
rewritten by hand that many times is where a silently-passing test comes from.

`declare_extends` writes `<component>.extends`, which TCW 4.0 removed: a
project inherits taxonomy and capabilities from its parents (TCW-112 Design
1.5). It survives only for a test that writes the removed key on purpose, to
check that it is refused or ignored; never use it to set up inheritance.

**Nothing here defaults an axis the code branches on.** Both the component and
the declaration are explicit arguments, because a helper's default is always
whichever value makes setup easiest, which is how a resolution cell ends up
unreachable by construction.
"""
from pathlib import Path

import yaml
from tests.projectfiles import config_file, write_config_file


def set_component_key(project_root: Path, component: str, key: str, value) -> None:
    """Merge `<component>.<key> = value` into the node's config, keeping the rest."""
    config_path = config_file(Path(project_root))
    raw = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}
    section = raw.get(component)
    if not isinstance(section, dict):
        section = {}
    section[key] = value
    raw[component] = section
    write_config_file(config_path, yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))


def declare_extends(project_root: Path, component: str, text: str) -> None:
    """Write the removed `<component>.extends` key from `extends:`-rooted YAML.

    Only for a test whose subject is that key: TCW 4.0 refuses it in the
    project's own file and ignores it in another project's file.
    """
    parsed = yaml.safe_load(text) or {}
    set_component_key(project_root, component, "extends", parsed.get("extends"))
