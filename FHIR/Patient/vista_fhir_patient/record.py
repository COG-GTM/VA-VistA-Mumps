"""A single ^DPT(DFN) entry, read field-by-field through the file #2 data dictionary."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from .zwr import iter_zwr, piece

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def load_dd(path: str | None = None) -> dict:
    return json.loads(Path(path or DATA_DIR / "dd_file2.json").read_text(encoding="utf-8"))


class PatientRecord:
    """Holds ``^DPT(dfn,...)`` nodes plus any ``^VA(20,...)`` name-component nodes.

    Every non-empty field read is recorded in ``trace`` as ``"<file>:<field>"``,
    so tests can prove the transform consumes every field the mapping table
    claims it maps.
    """

    def __init__(self, dfn: str, nodes: dict[tuple[str, ...], str],
                 name_components: dict[str, str] | None = None, dd: dict | None = None):
        self.dfn = str(dfn)
        self.nodes = nodes
        self.name_components = name_components or {}
        self.dd = dd or load_dd()
        self.trace: set[str] = set()

    @classmethod
    def from_zwr(cls, lines: Iterable[str], dfn: str | None = None, dd: dict | None = None) -> "PatientRecord":
        nodes: dict[tuple[str, ...], str] = {}
        comps: dict[str, str] = {}
        for zn in iter_zwr(lines):
            s = zn.subscripts
            if zn.global_name == "DPT" and len(s) >= 2 and s[0] != "0":
                if dfn is None:
                    dfn = s[0]
                if s[0] == str(dfn):
                    nodes[s[1:]] = zn.value
            elif zn.global_name == "VA" and len(s) == 3 and s[0] == "20" and s[2] == "1":
                comps[s[1]] = zn.value
        if dfn is None:
            raise ValueError("no ^DPT entry found")
        return cls(dfn, nodes, comps, dd)

    def fdef(self, file: str, num: str) -> dict:
        return self.dd["files"][file][num]

    def _extract(self, raw: str, fd: dict) -> str:
        pc = fd["piece"]
        if pc.startswith("E"):
            a, _, b = pc[1:].partition(",")
            return raw[int(a) - 1:int(b or a)]
        return piece(raw, int(pc)) if pc.isdigit() else ""

    def get(self, num: str) -> str:
        """Internal value of a top-level file #2 field."""
        fd = self.fdef("2", num)
        value = self._extract(self.nodes.get((fd["node"],), ""), fd).strip()
        if value:
            self.trace.add(f"2:{num}")
        return value

    def multiple(self, num: str) -> list[tuple[str, "SubEntry"]]:
        """Entries of a multiple field, in IEN order."""
        fd = self.fdef("2", num)
        sub, node = fd["subfile"], fd["node"]
        iens = sorted({k[1] for k in self.nodes if len(k) >= 3 and k[0] == node and k[1] != "0"},
                      key=lambda x: float(x) if x.replace(".", "").isdigit() else 0)
        if iens:
            self.trace.add(f"2:{num}")
        return [(i, SubEntry(self, sub, (node, i))) for i in iens]

    def components(self, ien: str) -> str:
        return self.name_components.get(str(ien).strip(), "")


class SubEntry:
    def __init__(self, record: PatientRecord, subfile: str, path: tuple[str, ...]):
        self.record, self.subfile, self.path = record, subfile, path

    def get(self, num: str) -> str:
        fd = self.record.fdef(self.subfile, num)
        raw = self.record.nodes.get(self.path + (fd["node"],), "")
        value = self.record._extract(raw, fd).strip()
        if value:
            self.record.trace.add(f"{self.subfile}:{num}")
        return value
