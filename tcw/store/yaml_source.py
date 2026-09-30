"""Parse YAML text that came from a file, naming that file in any error."""

from __future__ import annotations

from pathlib import Path

import yaml


def load(text: str, path: Path | str, loader: type = yaml.SafeLoader):
    """`yaml.load(text, Loader=loader)`, with `path` as the name in its errors.

    Handed a plain string, PyYAML calls it `"<unicode string>"` in every error
    position, so a syntax error names no file. Handing it a named stream instead
    fixes the name but drops the excerpt of the offending line and its `^` caret,
    which PyYAML keeps only for a string. Naming the loader built from the string
    keeps both. Two errors still name no file: a character YAML forbids is
    refused while the loader is built, before it has a name, and a duplicate
    key (`_UniqueKeyLoader`) is raised with no position at all."""
    parser = loader(text)
    parser.name = str(path)
    try:
        return parser.get_single_data()
    finally:
        parser.dispose()
