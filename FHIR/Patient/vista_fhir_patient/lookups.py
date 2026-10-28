"""Pointer-file lookup tables read from the repo's ZWR exports.

The transform resolves FileMan pointers (state, marital status, race, ...)
through these tables. ``build_data.py`` snapshots them into ``data/lookups.json``
so the transform runs without the 40 MB+ global exports present.
"""

from __future__ import annotations

import json
from pathlib import Path

from .zwr import iter_zwr, piece

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SOURCES = {
    "state": ("Packages/Kernel/Globals/5+STATE.zwr", "DIC", "5"),
    "race": ("Packages/Registration/Globals/10+RACE.zwr", "DIC", "10"),
    "ethnicity": ("Packages/Registration/Globals/10.2+ETHNICITY.zwr", "DIC", "10.2"),
    "collection_method": ("Packages/Registration/Globals/10.3+RACE AND ETHNICITY COLLECTION METHOD.zwr", "DIC", "10.3"),
    "marital_status": ("Packages/Registration/Globals/11+MARITAL STATUS.zwr", "DIC", "11"),
    "religion": ("Packages/Registration/Globals/13+RELIGION.zwr", "DIC", "13"),
    "country": ("Packages/Health Level Seven/Globals/779.004+COUNTRY CODE.zwr", "HL", "779.004"),
    "language": ("Packages/VA FileMan/Globals/0.85+LANGUAGE.zwr", "DI", ".85"),
}


def build(repo_root: Path) -> dict:
    """Read zero nodes (and state county sub-entries) from each source global."""
    tables: dict = {}
    for key, (rel, gname, fileno) in SOURCES.items():
        table: dict = {}
        with open(repo_root / rel, encoding="utf-8", errors="replace") as fh:
            for zn in iter_zwr(fh):
                s = zn.subscripts
                if zn.global_name != gname or not s or s[0] != fileno or len(s) < 3:
                    continue
                if not s[1].isdigit() or s[1] == "0":
                    continue
                if len(s) == 3 and s[2] == "0":
                    table.setdefault(s[1], {})["zero"] = zn.value
                elif key == "state" and len(s) == 5 and s[2] == "1" and s[4] == "0" and s[3].isdigit():
                    table.setdefault(s[1], {}).setdefault("county", {})[s[3]] = piece(zn.value, 1)
        tables[key] = {"source": rel, "file": fileno, "entries": table}
    return tables


class Lookups:
    def __init__(self, tables: dict):
        self.tables = tables

    @classmethod
    def load(cls, path: Path | None = None) -> "Lookups":
        path = path or DATA_DIR / "lookups.json"
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def zero(self, table: str, ien: str) -> str:
        entry = self.tables[table]["entries"].get(str(ien).strip())
        return entry["zero"] if entry and "zero" in entry else ""

    def field(self, table: str, ien: str, n: int) -> str:
        return piece(self.zero(table, ien), n)

    def county(self, state_ien: str, county_ien: str) -> str:
        entry = self.tables["state"]["entries"].get(str(state_ien).strip(), {})
        return entry.get("county", {}).get(str(county_ien).strip(), "")
