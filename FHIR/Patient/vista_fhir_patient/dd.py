"""Extract FileMan data-dictionary field definitions for file #2 from DD.zwr."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .zwr import iter_zwr, piece

DD_RELPATH = "Packages/VA FileMan/Globals/DD.zwr"
PATIENT_FILE = "2"
# Subfiles of file #2 whose fields feed Patient elements; other multiples are
# classified at the multiple-field level only.
MAPPED_SUBFILES = ("2.01", "2.02", "2.06", "2.07", "2.0991", "2.0992")

_ROUTINE_REF = re.compile(r"(?:\$\$)?([A-Z%][A-Z0-9]{0,15})?\^([A-Z%][A-Z0-9]{1,15})")


@dataclass
class FieldDef:
    file: str
    number: str
    name: str
    type_spec: str
    storage: str
    node: str
    piece: str
    set_codes: dict[str, str]
    pointer_file: str
    subfile: str
    input_transform: str
    routine_refs: list[str]
    dd_line: int
    dd_raw: str
    description: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.file}:{self.number}"

    def to_json(self) -> dict:
        row = asdict(self)
        row.pop("description")
        return row


def _type_info(type_spec: str) -> tuple[str, str]:
    """Return (subfile, pointer_file) parsed from piece 2 of a field's 0-node."""
    m = re.match(r"^(\d+\.\d+|\d+)", type_spec)
    if m:
        return m.group(1), ""
    m = re.search(r"P(\d*\.?\d+)'?", type_spec)
    return "", (m.group(1) if m else "")


def routine_refs(code: str) -> list[str]:
    """``TAG^ROUTINE`` / ``^ROUTINE`` calls in M code, excluding global references."""
    refs = []
    for m in _ROUTINE_REF.finditer(code):
        start = m.start(2) - 1
        if start > 0 and code[start - 1] == "(":
            continue  # $D(^DPT(...)) style global
        tail = code[m.end():m.end() + 1]
        if tail == "(" and not m.group(1):
            continue  # ^GLOBAL( reference
        ref = f"{m.group(1) or ''}^{m.group(2)}"
        if ref not in refs:
            refs.append(ref)
    return refs


def parse_zero_node(file: str, number: str, value: str, line_no: int, raw: str) -> FieldDef:
    parts = value.split("^")
    type_spec = piece(value, 2)
    subfile, pointer_file = _type_info(type_spec)
    storage = piece(value, 4)
    node, _, pc = storage.partition(";")
    set_codes = {}
    if "S" in re.sub(r"P\d.*", "", type_spec) and not subfile:
        for pair in piece(value, 3).split(";"):
            if ":" in pair:
                k, v = pair.split(":", 1)
                set_codes[k] = v
    transform = "^".join(parts[4:])
    return FieldDef(
        file=file, number=number, name=parts[0], type_spec=type_spec,
        storage=storage, node=node.strip(), piece=pc.strip(), set_codes=set_codes,
        pointer_file=pointer_file, subfile=subfile, input_transform=transform,
        routine_refs=routine_refs(transform), dd_line=line_no, dd_raw=raw,
    )


def extract(lines: Iterable[str], files: Iterable[str] = (PATIENT_FILE, *MAPPED_SUBFILES)) -> dict[str, dict[str, FieldDef]]:
    wanted = set(files)
    prefixes = tuple(f'^DD({f},' if "." not in f else f'^DD("{f}",' for f in wanted)
    out: dict[str, dict[str, FieldDef]] = {f: {} for f in wanted}
    for zn in iter_zwr(line for line in lines):
        if not zn.raw.startswith(prefixes) or zn.global_name != "DD":
            continue
        subs = zn.subscripts
        file = subs[0]
        if file not in wanted or len(subs) < 3 or subs[1] == "0":
            continue
        number = subs[1]
        if len(subs) == 3 and subs[2] == "0":
            out[file][number] = parse_zero_node(file, number, zn.value, zn.line_no, zn.raw)
        elif len(subs) == 5 and subs[2] == "21" and subs[4] == "0" and number in out[file]:
            out[file][number].description.append(zn.value)
    return out


def extract_from_repo(repo_root: Path) -> dict[str, dict[str, FieldDef]]:
    with open(repo_root / DD_RELPATH, encoding="utf-8", errors="replace") as fh:
        return extract(fh)
