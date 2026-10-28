"""Minimal reader for OSEHRA ZWR global exports (``^GLOBAL(sub,...)=value``)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from typing import Iterable, Iterator

_CHAR = re.compile(r"\$C\(([0-9,]+)\)")


@dataclass(frozen=True)
class ZwrNode:
    line_no: int
    global_name: str
    subscripts: tuple[str, ...]
    value: str
    raw: str


def _split_top(text: str, sep: str) -> list[str]:
    """Split on ``sep`` outside double-quoted strings (M escapes quotes as "")."""
    parts, buf, in_q, i = [], [], False, 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            in_q = not in_q
        if ch == sep and not in_q:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def canonical_number(text: str) -> str:
    """Return the M canonical form of a numeric subscript (``0.85`` -> ``.85``)."""
    try:
        num = Decimal(text)
    except InvalidOperation:
        return text
    out = format(num.normalize(), "f")
    if "." in out:
        out = out.rstrip("0").rstrip(".")
    if out.startswith("0."):
        out = out[1:]
    elif out.startswith("-0."):
        out = "-" + out[2:]
    return out


def _unquote(term: str) -> str:
    term = term.strip()
    if len(term) >= 2 and term[0] == '"' and term[-1] == '"':
        return term[1:-1].replace('""', '"')
    m = _CHAR.fullmatch(term)
    if m:
        return "".join(chr(int(c)) for c in m.group(1).split(","))
    return term


def decode_value(expr: str) -> str:
    """Decode a ZWR right-hand side, including ``"a"_$C(9)_"b"`` concatenations."""
    return "".join(_unquote(t) for t in _split_top(expr, "_"))


def decode_subscript(term: str) -> str:
    term = term.strip()
    text = _unquote(term)
    if re.fullmatch(r"-?(\d+\.?\d*|\.\d+)", text):
        return canonical_number(text)
    return text


def parse_line(line: str, line_no: int = 0) -> ZwrNode | None:
    line = line.rstrip("\r\n")
    if not line.startswith("^"):
        return None
    eq = None
    depth, in_q = 0, False
    for i, ch in enumerate(line):
        if ch == '"':
            in_q = not in_q
        elif not in_q and ch == "(":
            depth += 1
        elif not in_q and ch == ")":
            depth -= 1
        elif not in_q and depth == 0 and ch == "=":
            eq = i
            break
    if eq is None:
        return None
    ref, rhs = line[:eq], line[eq + 1 :]
    if "(" in ref:
        name, subs = ref[1:].split("(", 1)
        subscripts = tuple(decode_subscript(s) for s in _split_top(subs[:-1], ","))
    else:
        name, subscripts = ref[1:], ()
    return ZwrNode(line_no, name, subscripts, decode_value(rhs), line)


def iter_zwr(lines: Iterable[str]) -> Iterator[ZwrNode]:
    for n, line in enumerate(lines, start=1):
        node = parse_line(line, n)
        if node is not None:
            yield node


def piece(value: str, n: int, delim: str = "^") -> str:
    """M ``$PIECE(value,delim,n)`` (1-based)."""
    parts = value.split(delim)
    return parts[n - 1] if 0 < n <= len(parts) else ""
