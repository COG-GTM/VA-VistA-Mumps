"""Resolve M routine calls (``TAG^ROUTINE``) to the source line that defines the tag."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

REPO_URL = "https://github.com/COG-GTM/VA-VistA-Mumps"
# Commit the citations were generated against; the M sources under Packages/
# are unchanged by this directory, so these permalinks stay valid.
SOURCE_SHA = "b7aecb9029f9bb8639a7bfa63b635469065ab44d"
# FileMan ships the %DT date utility as routine DIDT (renamed to %DT on install).
_ROUTINE_FILE_ALIASES = {"%DT": "DIDT"}


@dataclass(frozen=True)
class RoutineCitation:
    ref: str
    path: str
    line: int
    text: str

    @property
    def url(self) -> str:
        return permalink(self.path, self.line)


def permalink(relpath: str, line: int) -> str:
    return f"{REPO_URL}/blob/{SOURCE_SHA}/{quote(relpath)}#L{line}"


def find_routine(repo_root: Path, routine: str) -> Path | None:
    name = _ROUTINE_FILE_ALIASES.get(routine, routine)
    hits = sorted(repo_root.glob(f"Packages/*/Routines/{name}.m"))
    return hits[0] if hits else None


def resolve(repo_root: Path, ref: str) -> RoutineCitation | None:
    tag, _, routine = ref.partition("^")
    path = find_routine(repo_root, routine)
    if path is None:
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rel = path.relative_to(repo_root).as_posix()
    if not tag:
        return RoutineCitation(ref, rel, 1, lines[0] if lines else "")
    pat = re.compile(rf"^{re.escape(tag)}(?=[\s;(]|$)")
    for n, text in enumerate(lines, start=1):
        if pat.match(text):
            return RoutineCitation(ref, rel, n, text)
    return None
