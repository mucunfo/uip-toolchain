"""File and project context — shared across detectors."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .encoding import detect_and_decode


# CommentOut blocks (UiPath-specific)
_RE_COMMENT_OUT_BLOCK = re.compile(
    r"<!--\s*<\w+:CommentOut.*?</\w+:CommentOut>\s*-->",
    re.DOTALL,
)


@dataclass
class FileContext:
    """Holds XAML file content with BOM-aware decoding.

    `content` = raw file content; `active_content` = with CommentOut blocks
    stripped (for detector matching); `lines` = splits of content (NOT
    active_content) so line numbers reported match real file positions.
    """
    path: Path
    content: str = field(default="", init=False)
    active_content: str = field(default="", init=False)
    lines: list[str] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if isinstance(self.path, str):
            self.path = Path(self.path)
        self.content = detect_and_decode(self.path)
        self.active_content = _RE_COMMENT_OUT_BLOCK.sub("", self.content)
        self.lines = self.content.splitlines()


@dataclass
class ProjectContext:
    """Holds project root + parsed project.json.

    Use `find_root(file_or_dir)` classmethod to locate the project.json
    walking up parent directories.
    """
    root: Path
    project_json: dict[str, Any]

    @property
    def target_framework(self) -> str:
        return self.project_json.get("targetFramework", "Legacy")

    @property
    def expression_language(self) -> str:
        return self.project_json.get("expressionLanguage", "VisualBasic")

    @property
    def project_type(self) -> str:
        return self.project_json.get("projectType", "Process")

    @classmethod
    def find_root(cls, start: Path | str) -> ProjectContext | None:
        """Walk up from `start` until finding project.json. Return None if none."""
        p = Path(start).resolve()
        if p.is_file():
            p = p.parent
        for candidate in [p] + list(p.parents):
            pj = candidate / "project.json"
            if pj.exists():
                try:
                    data = json.loads(pj.read_text(encoding="utf-8"))
                    return cls(root=candidate, project_json=data)
                except (json.JSONDecodeError, OSError):
                    return None
        return None
