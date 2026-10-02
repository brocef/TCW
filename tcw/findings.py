"""One problem a check found, in the shape every `tcw` check reports.

It sits at the top of the package because the stores, `validate` and the work
model all produce findings, and none should import another to get the type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Finding:
    severity: Literal["error", "warning", "unresolved"]
    where: str  # a path, with ":<line>" when known, or a slug
    message: str

    def __str__(self) -> str:
        return f"{self.severity}: {self.where}: {self.message}"
