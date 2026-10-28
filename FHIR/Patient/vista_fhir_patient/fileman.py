"""FileMan value conversions: dates, names, ZIP codes."""

from __future__ import annotations

import re

# Suffixes recognised by the Kernel name standardizer (see XLFNAME1) plus
# generational numerals.
NAME_SUFFIXES = {"JR", "SR", "II", "III", "IV", "V", "VI", "DR", "PHD", "MD", "ESQ"}


def fm_date(value: str, *, tz: str | None = None) -> str | None:
    """FileMan ``YYYMMDD[.HHMMSS]`` (YYY = year - 1700) to a FHIR date/dateTime.

    Imprecise dates (00 month or day) reduce precision. A time is emitted only
    when ``tz`` (e.g. ``"-05:00"``) is given, because FHIR requires a zone on
    dateTimes that carry a time.
    """
    value = (value or "").strip()
    m = re.fullmatch(r"(\d{7})(?:\.(\d{1,6}))?", value)
    if not m:
        return None
    d, t = m.groups()
    year = int(d[:3]) + 1700
    month, day = d[3:5], d[5:7]
    if month == "00":
        return f"{year:04d}"
    if day == "00":
        return f"{year:04d}-{month}"
    out = f"{year:04d}-{month}-{day}"
    if t and tz and int(t.ljust(6, "0")):
        t = t.ljust(6, "0")
        out += f"T{t[:2]}:{t[2:4]}:{t[4:6]}{tz}"
    return out


def parse_name(value: str) -> dict:
    """Split a standard VistA name ``LAST,FIRST MIDDLE SUFFIX`` into FHIR HumanName parts."""
    value = (value or "").strip()
    if not value:
        return {}
    family, _, rest = value.partition(",")
    tokens = rest.split()
    suffix = []
    while tokens and tokens[-1].replace(".", "") in NAME_SUFFIXES:
        suffix.insert(0, tokens.pop())
    name: dict = {"text": value}
    if family.strip():
        name["family"] = family.strip()
    if tokens:
        name["given"] = tokens
    if suffix:
        name["suffix"] = suffix
    return name


def name_from_components(zero: str, original: str) -> dict:
    """HumanName from NAME COMPONENTS (file #20) node 1: family^given^middle^prefix^suffix^degree."""
    p = (zero.split("^") + [""] * 6)[:6]
    family, given, middle, prefix, suffix, degree = (x.strip() for x in p)
    name: dict = {}
    if original:
        name["text"] = original
    if family:
        name["family"] = family
    givens = [g for g in [given, *middle.split()] if g]
    if givens:
        name["given"] = givens
    if prefix:
        name["prefix"] = [prefix]
    suffixes = [s for s in [*suffix.split(), degree] if s]
    if suffixes:
        name["suffix"] = suffixes
    return name


def postal_code(zip5: str, zip4: str) -> str | None:
    """Prefer the 9-digit ZIP+4 (stored without hyphen by ZIPIN^VAFADDR)."""
    z = (zip4 or "").replace("-", "").strip()
    if re.fullmatch(r"\d{9}", z):
        return f"{z[:5]}-{z[5:]}"
    if re.fullmatch(r"\d{5}", z):
        return z
    z5 = (zip5 or "").strip()
    return z5 or None
